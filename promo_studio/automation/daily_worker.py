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

from promo_studio.automation.panchang_engine import DailyPanchang
from promo_studio.automation.panchang_data_client import get_authoritative_daily_panchang
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


def select_daily_post_type(panchang: DailyPanchang) -> tuple[str, str]:
    """Intelligently selects the single primary post type from the 6-Card Universe.
    
    Priority Hierarchy:
    1. Festival: If today has an active festival, festival card is paramount.
    2. Solar/Lunar Eclipse or Major Planetary Transit: On transit days, Jyotish insight.
    3. Weekday Content Schedule:
       - Tuesday & Thursday: Plan Your Day (Muhurtas, Rahu Kaal, Choghadiya)
       - Saturday: Jyotish Insight or Kundli (Shani / Dasha focus)
       - Sunday: Panchang (Ravivar / Surya focus)
       - Wednesday: Chakra Balance (Mercury / Anahata & Vishuddha balance)
       - Monday: Daily Panchang (Soma / Chandra devotion)
       - Friday: Kundli (Venus / Lagna harmony)
    
    Returns:
        (post_type, display_title)
    """
    # 1. Festival Check
    if panchang.is_festival and panchang.festival_name:
        return "festival", f"Festival Alert: {panchang.festival_name}"

    # 2. Weekday-based Intelligent Selection
    weekday = panchang.date.weekday()  # Monday is 0, Sunday is 6

    if weekday in (1, 3):  # Tuesday, Thursday
        return "plan_day", "Plan Your Day Wisely"
    elif weekday == 5:     # Saturday
        return "kundli", "Your Kundli & Dasha Journey"
    elif weekday == 2:     # Wednesday
        return "chakra", "Balance Your Inner Energy (Chakras)"
    elif weekday == 4:     # Friday
        return "jyotish", "Jyotish Transit Insight"
    else:                  # Monday, Sunday
        return "panchang", "Today's Panchang Overview"


def render_selected_card(post_type: str, panchang: DailyPanchang, out_path: Path) -> Path:
    """Renders the single selected card at 1080 x 1350."""
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


def run_daily_worker(dry_run: bool = False, format_mode: str = "single", target_date: dt.date = None, post_type_override: str = None):
    log.info("========== Starting Siddhanta Daily Social Worker (4:5 Feed Mode) ==========")

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

    # 2. Authentic Panchang Calculation (Ingests Flutter dumps with fallback)
    panchang = get_authoritative_daily_panchang(target_date)
    log.info("Calculated Panchang: %s | Tithi: %s | Vara: %s | Festival: %s",
             panchang.date_formatted, panchang.tithi_name, panchang.vara_sa, panchang.festival_name or "None")

    # 3. Intelligent Content Selection
    if post_type_override:
        post_type = post_type_override
        display_title = f"Manual Override: {post_type}"
    else:
        post_type, display_title = select_daily_post_type(panchang)
    
    log.info("Selected Primary Post for Today: [%s] '%s'", post_type.upper(), display_title)

    # 4. Render 1080 x 1350 Primary Card
    out_dir = Path("output") / panchang.date.strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    primary_card_path = out_dir / f"primary_{post_type}.png"
    render_selected_card(post_type, panchang, primary_card_path)
    log.info("Rendered primary post card (1080x1350) to %s", primary_card_path)

    # Also render all 6 cards for reference/download package (and Hindi variant)
    render_card_1_panchang(panchang, out_dir / "card1_panchang.png", lang="en")
    render_card_1_panchang(panchang, out_dir / "card1_panchang_hindi.png", lang="hi")
    render_card_2_plan_day(panchang, out_dir / "card2_plan_day.png")
    render_card_3_festival(panchang, out_dir / "card3_festival.png")
    render_card_4_kundli(panchang, out_dir / "card4_kundli.png")
    render_card_5_chakra(out_dir / "card5_chakra.png")
    render_card_6_jyotish(panchang, out_dir / "card6_jyotish.png")

    # 5. AI Copywriting (Gemini as Writer/Composer tailored to the chosen card)
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
    (out_dir / "caption.txt").write_text(final_caption, encoding="utf-8")
    meta = {
        "date": panchang.date_formatted,
        "post_type": post_type,
        "title": display_title,
        "tithi": panchang.tithi_name,
        "nakshatra": panchang.nakshatra_name,
        "festival": panchang.festival_name,
        "image_file": primary_card_path.name,
        "image_dimensions": "1080x1350",
        "hashtags": copy_data.get("hashtags", []),
    }
    (out_dir / "post_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("--- GENERATED CAPTION ---\n%s\n-------------------------", final_caption)

    if dry_run:
        log.info("[DRY RUN] Primary 1080x1350 card & caption generated successfully!")
        return True

    # 6. Image Hosting Upload (ImgBB)
    img_host = ImgBBHost(img_host_key)
    log.info("Uploading primary 1080x1350 card to image host...")
    card_url = img_host.upload(str(primary_card_path))
    log.info("Uploaded Image: %s", card_url)

    # 7. Instagram Publishing via Graph API (Single 4:5 Portrait Feed Post)
    log.info("Publishing single 4:5 Portrait post to Instagram...")
    ig_publisher = InstagramCarouselPublisher(ig_user_id, ig_token)
    res = ig_publisher.publish_single(card_url, final_caption)

    if res.ok:
        log.info("SUCCESS! Post live on Instagram: %s (Post ID: %s)", res.url, res.post_id)
        return True
    else:
        log.error("Failed to publish to Instagram: [%s] %s", res.error_code, res.error_message)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Siddhanta Daily Social Automation (4:5 Feed Mode)")
    parser.add_argument("--dry-run", action="store_true", help="Generate 1080x1350 card & caption without posting")
    parser.add_argument("--format", choices=["single", "carousel"], default="single", help="Publish mode (default single 4:5)")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--type", choices=["panchang", "plan_day", "festival", "kundli", "chakra", "jyotish"], default=None, help="Force specific card type")
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = dt.date.fromisoformat(args.date)

    run_daily_worker(dry_run=args.dry_run, format_mode=args.format, target_date=target_date, post_type_override=args.type)


if __name__ == "__main__":
    main()
