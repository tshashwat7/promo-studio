"""Rule-based Background Template Selector for Siddhanta.

Picks the most appropriate, text-free background template based on:
- Active Festival (Navratri, Diwali, Shivratri, Holi, Saraswati Puja, Generic)
- Solar / Lunar Eclipse (Grahan)
- Planetary Transit / Jyotish Insight
- Daily Panchang / Sunrise Riverside
- Muhurta / Sandstone Pillar with Flowers
"""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image

ASSETS_TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
DOWNLOADS_DIR = Path(r"C:\Users\91962\Downloads")

# Template Registry mapping logical themes/festivals to candidate filenames
TEMPLATE_CANDIDATES = {
    "navratri": [
        "navratri_festival.png",
        "durga_festival.png"
    ],
    "diwali": [
        "Diwali Ghat Glow Template.png",
        "diwali_ghat.png"
    ],
    "shivratri": [
        "Shivratri Festive Diptych.png",
        "shivratri.png"
    ],
    "holi": [
        "Holi Festive Diptych.png",
        "holi.png"
    ],
    "saraswati": [
        "saraswati_festival.png",
        "vasant_panchami.png"
    ],
    "eclipse": [
        "Celestial Eclipse Ghat Mandala.png",
        "eclipse_mandala.png"
    ],
    "generic_festival": [
        "Generic festival.png",
        "Golden Temple Sunrise with Diyas and Lotuses.png"
    ],
    "transit": [
        "Celestial Temple Astrology Poster Template.png",
        "transit_template.png"
    ],
    "panchang": [
        "Panchang Temple Riverside Template.png",
        "panchang_template.png",
        "Golden Temple Sunrise with Diyas and Lotuses.png"
    ],
    "plan_day": [
        "plan_day_template.png",
        "Panchang Temple Riverside Template.png"
    ]
}


def find_template_file(theme_key: str) -> Path | None:
    """Finds existing template file either in project assets or user's Downloads."""
    candidates = TEMPLATE_CANDIDATES.get(theme_key, [])
    for fname in candidates:
        # Check project assets first
        p_asset = ASSETS_TEMPLATES / fname
        if p_asset.exists():
            return p_asset
        # Check Downloads folder
        p_dl = DOWNLOADS_DIR / fname
        if p_dl.exists():
            return p_dl

    # Fallback to general candidates
    for search_dir in (ASSETS_TEMPLATES, DOWNLOADS_DIR):
        for candidate in search_dir.glob("*.png"):
            if theme_key.lower() in candidate.name.lower():
                return candidate

    return None


def select_template_for_content(
    post_type: str,
    festival_name: str = "",
    is_eclipse: bool = False
) -> Path | None:
    """Selects the best template path based on festival name and post type."""
    fn_lower = festival_name.lower()

    if is_eclipse:
        found = find_template_file("eclipse")
        if found:
            return found

    if post_type == "festival" or festival_name:
        if "navratri" in fn_lower or "durga" in fn_lower:
            return find_template_file("navratri")
        elif "diwali" in fn_lower or "deepavali" in fn_lower or "dhanteras" in fn_lower:
            return find_template_file("diwali")
        elif "shivratri" in fn_lower or "shiva" in fn_lower:
            return find_template_file("shivratri")
        elif "holi" in fn_lower:
            return find_template_file("holi")
        elif "saraswati" in fn_lower or "vasant" in fn_lower or "basant" in fn_lower:
            return find_template_file("saraswati")
        else:
            # Other festivals: Jivitputrika, Janmashtami, Gudi Padwa, Chhath, etc.
            return find_template_file("generic_festival")

    if post_type == "transit":
        return find_template_file("transit")

    if post_type == "plan_day":
        return find_template_file("plan_day")

    if post_type == "panchang":
        return find_template_file("panchang")

    return None
