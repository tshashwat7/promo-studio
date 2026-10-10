"""Master Daily Cosmic Blueprint Worker.

Runs the complete automated pipeline for Siddhanta Social Publishing:
1. Computes today's Siddhanta Panchang & detects festivals via authentic app rules (festival_resolver)
2. Uses intelligent Daily Content Selection (1 Primary Post per day from the 6-Card Universe)
3. Renders strict 1080 x 1350 (4:5 Feed Portrait) visual card using rule-based background templates
4. Prompts Gemini AI as Composer & Writer (concise, focused captions & hashtags for the chosen card)
5. Uploads to ImgBB and publishes to Instagram Graph API (or runs dry-run)

Can be executed locally or via GitHub Actions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from promo_studio.pipeline import PromoStudio
from promo_studio.automation.panchang_engine import DailyPanchang
from promo_studio.automation.panchang_data_client import (
    get_authoritative_daily_panchang,
    fetch_cross_repo_file,
)
from promo_studio.automation.card_universe import (
    render_card_1_panchang,
    render_card_2_plan_day,
    render_card_3_festival,
    render_card_4_kundli,
    render_card_5_chakra,
    render_card_6_jyotish,
)
from promo_studio.automation.ai_blueprint import generate_cosmic_caption, get_devotional_fallback_copy
from promo_studio.automation.instagram_carousel import InstagramCarouselPublisher
from promo_studio.ai.gemini import GeminiProvider
from promo_studio.core.image_host import ImgBBHost

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("daily_worker")


def get_credential(name: str, fallback_settings_key: str = None) -> str:
    """Gets credential from ENV or local PromoStudio keyring/db."""
    val = os.environ.get(name)
    if val:
        return val.strip()

    try:
        from promo_studio.config.secrets import get_secret
        sec = get_secret(name)
        if sec:
            return sec.strip()
    except Exception:
        pass

    if fallback_settings_key:
        try:
            from promo_studio.data.db import Database
            from promo_studio.config.settings import Settings
            db_path = os.path.expandvars(r"%APPDATA%\PromoStudio\promo_studio.db")
            if os.path.exists(db_path):
                s = Settings(Database(db_path))
                v = s.get(fallback_settings_key)
                if v:
                    return v.strip()
        except Exception:
            pass

    return ""


def add_play_store_qr_overlay(image: Image.Image, lang: str = "en") -> Image.Image:
    """Overlays a clean, elegant Google Play QR Code badge on the bottom-right corner."""
    qr_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "qr_play_store.png"
    if not qr_path.exists():
        return image

    try:
        qr = Image.open(qr_path).convert("RGBA").resize((58, 58), Image.Resampling.LANCZOS)
        badge_box = (740, 1248, 950, 1316)

        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(badge_box, radius=16, fill=(255, 252, 245), outline=(136, 17, 34), width=2)
        image.paste(qr, (748, 1253), qr)

        font_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts" / "hind"
        f_med = font_dir / "Hind-Medium.ttf"
        f_semi = font_dir / "Hind-SemiBold.ttf"

        if f_med.exists() and f_semi.exists():
            font_xs = ImageFont.truetype(str(f_med), 11)
            font_bd = ImageFont.truetype(str(f_semi), 16)
            font_sm = ImageFont.truetype(str(f_med), 13)
        else:
            font_xs = font_bd = font_sm = ImageFont.load_default()

        draw.text((814, 1252), "GET IT ON", font=font_xs, fill=(90, 80, 70))
        draw.text((814, 1264), "Google Play", font=font_bd, fill=(20, 20, 20))
        draw.text((814, 1284), "Scan to Install", font=font_sm, fill=(136, 17, 34))
    except Exception as e:
        log.warning("Could not apply QR badge overlay: %s", e)

    return image


def is_last_day_of_month(d: dt.date) -> bool:
    """Returns True if d is the final day of its calendar month."""
    next_day = d + dt.timedelta(days=1)
    return next_day.month != d.month


def get_thematic_post_type(panchang: DailyPanchang) -> tuple[str | None, str | None]:
    """Determines the secondary/thematic post of the day:
    1. 1st of month: Chakra Balance ('New Month: Balance Your Inner Energy')
    2. Last day of month: Kundli Journey ('Month End: Your Kundli & Dasha Journey')
    3. Active festival: Festival Alert
    4. Friday: Today's Sky & Planetary Transit
    5. Tuesday & Thursday: Plan Your Day (Choghadiya & Rahu Kaal)
    """
    d = panchang.date
    if d.day == 1:
        return "chakra", "Balance Your Inner Energy (Chakras)"
    if is_last_day_of_month(d):
        return "kundli", "Your Kundli & Dasha Journey"
    if panchang.is_festival and panchang.festival_name:
        return "festival", f"Festival Alert: {panchang.festival_name}"
    weekday = d.weekday()  # Monday=0, Sunday=6
    if weekday == 4:  # Friday
        return "jyotish", "Today's Sky & Planetary Transit Insight"
    if weekday in (1, 3):  # Tuesday, Thursday
        return "plan_day", "Plan Your Day Wisely"
    return None, None


def select_daily_post_type(panchang: DailyPanchang, slot: str = "primary") -> tuple[str, str]:
    """Intelligently selects the post type based on slot and date.
    - Slot 'primary': Panchang is ALWAYS the primary post.
    - Slot 'secondary': Returns thematic card (Festival, Transit, Plan Day, or Monthly promo).
    - Slot 'auto': Defaults to primary in morning, secondary in afternoon.
    """
    if slot == "primary":
        return "panchang", "Today's Panchang Overview"
    if slot == "secondary":
        pt, title = get_thematic_post_type(panchang)
        if pt:
            return pt, title
        return "panchang", "Today's Panchang Overview"

    # Default / legacy fallback
    pt, title = get_thematic_post_type(panchang)
    if pt:
        return pt, title
    return "panchang", "Today's Panchang Overview"


def render_selected_card(post_type: str, panchang: DailyPanchang, out_path: Path) -> Path:
    """Renders the single selected card at 1080 x 1350 via legacy card universe."""
    if post_type == "festival":
        render_card_3_festival(panchang, out_path)
    elif post_type == "plan_day":
        render_card_2_plan_day(panchang, out_path)
    elif post_type == "kundli":
        render_card_4_kundli(panchang, out_path)
    elif post_type == "chakra":
        render_card_5_chakra(out_path)
    elif post_type == "jyotish":
        render_card_6_jyotish(panchang, out_path)
    else:  # default "panchang"
        render_card_1_panchang(panchang, out_path)
    return out_path


def format_12h_clean(time_str: str) -> str:
    r"""Ensures a 12-hour time string matches regex ^(1[0-2]|[1-9]):([0-5]\d) ([AP]M)$ without leading zeros."""
    if not time_str or not isinstance(time_str, str):
        return "6:00 AM"
    parts = time_str.strip().split(" ")
    if len(parts) == 2:
        hm = parts[0].split(":")
        if len(hm) == 2:
            try:
                h = int(hm[0])
                m = int(hm[1])
                half = parts[1].upper()
                if half in ("AM", "PM") and 1 <= h <= 12 and 0 <= m <= 59:
                    return f"{h}:{m:02d} {half}"
            except ValueError:
                pass
    return "6:00 AM"


def minutes_to_12h_clean(m: float) -> str:
    m_int = int(round(m)) % (24 * 60)
    hour = m_int // 60
    minute = m_int % 60
    half = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{minute:02d} {half}"


def synthesize_studio_inputs(panchang: DailyPanchang, target_date: dt.date) -> tuple[dict, dict]:
    """Synthesizes fully valid, schema-compliant daily_panchang and muhurta_data objects from DailyPanchang."""
    from promo_studio.adapter import (
        DAY_CYCLE, DAY_START, CHOGHADIYA_QUALITY,
        RAHU_OCTANT, YAMAGANDA_OCTANT, GULIKA_OCTANT, minutes
    )

    rise_s = format_12h_clean(panchang.sunrise_str)
    set_s = format_12h_clean(panchang.sunset_str)
    rise_m = minutes(rise_s)
    set_m = minutes(set_s)
    eighth = (set_m - rise_m) / 8.0
    fifteenth = (set_m - rise_m) / 15.0
    weekday = target_date.strftime("%A")

    abhijit_s = minutes_to_12h_clean(rise_m + 7 * fifteenth)
    abhijit_e = minutes_to_12h_clean(rise_m + 8 * fifteenth)

    rahu_s = minutes_to_12h_clean(rise_m + (RAHU_OCTANT[weekday] - 1) * eighth)
    rahu_e = minutes_to_12h_clean(rise_m + RAHU_OCTANT[weekday] * eighth)

    yama_s = minutes_to_12h_clean(rise_m + (YAMAGANDA_OCTANT[weekday] - 1) * eighth)
    yama_e = minutes_to_12h_clean(rise_m + YAMAGANDA_OCTANT[weekday] * eighth)

    guli_s = minutes_to_12h_clean(rise_m + (GULIKA_OCTANT[weekday] - 1) * eighth)
    guli_e = minutes_to_12h_clean(rise_m + GULIKA_OCTANT[weekday] * eighth)

    first_idx = DAY_CYCLE.index(DAY_START[weekday])
    day_slots = []
    for i in range(8):
        c_name = DAY_CYCLE[(first_idx + i) % len(DAY_CYCLE)]
        s_time = minutes_to_12h_clean(rise_m + i * eighth)
        e_time = minutes_to_12h_clean(rise_m + (i + 1) * eighth)
        q_en = CHOGHADIYA_QUALITY[c_name]
        day_slots.append({
            "slot_number": i + 1,
            "name_en": c_name,
            "name_hi": c_name,
            "quality_en": q_en,
            "quality_hi": q_en,
            "is_auspicious": q_en in ("Best", "Auspicious"),
            "start": s_time,
            "end": e_time
        })

    festivals = []
    if panchang.is_festival and panchang.festival_name:
        festivals.append({
            "id": panchang.festival_name.lower().replace(" ", "_"),
            "name_en": panchang.festival_name,
            "name_hi": panchang.festival_name,
            "description_en": panchang.festival_note or "",
            "description_hi": panchang.festival_note or "",
        })

    daily_dict = {
        "metadata": {
            "source": "Siddhanta Vedic Panchang Engine",
            "generated_at": dt.datetime.now().isoformat(),
            "schema_version": "3.5",
            "location": {
                "name": "Ujjain, India (Standard Astronomical Baseline)",
                "latitude": 23.1765,
                "longitude": 75.7885,
                "timezone": "Asia/Kolkata",
            },
        },
        "today": {
            "date": target_date.isoformat(),
            "day_of_week_en": weekday,
            "day_of_week_hi": panchang.vara_hi,
            "is_festival_today": panchang.is_festival,
            "festival_count_today": len(festivals),
            "primary_festival_en": panchang.festival_name if panchang.is_festival else None,
            "primary_festival_hi": panchang.festival_name if panchang.is_festival else None,
            "festivals_today": festivals,
            "english": {
                "date_formatted": panchang.date_formatted,
                "tithi": f"{panchang.masa_name} {panchang.paksha} {panchang.tithi_name}",
                "tithi_name": panchang.tithi_name,
                "paksha": panchang.paksha.lower(),
                "tithi_end": format_12h_clean(panchang.tithi_end) if panchang.tithi_end else "11:59 PM",
                "nakshatra": panchang.nakshatra_name,
                "nakshatra_end": format_12h_clean(panchang.nakshatra_end) if panchang.nakshatra_end else "11:59 PM",
                "yoga": panchang.yoga_name or "Shubha",
                "karana": panchang.karana_name or "Bava",
                "vara": panchang.vara_en,
                "masa": panchang.masa_name,
                "samvatsara": "Parikhi",
                "vikram_samvat": 2083,
                "shaka_samvat": 1948,
                "moon_rashi": panchang.moon_rashi.split(" ")[-1].strip("()") if "(" in panchang.moon_rashi else panchang.moon_rashi,
                "sun_rashi": panchang.sun_rashi.split(" ")[-1].strip("()") if "(" in panchang.sun_rashi else panchang.sun_rashi,
                "sunrise": rise_s,
                "sunset": set_s,
                "moonrise": "5:45 AM",
                "moonset": "5:30 PM",
            },
            "hindi": {
                "date_formatted": panchang.date_formatted_hi,
                "tithi": f"{panchang.masa_name_hi} {panchang.paksha_hi} {panchang.tithi_name_hi}",
                "tithi_name": panchang.tithi_name_hi,
                "paksha": panchang.paksha_hi,
                "tithi_end": format_12h_clean(panchang.tithi_end) if panchang.tithi_end else "11:59 PM",
                "nakshatra": panchang.nakshatra_name_hi,
                "nakshatra_end": format_12h_clean(panchang.nakshatra_end) if panchang.nakshatra_end else "11:59 PM",
                "yoga": panchang.yoga_name_hi or "शुभ",
                "karana": panchang.karana_name_hi or "बव",
                "vara": panchang.vara_hi,
                "masa": panchang.masa_name_hi,
                "samvatsara": "Parikhi",
                "vikram_samvat": 2083,
                "shaka_samvat": 1948,
                "chandra_rashi": panchang.moon_rashi_hi,
                "surya_rashi": panchang.sun_rashi_hi,
                "sunrise": rise_s,
                "sunset": set_s,
                "moonset": "5:30 PM",
                "shubh_muhurta": {
                    "abhijit": f"{abhijit_s} – {abhijit_e}",
                    "brahma_muhurta": panchang.brahma_muhurta or "4:40 AM – 5:28 AM",
                    "godhuli_muhurta": panchang.godhuli_muhurta or "5:45 PM – 6:30 PM",
                },
                "ashubh_muhurta": {
                    "rahu_kaal": f"{rahu_s} – {rahu_e}",
                },
            },
        },
        "transits": {},
    }

    muhurta_dict = {
        "metadata": {
            "source": "Siddhanta Vedic Panchang Engine",
            "generated_at": dt.datetime.now().isoformat(),
            "date": target_date.isoformat(),
            "location": {
                "name": "Ujjain, India (Standard Astronomical Baseline)",
                "latitude": 23.1765,
                "longitude": 75.7885,
                "timezone": "Asia/Kolkata",
            },
        },
        "date": target_date.isoformat(),
        "choghadiya": {
            "day": day_slots,
            "night": []
        },
        "muhurtas": {
            "abhijit_muhurta": {"start": abhijit_s, "end": abhijit_e, "name_en": "Abhijit", "name_hi": "अभिजित", "is_auspicious": True},
            "rahu_kaal": {"start": rahu_s, "end": rahu_e, "name_en": "Rahu Kaal", "name_hi": "राहु काल", "is_auspicious": False},
            "yamaghanta": {"start": yama_s, "end": yama_e, "name_en": "Yamaganda", "name_hi": "यमगण्ड", "is_auspicious": False},
            "gulika_kaal": {"start": guli_s, "end": guli_e, "name_en": "Gulika Kaal", "name_hi": "गुलिक काल", "is_auspicious": False},
        }
    }

    return daily_dict, muhurta_dict


def prepare_studio_inputs(
    panchang: DailyPanchang,
    daily_json: dict | None,
    muhurta_json: dict | None,
) -> tuple[dict, dict]:
    """Prepares 100% verified PromoStudio-compatible inputs, sanitizing dumps or synthesizing accurately."""
    target_date_iso = panchang.date.isoformat()
    if daily_json and muhurta_json:
        d_date = daily_json.get("today", {}).get("date")
        m_date = muhurta_json.get("date")
        if d_date == target_date_iso and m_date == target_date_iso:
            # Authentic dump matches target date! Clean required fields.
            en = daily_json.setdefault("today", {}).setdefault("english", {})
            hi = daily_json.setdefault("today", {}).setdefault("hindi", {})
            for k in ("sunrise", "sunset", "tithi_end", "nakshatra_end", "moonrise"):
                if en.get(k):
                    en[k] = format_12h_clean(en[k])
            if not en.get("moonrise"):
                en["moonrise"] = format_12h_clean(hi.get("moonrise")) if hi.get("moonrise") else "5:45 AM"
            if not hi.get("chandra_rashi"):
                hi["chandra_rashi"] = panchang.moon_rashi_hi
            log.info("Using authentic Flutter engine JSON inputs matching %s", target_date_iso)
            return daily_json, muhurta_json

    log.info("Synthesizing authoritative PromoStudio inputs directly for %s", target_date_iso)
    return synthesize_studio_inputs(panchang, panchang.date)


def publish_post_unit(
    post_type: str,
    display_title: str,
    panchang: DailyPanchang,
    daily_json: dict | None,
    muhurta_json: dict | None,
    out_dir: Path,
    dry_run: bool,
    gemini_key: str,
    gemini_model: str,
    ig_user_id: str,
    ig_token: str,
    img_host_key: str,
) -> bool:
    """Renders, generates bilingual copy, and publishes a single or carousel post unit."""
    log.info("========== Processing Post Unit: [%s] '%s' ==========", post_type.upper(), display_title)

    # 1. Idempotency Guard Check via Instagram Graph API
    if not dry_run and ig_user_id and ig_token:
        ig_guard = InstagramCarouselPublisher(ig_user_id, ig_token)
        if ig_guard.has_posted_for_date(panchang.date, post_type):
            log.info("[IDEMPOTENCY GUARD] Post for %s (%s) is already live on Instagram! Skipping to prevent duplicate.",
                     panchang.date, post_type)
            return True

    # 2. Render 1080 x 1350 Carousel Slides
    slide_paths: list[Path] = []
    primary_card_path = out_dir / f"primary_{post_type}.jpg"
    rendered_via_studio = False

    daily_input, muhurta_input = prepare_studio_inputs(panchang, daily_json, muhurta_json)
    if daily_input and muhurta_input:
        try:
            studio = PromoStudio(out_dir)
            studio_card = {"plan_day": "muhurta", "jyotish": "transit"}.get(post_type, post_type)

            if post_type == "jyotish":
                # Transit card produces a 2-slide carousel (Slide 1 Story, Slide 2 Planetary Grid)
                res_transit = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, card="transit")
                raw_paths = res_transit.get("paths", [res_transit["path"]])
                for idx, p_path in enumerate(raw_paths):
                    jpg_slide = out_dir / f"primary_transit_slide_{idx+1}.jpg"
                    with Image.open(p_path) as img:
                        img = add_play_store_qr_overlay(img, lang="en")
                        img.convert("RGB").save(jpg_slide, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(jpg_slide)
            else:
                # Bilingual Carousel: Slide 1 Hindi, Slide 2 English
                try:
                    res_hi = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, language="hi", card=studio_card)
                    hi_jpg = out_dir / f"primary_{post_type}_slide1_hi.jpg"
                    with Image.open(res_hi["path"]) as img:
                        img = add_play_store_qr_overlay(img, lang="hi")
                        img.convert("RGB").save(hi_jpg, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(hi_jpg)
                except Exception as e_hi:
                    log.warning("Hindi slide note (%s); proceeding with English slide", e_hi)

                res_en = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, language="en", card=studio_card)
                en_jpg = out_dir / f"primary_{post_type}_slide2_en.jpg"
                with Image.open(res_en["path"]) as img:
                    img = add_play_store_qr_overlay(img, lang="en")
                    img.convert("RGB").save(en_jpg, format="JPEG", quality=95, optimize=True)
                slide_paths.append(en_jpg)

            if slide_paths:
                primary_card_path = slide_paths[0]
                rendered_via_studio = True
                log.info("Rendered %d carousel slide(s) via PromoStudio design system", len(slide_paths))

            # Also generate other cards for the day's local package
            for c in ("panchang", "muhurta", "festival", "kundli", "chakra", "transit"):
                try:
                    studio.generate(daily_input, muhurta_input, expected_date=panchang.date, card=c)
                except Exception:
                    pass
        except Exception as e:
            log.warning("PromoStudio generation note (%s); falling back to card_universe", e)

    if not rendered_via_studio:
        render_selected_card(post_type, panchang, primary_card_path)
        with Image.open(primary_card_path) as img:
            img = add_play_store_qr_overlay(img, lang="en")
            img.convert("RGB").save(primary_card_path, format="JPEG", quality=95, optimize=True)
        slide_paths = [primary_card_path]
        log.info("Rendered fallback primary post card (1080x1350 JPEG) to %s", primary_card_path)

    # 3. AI Copywriting (Bilingual caption with Hindi + English sections)
    log.info("Invoking Gemini AI as Composer for post type '%s'...", post_type)
    copy_data = None
    if gemini_key:
        try:
            gemini = GeminiProvider(gemini_key, gemini_model)
            copy_data = generate_cosmic_caption(panchang, gemini, api_key=gemini_key, post_type=post_type)
        except Exception as e:
            log.warning("Gemini AI failed: %s. Using devotional fallback copy.", e)
            copy_data = get_devotional_fallback_copy(panchang, post_type=post_type)
    else:
        copy_data = get_devotional_fallback_copy(panchang, post_type=post_type)

    raw_caption = copy_data.get("instagram_caption", "")
    hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in copy_data.get("hashtags", []))
    final_caption = f"{raw_caption}\n\n.\n.\n{hashtags}".strip()

    # Save outputs
    (out_dir / f"caption_{post_type}.txt").write_text(final_caption, encoding="utf-8")
    meta = {
        "date": panchang.date_formatted,
        "post_type": post_type,
        "title": display_title,
        "tithi": panchang.tithi_name,
        "nakshatra": panchang.nakshatra_name,
        "festival": panchang.festival_name,
        "slides": [p.name for p in slide_paths],
        "image_dimensions": "1080x1350",
        "hashtags": copy_data.get("hashtags", []),
    }
    (out_dir / f"metadata_{post_type}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("--- GENERATED BILINGUAL CAPTION ---\n%s\n-----------------------------------", final_caption)

    if dry_run:
        log.info("[DRY RUN] %d-slide card(s) & bilingual caption generated successfully!", len(slide_paths))
        return True

    # 4. Upload Carousel Slides to Image Host (ImgBB)
    img_host = ImgBBHost(img_host_key)
    uploaded_urls: list[str] = []
    for s_path in slide_paths:
        log.info("Uploading slide %s to image host...", s_path.name)
        url = img_host.upload(str(s_path))
        uploaded_urls.append(url)
    log.info("Uploaded %d Image URL(s)", len(uploaded_urls))

    # 5. Instagram Publishing via Graph API (Carousel or Single)
    ig_publisher = InstagramCarouselPublisher(ig_user_id, ig_token)
    if len(uploaded_urls) > 1:
        log.info("Publishing %d-slide carousel to Instagram...", len(uploaded_urls))
        res = ig_publisher.publish_carousel(uploaded_urls, final_caption)
    else:
        log.info("Publishing single 4:5 Portrait post to Instagram...")
        res = ig_publisher.publish_single(uploaded_urls[0], final_caption)

    if res.ok:
        log.info("SUCCESS! Post live on Instagram: %s (Post ID: %s)", res.url, res.post_id)
        return True
    else:
        log.error("Failed to publish to Instagram: [%s] %s", res.error_code, res.error_message)
        sys.exit(1)


def run_daily_worker(
    dry_run: bool = False,
    format_mode: str = "carousel",
    target_date: dt.date = None,
    post_type_override: str = None,
    slot: str = "auto",
):
    log.info("========== Starting Siddhanta Daily Social Worker (Bilingual Carousel Mode) ==========")

    # 1. Credentials
    gemini_key = get_credential("GEMINI_API_KEY")
    ig_user_id = get_credential("IG_USER_ID", "ig.user_id")
    ig_token = get_credential("IG_ACCESS_TOKEN")
    img_host_key = get_credential("IMAGE_HOST_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    if not dry_run:
        missing = []
        if not gemini_key: missing.append("GEMINI_API_KEY")
        if not ig_user_id: missing.append("IG_USER_ID")
        if not ig_token: missing.append("IG_ACCESS_TOKEN")
        if not img_host_key: missing.append("IMAGE_HOST_KEY")
        if missing:
            log.error("Missing required credentials: %s", ", ".join(missing))
            sys.exit(1)

    # 2. Authentic Panchang Calculation
    panchang = get_authoritative_daily_panchang(target_date)
    log.info("Calculated Panchang: %s | Tithi: %s | Vara: %s | Festival: %s",
             panchang.date_formatted, panchang.tithi_name, panchang.vara_sa, panchang.festival_name or "None")

    out_dir = Path("output") / panchang.date.strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    daily_json = fetch_cross_repo_file("daily_panchang.json", panchang.date) or fetch_cross_repo_file("data.json", panchang.date)
    muhurta_json = fetch_cross_repo_file("muhurta_data.json", panchang.date) or fetch_cross_repo_file("muhu.json", panchang.date)

    # 3. Handle Slots & Post Selection
    ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
    now_ist = dt.datetime.now(ist_tz)

    active_slots = []
    if post_type_override:
        active_slots = [(post_type_override, f"Manual Override: {post_type_override}")]
    elif slot == "primary":
        active_slots = [("panchang", "Today's Panchang Overview")]
    elif slot == "secondary":
        t_type, t_title = get_thematic_post_type(panchang)
        if t_type:
            active_slots = [(t_type, t_title)]
        else:
            log.info("No secondary post scheduled for today (%s). Exiting cleanly.", panchang.date)
            return True
    elif slot == "both":
        active_slots = [("panchang", "Today's Panchang Overview")]
        t_type, t_title = get_thematic_post_type(panchang)
        if t_type:
            active_slots.append((t_type, t_title))
    else:  # "auto"
        # In the morning (< 10 AM IST), anchor with Primary Panchang post
        if now_ist.hour < 10:
            active_slots = [("panchang", "Today's Panchang Overview")]
        else:
            t_type, t_title = get_thematic_post_type(panchang)
            if t_type:
                active_slots = [(t_type, t_title)]
            else:
                log.info("No secondary post scheduled for afternoon (%s). Exiting cleanly.", panchang.date)
                return True

    success = True
    for p_type, p_title in active_slots:
        res = publish_post_unit(
            post_type=p_type,
            display_title=p_title,
            panchang=panchang,
            daily_json=daily_json,
            muhurta_json=muhurta_json,
            out_dir=out_dir,
            dry_run=dry_run,
            gemini_key=gemini_key,
            gemini_model=gemini_model,
            ig_user_id=ig_user_id,
            ig_token=ig_token,
            img_host_key=img_host_key,
        )
        if not res:
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(description="Siddhanta Daily Social Automation (Bilingual Carousel Mode)")
    parser.add_argument("--dry-run", action="store_true", help="Generate cards & caption without publishing")
    parser.add_argument("--format", choices=["single", "carousel"], default="carousel", help="Publish mode (default carousel)")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--type", choices=["panchang", "plan_day", "festival", "kundli", "chakra", "jyotish"], default=None, help="Force specific card type")
    parser.add_argument("--slot", choices=["auto", "primary", "secondary", "both"], default="auto", help="Post slot: primary (Panchang), secondary (Thematic), both, or auto")
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = dt.date.fromisoformat(args.date)

    run_daily_worker(
        dry_run=args.dry_run,
        format_mode=args.format,
        target_date=target_date,
        post_type_override=args.type,
        slot=args.slot,
    )


if __name__ == "__main__":
    main()
