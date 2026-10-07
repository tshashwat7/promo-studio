"""Pure daily selection; an empty explicit festival list never promotes future events."""
from __future__ import annotations

from datetime import date

from .adapter import GRAHAS, ZODIAC, ZODIAC_HI
from .models import DataError, PostSpec, end_date, text

# Source muhurta key -> fact key; each is optional on the card once validated.
MUHURTA_WINDOWS = (("abhijit_muhurta", "abhijit"), ("rahu_kaal", "rahu"),
                   ("yamaghanta", "yamaganda"), ("gulika_kaal", "gulika"))


def muhurta_facts(daily: dict, muhurta: dict) -> dict | None:
    """Validated day Choghadiya plus every window that passed the adapter's cross-checks."""
    en = daily["today"]["english"]
    slots = muhurta["choghadiya"]["day"]
    windows = muhurta["muhurtas"]
    if len(slots) != 8 or "rahu_kaal" not in windows or not {"sunrise", "sunset"} <= en.keys():
        return None
    facts = {"sunrise": en["sunrise"], "sunset": en["sunset"],
             "choghadiya": [{k: s[k] for k in ("name_en", "name_hi", "quality_en", "quality_hi",
                                              "start", "end", "is_auspicious")} for s in slots]}
    for key, name in MUHURTA_WINDOWS:
        if key in windows:
            w = windows[key]
            facts[name] = f"{w['start']} – {w['end']}"
            for field in ("is_auspicious", "name_en", "name_hi"):
                if field in w:
                    facts[f"{name}_{field.replace('is_', '')}"] = w[field]
    return facts


def _transit(daily: dict) -> tuple[str, dict] | None:
    """Most recent ingress among the adapter-validated major transits, plus all nine grahas."""
    transits = daily["transits"]
    major = transits.get("major_transits")
    positions = transits.get("positions")
    if not major or not positions:
        return None
    key = max(major, key=lambda k: (major[k]["ingress_date"], k))
    featured, position = major[key], positions[key]
    rows = [{"key": k, "degree_in_rashi": round(positions[k]["degree_in_rashi"], 2),
             **{f: positions[k][f] for f in ("name_en", "name_hi", "rashi_en", "rashi_hi",
                                             "motion_en", "motion_hi", "is_retrograde")}}
            for k in GRAHAS]
    facts = {"featured": key, "planet": text(position["name_en"], "transit planet"),
             "planet_hi": position["name_hi"], "rashi": position["rashi_en"],
             "rashi_hi": position["rashi_hi"], "motion": position["motion_en"],
             "degree_in_rashi": round(position["degree_in_rashi"], 2),
             "ingress": featured["ingress_date"], "egress": featured["egress_date"],
             "moon_rashi": positions["moon"]["rashi_en"],
             "nakshatra_hi": daily["today"]["hindi"]["nakshatra"], "positions": rows}
    # Present only when the adapter found the lists consistent with the Moon-sign rules.
    if "benefited_rashis_en" in featured:
        good = set(featured["benefited_rashis_en"])
        facts["rashis"] = [{"en": z, "hi": ZODIAC_HI[i], "favourable": z in good}
                           for i, z in enumerate(ZODIAC)]
    return key, facts


def select(daily: dict, muhurta: dict, card: str | None = None) -> PostSpec:
    """Weekday rotation by default; `card` (panchang, muhurta or transit) overrides it."""
    if card not in (None, "panchang", "muhurta", "transit"):
        raise DataError(f"Unknown card {card!r}; choose panchang, muhurta or transit")
    today, en = daily["today"], daily["today"]["english"]
    when = today["date"]
    location = daily["metadata"]["location"]["name"]
    base = {"date": when, "location": location,
            "tithi": f"{en['paksha'].title()} {en['tithi_name']}", "nakshatra": en["nakshatra"]}
    festivals = today["festivals_today"]
    if card is None and festivals:
        hindi = today["hindi"]
        return PostSpec("festival", when, {
            **base, "festival": festivals[0]["name_en"], "festival_hi": festivals[0]["name_hi"],
            "tithi_hi": f"{hindi['paksha']} {hindi['tithi_name']}",
            "nakshatra_hi": hindi["nakshatra"]})
    weekday = today["day_of_week_en"]
    if card is None and weekday in ("Saturday", "Wednesday"):
        return PostSpec("kundli" if weekday == "Saturday" else "chakra", when, {}, True)
    windows = muhurta["muhurtas"]
    if card == "muhurta" or (card is None and weekday in ("Tuesday", "Thursday")):
        facts = muhurta_facts(daily, muhurta)
        if facts is not None:
            return PostSpec("muhurta", when, {**base, **facts})
        if card == "muhurta":
            raise DataError("The Muhurta card needs the validated day Choghadiya and Rahu Kaal")
    if card == "transit" or (card is None and weekday == "Friday"):
        chosen = _transit(daily)
        if chosen:
            _, detail = chosen
            return PostSpec("transit", when, {**base, **detail})
        if card == "transit":
            raise DataError("The transit card needs validated planet positions and transits")
    for required in ("sunrise", "sunset", "tithi_end", "nakshatra_end", "moonrise"):
        if required not in en:
            raise DataError(f"today.english.{required} is needed by the Panchang renderer")
    if "chandra_rashi" not in today["hindi"]:
        raise DataError("today.hindi.chandra_rashi is needed by the Panchang renderer")
    facts = {**base, **{k: en[k] for k in ("yoga", "karana", "sunrise", "sunset", "masa",
                                           "tithi_end", "nakshatra_end", "moonrise")},
             "tithi_hi": today["hindi"]["tithi"], "nakshatra_hi": today["hindi"]["nakshatra"],
             "tithi_name_hi": today["hindi"]["tithi_name"], "paksha_hi": today["hindi"]["paksha"],
             "masa_hi": today["hindi"]["masa"],
             "yoga_hi": today["hindi"]["yoga"], "karana_hi": today["hindi"]["karana"],
             "moon_rashi_hi": today["hindi"]["chandra_rashi"]}
    for key in ("tithi_end", "nakshatra_end"):
        facts[f"{key}_date"] = end_date(date.fromisoformat(when), en[key],
                                        en["sunrise"]).isoformat()
    for key, name in (("abhijit_muhurta", "abhijit"), ("rahu_kaal", "rahu")):
        if key in windows:
            w = windows[key]
            facts[name] = f"{w['start']} – {w['end']}"
            if "is_auspicious" in w:
                facts[f"{name}_auspicious"] = w["is_auspicious"]
    return PostSpec("panchang", when, facts)
