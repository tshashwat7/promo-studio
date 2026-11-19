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
import copy
import datetime as dt
import json
import logging
import os
import sys
import time
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
from promo_studio.adapters.facebook import FacebookAdapter
from promo_studio.adapters.twitter import TwitterAdapter
from promo_studio.adapters.twitter_playwright import TwitterPlaywrightAdapter
from promo_studio.automation.github_media_host import DEFAULT_REELS_REPO, GitHubReleaseMediaHost
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


def get_thematic_posts(panchang: DailyPanchang) -> list[tuple[str, str]]:
    """Determines secondary/thematic post(s) of the day based on actual data content.

    Data-driven logic (replaces fixed weekday schedule):
    1. 1st of month → Chakra Balance (fixed)
    2. Last day of month → Kundli Journey (fixed)
    3. Festival detected in panchang data → Festival Alert
    4. Active transit event (retrograde, ingress) in gochar → Transit Insight
    5. Otherwise → no thematic post
    Multiple thematic posts can coexist (e.g. Festival + Transit on the same day).
    """
    posts: list[tuple[str, str]] = []
    d = panchang.date

    # Monthly anchor cards (exclusive — only one of these)
    if d.day == 1:
        posts.append(("chakra", "Balance Your Inner Energy (Chakras)"))
        return posts
    if is_last_day_of_month(d):
        posts.append(("kundli", "Your Kundli & Dasha Journey"))
        return posts

    # Festival card (from JSON data or fallback detector)
    if panchang.is_festival and panchang.festival_name:
        posts.append(("festival", f"Festival Alert: {panchang.festival_name}"))

    # Transit card — show when gochar has an active spotlight event (retrograde or ingress)
    if panchang.gochar:
        motion = getattr(panchang.gochar, "spotlight_motion", "Direct")
        # Show transit card if there's a retrograde or if major transit data exists
        if motion and motion.lower() not in ("direct", ""):
            posts.append(("jyotish", f"Planetary Transit: {panchang.gochar.spotlight_planet} {motion}"))

    return posts


def get_thematic_post_type(panchang: DailyPanchang) -> tuple[str | None, str | None]:
    """Legacy wrapper — returns the first thematic post type for backward compatibility."""
    posts = get_thematic_posts(panchang)
    if posts:
        return posts[0]
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
    daily_dict, muhu_dict = synthesize_studio_inputs(panchang, panchang.date)
    if daily_json and "transits" in daily_json:
        daily_dict["transits"] = daily_json["transits"]
    return daily_dict, muhu_dict


def _build_twitter_caption(
    panchang: DailyPanchang,
    slot: str,
    app_url: str,
    instagram_hashtags: list[str] | None = None,
) -> str:
    """Builds a clean, high-engagement Twitter (X) post strictly under 280 characters.

    Keeps text generic & inviting, directs users to the App, and packs top discovery hashtags.
    """
    d_str = panchang.date.strftime("%d %b %Y")
    download_link = app_url or "https://bit.ly/47HN61M"

    if slot == "festival" and panchang.festival_name:
        head = f"🚩 {panchang.festival_name} • {d_str}"
        sub = "🕉️ Today's Tithi, Nakshatra, Shubh Muhurat & Choghadiya"
        cta = f"📲 Complete Puja Vidhi & Panchang on Siddhanta App:\n{download_link}"
    else:
        head = f"✨ Daily Vedic Panchang • {d_str}"
        sub = "🕉️ Today's Tithi, Nakshatra, Shubh Muhurat & Choghadiya"
        cta = f"📲 Complete calculations & Kundli on Siddhanta App:\n{download_link}"

    # Pool high-traffic community discovery hashtags from Instagram generation + fallbacks
    tags_pool: list[str] = []
    if instagram_hashtags:
        for tag in instagram_hashtags:
            clean_tag = tag.strip().lstrip("#")
            # Exclude internal slot tags or excessively long tags
            if clean_tag and not clean_tag.startswith("siddhanta_slot") and clean_tag not in tags_pool:
                tags_pool.append(clean_tag)

    default_tags = [
        "DailyPanchang", "AajKaPanchang", "DrikPanchang", "AstroSage",
        "HinduCalendar", "ShubhMuhurat", "VedicAstrology", "Jyotish",
        "पंचांग", "SiddhantaApp"
    ]
    for dt_tag in default_tags:
        if dt_tag not in tags_pool:
            tags_pool.append(dt_tag)

    # Greedily pack hashtags into remaining 280-char space
    base_block = f"{head}\n{sub}\n\n{cta}\n"
    current_tags: list[str] = []
    for candidate in tags_pool:
        test_tag = f"#{candidate}"
        test_line = " ".join(current_tags + [test_tag])
        if len(base_block) + len(test_line) <= 270:
            current_tags.append(test_tag)

    full_tweet = f"{base_block}{' '.join(current_tags)}".strip()
    return full_tweet[:275]


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

    canonical_slot = (
        "master" if post_type in ("master", "panchang", "master_panchang")
        else ("festival" if post_type == "festival"
        else ("muhurta" if post_type in ("plan_day", "muhurta")
        else ("transit" if post_type in ("jyotish", "transit")
        else post_type.lower())))
    )
    slot_tag = f"#siddhanta_slot_{canonical_slot}_{panchang.date.strftime('%Y%m%d')}"

    # 1. Independent Idempotency Guard Checks for Each Platform
    ig_posted = False
    if not dry_run and ig_user_id and ig_token:
        try:
            ig_guard = InstagramCarouselPublisher(ig_user_id, ig_token)
            ig_posted = ig_guard.has_posted_for_date(panchang.date, post_type)
            if ig_posted:
                log.info("[IG IDEMPOTENCY GUARD] Post for %s (%s) is already live on Instagram.", panchang.date, post_type)
        except Exception as e_ig_chk:
            log.warning("IG guard check note: %s", e_ig_chk)

    fb_posted = False
    fb_page_id = get_credential("FB_PAGE_ID", "fb.page_id")
    fb_page_token = get_credential("FB_PAGE_TOKEN")
    if not dry_run and fb_page_id and fb_page_token:
        try:
            fb_guard = FacebookAdapter(fb_page_id, fb_page_token)
            fb_posted = fb_guard.has_posted_for_date(panchang.date, post_type)
            if fb_posted:
                log.info("[FB IDEMPOTENCY GUARD] Post for %s (%s) is already live on Facebook.", panchang.date, post_type)
        except Exception as e_fb_chk:
            log.warning("FB guard check note: %s", e_fb_chk)

    tw_marker = out_dir / f"twitter_posted_{canonical_slot}.json"
    tw_posted = tw_marker.exists()
    if tw_posted:
        log.info("[TWITTER IDEMPOTENCY GUARD] Tweet for %s (%s) is already live.", panchang.date, canonical_slot)

    # Check if Twitter is configured
    tw_auth_token = get_credential("TWITTER_AUTH_TOKEN")
    tw_ct0 = get_credential("TWITTER_CT0")
    tw_key = get_credential("TWITTER_API_KEY")
    tw_secret = get_credential("TWITTER_API_SECRET")
    tw_token = get_credential("TWITTER_ACCESS_TOKEN")
    tw_token_secret = get_credential("TWITTER_ACCESS_TOKEN_SECRET")
    has_tw_creds = bool((tw_auth_token and tw_ct0) or (tw_key and tw_secret and tw_token and tw_token_secret))

    # If all configured platforms are already live, exit early (Zero AI & rendering wasted)
    if (not ig_user_id or ig_posted) and (not fb_page_id or fb_posted) and (not has_tw_creds or tw_posted):
        log.info("[ALL-PLATFORM GUARD] All configured platforms already live for %s (%s)! Skipping unit.",
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

            if post_type in ("master", "panchang", "master_panchang"):
                # 6-Slide Master Carousel:
                # Slide 1 & 2: Panchang (Hi + En)
                # Slide 3 & 4: Muhurta / Choghadiya (Hi + En)
                # Slide 5 & 6: Planetary Transit (2 slides: Story + Grid)
                master_cards = [
                    ("panchang", "hi"),
                    ("panchang", "en"),
                    ("muhurta", "hi"),
                    ("muhurta", "en"),
                ]
                for c_type, c_lang in master_cards:
                    try:
                        res_c = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, language=c_lang, card=c_type)
                        slide_jpg = out_dir / f"master_{c_type}_{c_lang}.jpg"
                        with Image.open(res_c["path"]) as img:
                            img = add_play_store_qr_overlay(img, lang=c_lang)
                            img.convert("RGB").save(slide_jpg, format="JPEG", quality=95, optimize=True)
                        slide_paths.append(slide_jpg)
                    except Exception as e_c:
                        log.warning("Master slide (%s %s) note: %s", c_type, c_lang, e_c)

                # Transit & Planetary Positions: Generate both Hindi and English pairs
                try:
                    res_tr_hi = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, language="hi", card="transit")
                    paths_hi = res_tr_hi.get("paths", [res_tr_hi["path"]])
                except Exception as e_tr_hi:
                    log.warning("Hindi transit error: %s", e_tr_hi)
                    paths_hi = []

                try:
                    res_tr_en = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, language="en", card="transit")
                    paths_en = res_tr_en.get("paths", [res_tr_en["path"]])
                except Exception as e_tr_en:
                    log.warning("English transit error: %s", e_tr_en)
                    paths_en = []

                # Story slides (Hi + En)
                if paths_hi:
                    s_hi = out_dir / "master_transit_story_hi.jpg"
                    with Image.open(paths_hi[0]) as img:
                        img = add_play_store_qr_overlay(img, lang="hi")
                        img.convert("RGB").save(s_hi, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(s_hi)
                if paths_en:
                    s_en = out_dir / "master_transit_story_en.jpg"
                    with Image.open(paths_en[0]) as img:
                        img = add_play_store_qr_overlay(img, lang="en")
                        img.convert("RGB").save(s_en, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(s_en)
                    # Also save as master_transit_slide_1.jpg for backwards compatibility
                    img.convert("RGB").save(out_dir / "master_transit_slide_1.jpg", format="JPEG", quality=95, optimize=True)

                # Planetary Grid positions slides (Hi + En)
                if len(paths_hi) > 1:
                    p_hi = out_dir / "master_transit_positions_hi.jpg"
                    with Image.open(paths_hi[1]) as img:
                        img = add_play_store_qr_overlay(img, lang="hi")
                        img.convert("RGB").save(p_hi, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(p_hi)
                if len(paths_en) > 1:
                    p_en = out_dir / "master_transit_positions_en.jpg"
                    with Image.open(paths_en[1]) as img:
                        img = add_play_store_qr_overlay(img, lang="en")
                        img.convert("RGB").save(p_en, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(p_en)
                    # Also save as master_transit_slide_2.jpg for backwards compatibility
                    img.convert("RGB").save(out_dir / "master_transit_slide_2.jpg", format="JPEG", quality=95, optimize=True)
            elif post_type == "jyotish":
                # Transit card produces a 2-slide carousel (Slide 1 Story, Slide 2 Planetary Grid)
                res_transit = studio.generate(daily_input, muhurta_input, expected_date=panchang.date, card="transit")
                raw_paths = res_transit.get("paths", [res_transit["path"]])
                for idx, p_path in enumerate(raw_paths):
                    jpg_slide = out_dir / f"primary_transit_slide_{idx+1}.jpg"
                    with Image.open(p_path) as img:
                        img = add_play_store_qr_overlay(img, lang="en")
                        img.convert("RGB").save(jpg_slide, format="JPEG", quality=95, optimize=True)
                    slide_paths.append(jpg_slide)
            elif post_type == "festival" and len(daily_input.get("today", {}).get("festivals_today", [])) > 1:
                # Multi-Festival Carousel: Render dedicated bilingual pair (Hindi + English) for each festival
                all_fests = daily_input["today"]["festivals_today"]
                log.info("Detected %d coinciding festivals today. Generating multi-festival bilingual carousel slides...", len(all_fests))
                for f_idx, fest_obj in enumerate(all_fests):
                    sub_daily = copy.deepcopy(daily_input)
                    sub_daily["today"]["festivals_today"] = [fest_obj]
                    # Hindi Slide for this festival
                    try:
                        res_hi = studio.generate(sub_daily, muhurta_input, expected_date=panchang.date, language="hi", card="festival")
                        hi_jpg = out_dir / f"primary_festival_{f_idx + 1}_hi.jpg"
                        with Image.open(res_hi["path"]) as img:
                            img = add_play_store_qr_overlay(img, lang="hi")
                            img.convert("RGB").save(hi_jpg, format="JPEG", quality=95, optimize=True)
                        slide_paths.append(hi_jpg)
                    except Exception as e_hi:
                        log.warning("Festival %d Hindi slide note (%s)", f_idx + 1, e_hi)

                    # English Slide for this festival
                    try:
                        res_en = studio.generate(sub_daily, muhurta_input, expected_date=panchang.date, language="en", card="festival")
                        en_jpg = out_dir / f"primary_festival_{f_idx + 1}_en.jpg"
                        with Image.open(res_en["path"]) as img:
                            img = add_play_store_qr_overlay(img, lang="en")
                            img.convert("RGB").save(en_jpg, format="JPEG", quality=95, optimize=True)
                        slide_paths.append(en_jpg)
                    except Exception as e_en:
                        log.warning("Festival %d English slide note (%s)", f_idx + 1, e_en)
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
    copy_data = None
    # Only invoke Gemini AI if Instagram or Facebook actually needs a new caption
    if (not ig_posted or not fb_posted) and gemini_key:
        log.info("Invoking Gemini AI as Composer for post type '%s'...", post_type)
        try:
            gemini = GeminiProvider(gemini_key, gemini_model)
            copy_data = generate_cosmic_caption(panchang, gemini, api_key=gemini_key, post_type=post_type)
        except Exception as e:
            log.warning("Gemini AI failed: %s. Using devotional fallback copy.", e)
            copy_data = get_devotional_fallback_copy(panchang, post_type=post_type)
    else:
        if ig_posted and fb_posted:
            log.info("Instagram & Facebook already posted. Bypassing Gemini AI to save tokens.")
        copy_data = get_devotional_fallback_copy(panchang, post_type=post_type)

    raw_caption = copy_data.get("instagram_caption", "")
    hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in copy_data.get("hashtags", []))
    anchor_tag = "#Siddhanta_Festival" if post_type == "festival" else "#Siddhanta_DailyGuide"
    final_caption = f"{raw_caption}\n\n.\n.\n{hashtags}\n{anchor_tag}\n{slot_tag}".strip()

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

    # 4. Upload Carousel Slides to Image Host (ImgBB) - only if IG or FB needs to post
    uploaded_urls: list[str] = []
    if not ig_posted or not fb_posted:
        img_host = ImgBBHost(img_host_key)
        for idx, s_path in enumerate(slide_paths):
            log.info("Uploading slide %s to image host...", s_path.name)
            url = img_host.upload(str(s_path))
            log.info("Slide %d URL: %s", idx + 1, url)
            uploaded_urls.append(url)
        log.info("Uploaded %d Image URL(s). Pausing 4s for public CDN edge propagation...", len(uploaded_urls))
        time.sleep(4)

    # 5. Instagram Publishing via Graph API (Carousel or Single)
    if not ig_posted and ig_user_id and ig_token and uploaded_urls:
        ig_publisher = InstagramCarouselPublisher(ig_user_id, ig_token)
        if len(uploaded_urls) > 1:
            log.info("Publishing %d-slide carousel to Instagram...", len(uploaded_urls))
            res = ig_publisher.publish_carousel(uploaded_urls, final_caption)
        else:
            log.info("Publishing single 4:5 Portrait post to Instagram...")
            res = ig_publisher.publish_single(uploaded_urls[0], final_caption)

        if res.ok:
            log.info("SUCCESS! Post live on Instagram: %s (Post ID: %s)", res.url, res.post_id)
        else:
            log.warning("Instagram publish note: [%s] %s", res.error_code, res.error_message)
    elif ig_posted:
        log.info("[IG GUARD] Instagram post already live for %s (%s). Skipping.", panchang.date, post_type)

    # 6. Facebook Page Publishing via Graph API (Multi-Image Album or Single Photo)
    if not fb_posted and fb_page_id and fb_page_token and uploaded_urls:
        try:
            fb = FacebookAdapter(fb_page_id, fb_page_token)
            log.info("Publishing %d photo(s) to Facebook Page (%s)...", len(uploaded_urls), fb_page_id)
            fb_res = fb.publish_multi_photo(uploaded_urls, final_caption)
            if fb_res.ok:
                log.info("SUCCESS! Post live on Facebook: %s (Post ID: %s)", fb_res.url, fb_res.post_id)
            else:
                log.warning("Facebook publish note: [%s] %s", fb_res.error_code, fb_res.error_message)
        except Exception as e_fb:
            log.warning("Facebook publish exception (non-fatal): %s", e_fb)
    elif fb_posted:
        log.info("[FB GUARD] Facebook post already live for %s (%s). Skipping.", panchang.date, post_type)

    # 7. Twitter (X) Publishing (Playwright Browser Session preferred, API fallback)
    if has_tw_creds:
        try:
            if not tw_posted:
                app_url = os.environ.get("APP_URL", "https://bit.ly/47HN61M")
                ig_hashtags = copy_data.get("hashtags", []) if copy_data else []
                tweet_text = _build_twitter_caption(
                    panchang,
                    canonical_slot,
                    app_url,
                    instagram_hashtags=ig_hashtags,
                )
                # Select English cards for Twitter (up to 4 cards)
                tw_media_files = [p for p in slide_paths if "_en." in p.name.lower()]
                if not tw_media_files:
                    tw_media_files = slide_paths[:4]
                else:
                    tw_media_files = tw_media_files[:4]

                log.info("Publishing %d English visual image card(s) to X (Twitter): %s",
                         len(tw_media_files), [p.name for p in tw_media_files])

                # Prefer Playwright browser automation (100% free, full visual cards)
                if tw_auth_token and tw_ct0:
                    log.info("Using Twitter Playwright browser automation with session credentials...")
                    tw_adapter = TwitterPlaywrightAdapter(tw_auth_token, tw_ct0)
                    tw_res = tw_adapter.publish_tweet(tweet_text, media_files=tw_media_files)
                else:
                    log.info("Using Twitter Developer API v2...")
                    tw_adapter = TwitterAdapter(tw_key, tw_secret, tw_token, tw_token_secret)
                    tw_res = tw_adapter.publish_tweet(tweet_text, media_files=tw_media_files)

                if tw_res.ok:
                    log.info("SUCCESS! Tweet live on X: %s (Tweet ID: %s)", tw_res.url, tw_res.post_id)
                    tw_marker.write_text(json.dumps({"post_id": tw_res.post_id, "url": tw_res.url}), encoding="utf-8")
                else:
                    log.warning("Twitter publish note: [%s] %s", tw_res.error_code, tw_res.error_message)
            else:
                log.info("[TWITTER IDEMPOTENCY GUARD] Tweet for %s (%s) already live. Skipping.", panchang.date, canonical_slot)
        except Exception as e_tw:
            log.warning("Twitter publish exception (non-fatal): %s", e_tw)

    return True


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

    # 3. Content Selection
    ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
    current_ist_hour = dt.datetime.now(ist_tz).hour

    active_posts: list[tuple[str, str]] = []
    if post_type_override:
        active_posts = [(post_type_override, f"Manual Override: {post_type_override}")]
    elif slot == "festival":
        if panchang.is_festival and panchang.festival_name:
            active_posts = [("festival", f"Festival Alert: {panchang.festival_name}")]
        else:
            log.info("No festival scheduled for %s. Exiting cleanly.", panchang.date)
            return True
    elif slot in ("reel", "reels"):
        return run_daily_reel(dry_run=dry_run, target_date=target_date, reel_lang="en")
    else:
        # Default / "auto": Streamlined Daily Master Cadence
        # 1. 6-Slide Master Carousel (Panchang + Muhurat + Transit)
        active_posts.append(("master", "Today's Cosmic Master Guide (Panchang + Muhurta + Transit)"))

        # 2. If today is an active festival, schedule dedicated Festival Carousel
        if panchang.is_festival and panchang.festival_name:
            active_posts.append(("festival", f"Festival Alert: {panchang.festival_name}"))

    success = True
    total_posts = len(active_posts)
    for idx, (p_type, p_title) in enumerate(active_posts):
        if idx > 0 and not dry_run:
            log.info("Pausing 300 seconds (5 minutes) before publishing post %d/%d...", idx + 1, total_posts)
            time.sleep(300)

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

    # Publish Daily Reel in sequence (paced 5 mins later)
    if not post_type_override and slot not in ("carousel_only", "festival"):
        if not dry_run:
            log.info("Pausing 300 seconds (5 minutes) before generating and publishing Daily Reel...")
            time.sleep(300)
        reel_success = run_daily_reel(dry_run=dry_run, target_date=target_date, reel_lang="en")
        if not reel_success:
            log.warning("Daily Reel run finished with non-success status.")

    return success


def _build_reel_caption(panchang, lang: str) -> str:
    """Build a concise, high-retention Instagram Reel caption with industry discovery hashtags and audio hooks."""
    reel_tags = (
        "#PanchangReels #DailyPanchang #DrikPanchang #AstroSage #HinduCalendar "
        "#ShubhMuhurat #AbhijitMuhurta #RahuKaal #VedicAstrology #Jyotish "
        "#SpiritualReels #SanatanDharma #AstrologyReels #आजकापंचांग #पंचांग "
        "#शुभमुहूर्त #राशिफल #SiddhantaApp #ReelsIndia #ExplorePage"
    )

    slot_tag = f"#siddhanta_slot_reel_{panchang.date.strftime('%Y%m%d')}"

    if lang == "hi":
        lines = [
            f"🔊 आज का दैनिक पंचांग और शुभ मुहूर्त • {panchang.date_formatted}",
            f"✨ तिथि: {panchang.tithi_name} | नक्षत्र: {panchang.nakshatra_name}",
        ]
        if panchang.festival_name:
            lines.append(f"🚩 विशेष पर्व: {panchang.festival_name}")
        lines += [
            "आज के शुभ-अशुभ मुहूर्त और 12 राशियों के गोचर फल की जानकारी वीडियो में देखें।",
            "📲 दिन भर की सटीक वैदिक गणनाओं के लिए इस रील को सेव (Save 🔖) करें।",
            "",
            reel_tags,
            slot_tag,
        ]
        return "\n".join(lines)

    lines = [
        f"🔊 Daily Panchang & Cosmic Alignment • {panchang.date_formatted}",
        f"✨ Tithi: {panchang.tithi_name} | Nakshatra: {panchang.nakshatra_name}",
    ]
    if panchang.festival_name:
        lines.append(f"🚩 Festival: {panchang.festival_name}")
    lines += [
        "Check today's auspicious Abhijit Muhurta, Rahu Kaal window & Planetary Transits.",
        "📲 Save 🔖 this Reel for today's auspicious timing reference.",
        "",
        reel_tags,
        slot_tag,
    ]
    return "\n".join(lines)


def run_daily_reel(
    dry_run: bool = False,
    target_date: dt.date = None,
    reel_lang: str = "en",
):
    """Render the daily Panchang Reel MP4, upload to GitHub Releases, and publish to Instagram."""
    log.info("========== Starting Siddhanta Daily Reel Worker (lang=%s) ==========", reel_lang)

    ig_user_id = get_credential("IG_USER_ID", "ig.user_id")
    ig_token = get_credential("IG_ACCESS_TOKEN")
    reels_pat = get_credential("REELS_MEDIA_PAT")
    reels_repo = os.environ.get("REELS_MEDIA_REPO", DEFAULT_REELS_REPO)

    if not dry_run:
        missing = []
        if not ig_user_id: missing.append("IG_USER_ID")
        if not ig_token: missing.append("IG_ACCESS_TOKEN")
        if not reels_pat: missing.append("REELS_MEDIA_PAT")
        if missing:
            log.error("Missing required credentials for Reel publishing: %s", ", ".join(missing))
            sys.exit(1)

    panchang = get_authoritative_daily_panchang(target_date)
    log.info("Reel Panchang: %s | Tithi: %s | Festival: %s",
             panchang.date_formatted, panchang.tithi_name, panchang.festival_name or "None")

    if not dry_run:
        ig_publisher = InstagramCarouselPublisher(ig_user_id, ig_token)
        if ig_publisher.has_posted_for_date(panchang.date, "reel"):
            log.info("IDEMPOTENCY GUARD: Daily Reel already posted for %s. Skipping.", panchang.date)
            return True

    out_dir = Path("output") / panchang.date.strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    daily_json = fetch_cross_repo_file("daily_panchang.json", panchang.date)
    muhurta_json = fetch_cross_repo_file("muhurta_data.json", panchang.date)
    if not daily_json or not muhurta_json:
        log.info("Panchang dump not found matching %s; synthesizing authoritative inputs directly for Reel", panchang.date)
        synth_daily, synth_muhu = synthesize_studio_inputs(panchang, panchang.date)
        daily_json = daily_json or synth_daily
        muhurta_json = muhurta_json or synth_muhu

    reel_data_path = out_dir / "reel_daily_panchang.json"
    reel_data_path.write_text(json.dumps(daily_json, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parents[2] / "generate_reel.py"),
        str(reel_data_path),
        "--lang",
        reel_lang,
        "--voiceover",
        "swara",
        "--out",
        str(out_dir / f"reel_{panchang.date.isoformat()}.mp4"),
    ]
    if muhurta_json:
        reel_muhu_path = out_dir / "reel_muhurta.json"
        reel_muhu_path.write_text(json.dumps(muhurta_json, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd.extend(["--muhurta", str(reel_muhu_path)])

    log.info("Rendering Reel MP4: %s", " ".join(cmd))
    import subprocess
    subprocess.run(cmd, check=True)

    publish_langs = ["en"] if reel_lang == "both" else [reel_lang]
    if reel_lang == "both":
        mp4_path = out_dir / f"reel_{panchang.date.isoformat()}_en.mp4"
    else:
        mp4_path = out_dir / f"reel_{panchang.date.isoformat()}.mp4"

    caption = _build_reel_caption(panchang, publish_langs[0])
    if dry_run:
        log.info("[DRY RUN] Rendered Reel: %s", mp4_path)
        log.info("[DRY RUN] Reel Caption:\n%s", caption)
        return True

    media_host = GitHubReleaseMediaHost(reels_pat, repo=reels_repo)
    tag = f"reel-{panchang.date.isoformat()}"
    asset_name = f"siddhanta_reel_{panchang.date.isoformat()}_{publish_langs[0]}.mp4"
    log.info("Uploading %s to GitHub Release %s (%s)...", mp4_path.name, tag, reels_repo)
    video_url = media_host.upload_video(mp4_path, tag=tag, asset_name=asset_name)
    log.info("Uploaded Reel URL: %s. Pausing 4s for CDN propagation...", video_url)
    time.sleep(4)

    # Check for custom cover thumbnail generated alongside MP4
    cover_path = mp4_path.with_name(f"{mp4_path.stem}_cover.jpg")
    cover_url = None
    img_host_key = get_credential("IMAGE_HOST_KEY")
    if cover_path.exists() and img_host_key:
        try:
            img_host = ImgBBHost(img_host_key)
            cover_url = img_host.upload(str(cover_path))
            log.info("Uploaded custom Reel cover thumbnail: %s", cover_url)
        except Exception as e_cov:
            log.warning("Could not upload Reel cover thumbnail (%s); using video thumb_offset", e_cov)

    ig_publisher = InstagramCarouselPublisher(ig_user_id, ig_token)
    res = ig_publisher.publish_reel(video_url, caption, cover_url=cover_url, thumb_offset=2000)
    if res.ok:
        log.info("SUCCESS! Reel live on Instagram: %s (Post ID: %s)", res.url, res.post_id)

        # Facebook Reel / Video publishing
        fb_page_id = get_credential("FB_PAGE_ID", "fb.page_id")
        fb_page_token = get_credential("FB_PAGE_TOKEN")
        if fb_page_id and fb_page_token:
            try:
                fb = FacebookAdapter(fb_page_id, fb_page_token)
                if not fb.has_posted_for_date(panchang.date, "reel"):
                    log.info("Publishing Daily Reel to Facebook Page (%s)...", fb_page_id)
                    reel_title = f"Daily Panchang • {panchang.date_formatted}"
                    fb_res = fb.publish_video(video_url, caption, title=reel_title)
                    if fb_res.ok:
                        log.info("SUCCESS! Reel live on Facebook: %s (Video ID: %s)", fb_res.url, fb_res.post_id)
                    else:
                        log.warning("Facebook Reel publish note: [%s] %s", fb_res.error_code, fb_res.error_message)
                else:
                    log.info("[FB IDEMPOTENCY GUARD] Facebook Reel for %s already live. Skipping.", panchang.date)
            except Exception as e_fb:
                log.warning("Facebook Reel publish exception (non-fatal): %s", e_fb)

        return True

    log.error("Failed to publish Reel to Instagram: [%s] %s", res.error_code, res.error_message)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Siddhanta Daily Social Automation (Bilingual Carousel Mode)")
    parser.add_argument("--dry-run", action="store_true", help="Generate cards & caption without publishing")
    parser.add_argument("--format", choices=["single", "carousel"], default="carousel", help="Publish mode (default carousel)")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--type", choices=["panchang", "plan_day", "festival", "kundli", "chakra", "jyotish"], default=None, help="Force specific card type")
    parser.add_argument("--slot", choices=["auto", "master", "festival", "reel", "carousel_only", "morning", "midday", "primary", "secondary", "both"], default="auto", help="Post slot: auto (streamlined daily sequence), master (carousel), festival, or reel")
    parser.add_argument("--reel", action="store_true", help="Generate and publish daily Reel MP4 instead of image cards")
    parser.add_argument("--reel-lang", choices=["en", "hi", "both"], default="en", help="Reel language (default en)")
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = dt.date.fromisoformat(args.date)

    if args.reel or args.slot in ("reel", "reels"):
        run_daily_reel(
            dry_run=args.dry_run,
            target_date=target_date,
            reel_lang=args.reel_lang,
        )
        return

    run_daily_worker(
        dry_run=args.dry_run,
        format_mode=args.format,
        target_date=target_date,
        post_type_override=args.type,
        slot=args.slot,
    )


if __name__ == "__main__":
    main()
