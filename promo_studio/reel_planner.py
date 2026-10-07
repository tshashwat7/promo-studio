"""Planning-only Reel contracts from validated Siddhanta exports; no media is produced."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from .adapter import CHOGHADIYA_QUALITY, adapt_siddhanta
from .models import DataError, end_date
from .selector import _transit

LANGUAGES = ("en", "hi")
KINDS = ("auto", "daily", "festival", "transit", "chakra", "kundli")


def _daily_facts(daily: dict, muhurta: dict) -> dict:
    today = daily["today"]
    en, hi = today["english"], today["hindi"]
    windows = muhurta["muhurtas"]
    for key in ("sunrise", "sunset"):
        if key not in en:
            raise DataError(f"Daily Reel requires today.english.{key}")
    rahu = windows.get("rahu_kaal")
    if rahu is None or rahu.get("is_auspicious") is not False:
        raise DataError("Daily Reel requires validated, inauspicious Rahu Kaal")
    auspicious = windows.get("abhijit_muhurta")
    if auspicious is not None and auspicious.get("is_auspicious") is True:
        good = {"source": "abhijit_muhurta", "name_en": "Abhijit Muhurta",
                "name_hi": "अभिजित मुहूर्त", "start": auspicious["start"],
                "end": auspicious["end"]}
    else:
        # A slot is usable only if the adapter retained the complete validated day cycle.
        slots = muhurta["choghadiya"]["day"]
        candidates = [s for s in slots if s["is_auspicious"] and
                  CHOGHADIYA_QUALITY[s["name_en"]] in ("Best", "Auspicious")
                  ] if len(slots) == 8 else []
        if not candidates:
            raise DataError("Daily Reel requires a validated auspicious window")
        slot = candidates[0]
        good = {"source": "choghadiya", "name_en": slot["name_en"],
                "name_hi": slot["name_hi"], "start": slot["start"], "end": slot["end"]}
    day = date.fromisoformat(today["date"])
    facts = {"tithi_en": f"{en['paksha'].title()} {en['tithi_name']}",
             "tithi_hi": hi["tithi"], "nakshatra_en": en["nakshatra"],
             "nakshatra_hi": hi["nakshatra"], "sunrise": en["sunrise"],
             "sunset": en["sunset"], "auspicious_window": good,
             "rahu_kaal": {"start": rahu["start"], "end": rahu["end"],
                           "is_auspicious": False}}
    for key in ("tithi_end", "nakshatra_end"):
        if key in en:
            facts[key] = en[key]
            facts[f"{key}_date"] = end_date(day, en[key], en["sunrise"]).isoformat()
    return facts


def plan_reels(daily: Mapping[str, Any], muhurta: Mapping[str, Any], *,
               expected_date: date | None = None, language: str = "both",
               kind: str = "auto") -> dict:
    """Return factual planning contracts, never publishable or rendered deliverables.

    An explicit kind refuses absent prerequisites. Auto mode holds optional kinds
    without suppressing the daily deliverable. No script/art is assumed approved.
    """
    if language not in (*LANGUAGES, "both") or kind not in KINDS:
        raise DataError("Choose language en|hi|both and kind auto|daily|festival|transit|chakra|kundli")
    if expected_date is None:
        expected_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    metadata = muhurta.get("metadata") if isinstance(muhurta, Mapping) else None
    other_location = metadata.get("location") if isinstance(metadata, Mapping) else None
    if not isinstance(other_location, Mapping) or other_location.get("timezone") != "Asia/Kolkata":
        raise DataError("Reel planning requires muhurta.metadata.location in Asia/Kolkata")
    data, windows = adapt_siddhanta(daily, muhurta, expected_date)
    today = data["today"]
    location = data["metadata"]["location"]
    languages = LANGUAGES if language == "both" else (language,)
    deliverables: list[dict] = []
    held: list[dict] = []

    def add(reel_kind: str, facts: dict) -> None:
        for lang in languages:
            deliverables.append({"kind": reel_kind, "language": lang, "date": today["date"],
                                 "location": location["name"], "timezone": location["timezone"],
                                 "facts": facts, "review_state": "not_reviewed",
                                 "media_status": "not_rendered"})

    if kind in ("auto", "daily"):
        add("daily", _daily_facts(data, windows))
    if kind in ("auto", "festival"):
        festivals = today["festivals_today"]
        if kind == "festival" and not festivals:
            raise DataError("No explicit today.festivals_today entries for the requested date")
        for festival in festivals:
            add("festival", {"festival_en": festival["name_en"],
                             "festival_hi": festival["name_hi"]})
        if len(festivals) > 1:
            held.append({"kind": "festival", "reason": "Editorial priority among multiple observances requires human review"})
    if kind in ("auto", "transit") and (kind == "transit" or today["day_of_week_en"] == "Friday"):
        chosen = _transit(data)
        if chosen and chosen[1]["ingress"] == today["date"]:
            facts = chosen[1]
            add("transit", {key: facts[key] for key in ("planet", "planet_hi", "rashi",
                                                        "rashi_hi", "ingress", "egress")})
        elif kind == "transit":
            raise DataError("Transit Reel requires a validated major ingress dated today")
        else:
            held.append({"kind": "transit", "reason": "No validated new ingress today; do not re-announce an ongoing transit"})
    for reel_kind, weekday in (("chakra", "Wednesday"), ("kundli", "Saturday")):
        if kind == reel_kind:
            raise DataError(f"{reel_kind.title()} Reel needs a reviewed bilingual script and approved art")
        if kind == "auto" and today["day_of_week_en"] == weekday:
            held.append({"kind": reel_kind, "reason": "Reviewed bilingual script and approved art not yet configured"})
    return {"status": "planning_only", "date": today["date"], "deliverables": deliverables,
            "held": held, "warnings": windows["warnings"]}
