"""Siddhanta App Festival Resolver.

Decoupled festival engine that queries the authentic Siddhanta app rules
from 'panchang_master_app/assets/rules/' to ensure 100% data authority and
agreement between the app and social automation.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("festival_resolver")

APP_RULES_DIR = Path(r"D:\AI My Projects\Production\panchang_master_app\assets\rules")
LOCAL_RULES_DIR = Path(__file__).resolve().parent.parent / "assets" / "rules"

_CACHED_FESTIVALS: list[dict] | None = None


def load_siddhanta_festival_rules() -> list[dict]:
    """Loads festival rules from the Siddhanta app codebase or local fallback."""
    global _CACHED_FESTIVALS
    if _CACHED_FESTIVALS is not None:
        return _CACHED_FESTIVALS

    rules: list[dict] = []
    sources = [
        APP_RULES_DIR / "festivals_smartha.json",
        APP_RULES_DIR / "festivals_solar.json",
        LOCAL_RULES_DIR / "festivals_smartha.json",
    ]

    for p in sources:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                f_list = data.get("festivals", [])
                rules.extend(f_list)
                log.info("Loaded %d festival rules from %s", len(f_list), p)
                break
            except Exception as e:
                log.warning("Could not parse festival rules from %s: %s", p, e)

    _CACHED_FESTIVALS = rules
    return rules


def resolve_festival(
    masa_name: str,
    paksha: str,
    tithi_index: int,
    tithi_name: str = ""
) -> tuple[bool, str, str, str]:
    """Resolves today's festival against Siddhanta app rules.
    
    Returns:
        (is_festival, festival_name_en, festival_name_hi, festival_observance_note)
    """
    rules = load_siddhanta_festival_rules()

    # Tithi in paksha (1..15, with 30 being Amavasya and 15 being Purnima)
    t_in_paksha = (tithi_index % 15) + 1
    if tithi_index == 29:
        t_in_paksha = 30
    elif tithi_index == 14:
        t_in_paksha = 15

    m_lower = masa_name.lower()
    p_lower = paksha.lower()

    for r in rules:
        r_masa = str(r.get("masa", "")).lower()
        r_masa_amanta = str(r.get("masa_amanta", "")).lower()
        r_paksha = str(r.get("paksha", "")).lower()
        r_tithi = r.get("tithi")

        # Match Masa (both Purnimanta and Amanta conventions)
        masa_matches = (r_masa == m_lower) or (r_masa_amanta == m_lower) or (not r_masa)
        paksha_matches = (r_paksha == p_lower) or (not r_paksha)
        tithi_matches = (r_tithi == t_in_paksha) or (r_tithi == (tithi_index + 1))

        if masa_matches and paksha_matches and tithi_matches:
            name_obj = r.get("name", {})
            name_en = name_obj.get("en", r.get("id", "Festival"))
            name_hi = name_obj.get("hi", name_en)

            # Guidelines / observance summary from rule
            notes = []
            for g in r.get("guidelines", []):
                notes.append(f"{g.get('label')}: {g.get('value')}")
            note_str = " • ".join(notes) if notes else "Auspicious Vedic observance."

            return True, name_en, name_hi, note_str

    # Built-in Shastric core festivals if external JSON rules did not match
    known_shastric = {
        # Jivitputrika (Ashwin/Bhadrapada Krishna Ashtami/Navami)
        ("bhadrapada", "krishna", 8): ("Jivitputrika Vrat (Jitiya)", "जीवित्पुत्रिका व्रत", "Nirjala Mahavrat for children's long life & protection"),
        ("bhadrapada", "krishna", 9): ("Jivitputrika Vrat (Parana)", "जितिया पारण", "Breaking of the sacred fast after sunrise puja"),
        ("ashwina", "krishna", 8): ("Jivitputrika Vrat (Jitiya)", "जीवित्पुत्रिका व्रत", "Nirjala Mahavrat for children's long life & protection"),
        ("ashwina", "krishna", 9): ("Jivitputrika Vrat (Parana)", "जितिया पारण", "Breaking of the sacred fast after sunrise puja"),
        # Navratri Day 1
        ("ashwina", "shukla", 1): ("Sharad Navratri Begins (Day 1)", "शारदीय नवरात्रि प्रतिपदा", "Ghatasthapana & worship of Maa Shailputri"),
        # Dussehra
        ("ashwina", "shukla", 10): ("Vijayadashami (Dussehra)", "विजयादशमी", "Triumph of Dharma over Adharma • Shami Puja"),
        # Diwali
        ("kartika", "krishna", 30): ("Diwali (Deepavali)", "दीपावली", "Maha Lakshmi Puja & festival of lights"),
        ("kartik", "krishna", 30): ("Diwali (Deepavali)", "दीपावली", "Maha Lakshmi Puja & festival of lights"),
    }

    key = (m_lower, p_lower, t_in_paksha)
    if key in known_shastric:
        en, hi, desc = known_shastric[key]
        return True, en, hi, desc

    return False, "", "", ""
