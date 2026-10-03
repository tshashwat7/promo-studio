"""Master Daily Cosmic Blueprint Worker.

Runs the complete automated pipeline:
1. Computes today's Siddhanta Panchang & 7-day rotation theme
2. Generates Material 3 Saffron & Gold visual cards (Pillow)
3. Prompts Gemini AI for authentic Vedic caption & hashtags
4. Uploads images to ImgBB
5. Publishes Carousel / 4:5 Portrait to Instagram (& Facebook if configured)

Can be executed locally or in GitHub Actions at 6:00 AM IST.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from pathlib import Path

from promo_studio.automation.panchang_engine import calculate_daily_panchang
from promo_studio.automation.card_generator import (
    generate_slide_1_hook,
    generate_slide_2_value,
    generate_combined_card
)
from promo_studio.automation.ai_blueprint import generate_cosmic_caption
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

    # Fallback to local PromoStudio keyring/settings if available
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


def run_daily_worker(dry_run: bool = False, format_mode: str = "carousel", target_date: dt.date = None):
    log.info("========== Starting Siddhanta Daily Cosmic Blueprint Worker ==========")

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

    # 2. Panchang Calculation
    panchang = calculate_daily_panchang(target_date)
    log.info("Calculated Panchang: %s | Tithi: %s | Vara: %s | Theme: %s",
             panchang.date_formatted, panchang.tithi_name, panchang.vara_sa, panchang.content_theme)

    # 3. Card Generation (Full 6-Card Universe)
    out_dir = Path("output") / panchang.date.strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    slide1_path = out_dir / "slide1_hook.png"
    slide2_path = out_dir / "slide2_value.png"
    combined_path = out_dir / "combined_card.png"

    from promo_studio.automation.card_universe import (
        render_card_1_panchang,
        render_card_2_plan_day,
        render_card_3_festival,
        render_card_4_kundli,
        render_card_5_chakra,
        render_card_6_jyotish,
    )

    # Carousel slides
    render_card_1_panchang(panchang, slide1_path)
    render_card_2_plan_day(panchang, slide2_path)
    render_card_6_jyotish(panchang, combined_path)

    # Complete Universe Cards for artifact downloads
    render_card_3_festival(panchang, out_dir / "card3_festival.png")
    render_card_4_kundli(panchang, out_dir / "card4_kundli.png")
    render_card_5_chakra(out_dir / "card5_chakra.png")

    log.info("Rendered all 6 Universe cards to %s", out_dir)

    # 4. AI Caption Generation
    log.info("Invoking Gemini AI (%s) for Daily Cosmic Blueprint copy...", gemini_model)
    copy_data = None
    if gemini_key:
        try:
            from promo_studio.automation.ai_blueprint import get_devotional_fallback_copy
            gemini = GeminiProvider(gemini_key, gemini_model)
            copy_data = generate_cosmic_caption(panchang, gemini, api_key=gemini_key)
        except Exception as e:
            log.warning("Gemini AI failed or not installed: %s. Using rich Vedic fallback copy.", e)
            from promo_studio.automation.ai_blueprint import get_devotional_fallback_copy
            copy_data = get_devotional_fallback_copy(panchang)
    else:
        from promo_studio.automation.ai_blueprint import get_devotional_fallback_copy
        copy_data = get_devotional_fallback_copy(panchang)

    raw_caption = copy_data.get("instagram_caption", "")
    hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in copy_data.get("hashtags", []))
    final_caption = f"{raw_caption}\n\n.\n.\n{hashtags}".strip()

    # Save caption and metadata so they are included in the downloadable zip artifact
    caption_file = out_dir / "caption.txt"
    caption_file.write_text(final_caption, encoding="utf-8")

    import json
    metadata_file = out_dir / "post_metadata.json"
    meta = {
        "date": panchang.date_formatted,
        "date_hi": panchang.date_formatted_hi,
        "tithi": panchang.tithi_name,
        "tithi_hi": panchang.tithi_name_hi,
        "nakshatra": panchang.nakshatra_name,
        "nakshatra_hi": panchang.nakshatra_name_hi,
        "vara": panchang.vara_sa,
        "vara_hi": panchang.vara_hi,
        "deity": panchang.deity,
        "deity_hi": panchang.deity_hi,
        "abhijit_muhurta": panchang.abhijit_muhurta,
        "rahu_kaal": panchang.rahu_kaal,
        "favorable_rashis": panchang.gochar.favorable_rashis if panchang.gochar else [],
        "dasha_spotlight": panchang.gochar.dasha_spotlight_title if panchang.gochar else "",
        "hashtags": copy_data.get("hashtags", []),
    }
    metadata_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved caption.txt and post_metadata.json into %s", out_dir)

    log.info("--- GENERATED CAPTION ---\n%s\n-------------------------", final_caption)

    if dry_run:
        log.info("[DRY RUN] Skipping upload and Instagram publish. Everything executed successfully!")
        return True

    # 5. Image Hosting Upload (ImgBB)
    img_host = ImgBBHost(img_host_key)
    log.info("Uploading cards to temporary image host...")

    if format_mode == "carousel":
        url1 = img_host.upload(str(slide1_path))
        url2 = img_host.upload(str(slide2_path))
        image_urls = [url1, url2]
        log.info("Uploaded Slide 1: %s", url1)
        log.info("Uploaded Slide 2: %s", url2)
    else:
        url_combined = img_host.upload(str(combined_path))
        image_urls = [url_combined]
        log.info("Uploaded Combined Card: %s", url_combined)

    # 6. Instagram Publishing
    log.info("Publishing to Instagram via Graph API...")
    ig_publisher = InstagramCarouselPublisher(ig_user_id, ig_token)

    if format_mode == "carousel":
        res = ig_publisher.publish_carousel(image_urls, final_caption)
    else:
        res = ig_publisher.publish_single(image_urls[0], final_caption)

    if res.ok:
        log.info("SUCCESS! Post live on Instagram: %s (Post ID: %s)", res.url, res.post_id)
        return True
    else:
        log.error("Failed to publish to Instagram: [%s] %s", res.error_code, res.error_message)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Siddhanta Daily Cosmic Blueprint Automated Poster")
    parser.add_argument("--dry-run", action="store_true", help="Generate panchang, cards, and AI caption without posting")
    parser.add_argument("--format", choices=["carousel", "single"], default="carousel", help="Post as 2-slide carousel or single 4:5 portrait card")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (default: today IST)")
    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = dt.date.fromisoformat(args.date)

    run_daily_worker(dry_run=args.dry_run, format_mode=args.format, target_date=target_date)


if __name__ == "__main__":
    main()
