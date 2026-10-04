"""Adapter from the real Siddhanta workflow schema to Promo Studio's internal schema.

Only this module knows the external Siddhanta JSON layout. Renderers and selectors
consume the validated internal model and never inspect the upstream JSON directly.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Optional
from .models import DataError


def adapt_siddhanta(daily_panchang: Mapping[str, Any], muhurta_data: Optional[Mapping[str, Any]] = None) -> dict:
    if not isinstance(daily_panchang, Mapping):
        raise TypeError("daily_panchang must be an object")
    today = daily_panchang.get("today")
    if not isinstance(today, Mapping):
        raise ValueError("daily_panchang.today is required")

    en = today.get("english")
    if not isinstance(en, Mapping):
        raise DataError("not a Siddhanta payload: today.english is required")

    # The English block is the canonical Promo Studio language binding.
    metadata = daily_panchang.get("metadata")
    if not isinstance(metadata, Mapping):
        raise DataError("not a Siddhanta payload: metadata is required")
    location = metadata.get("location")
    if not isinstance(location, Mapping) or not isinstance(location.get("name"), str) or not location.get("name").strip():
        raise DataError("Siddhanta metadata.location.name is required")

    binding_warnings: list[str] = []
    normalised_nodes: set[str] = set()
    out_today = {
        "date": today.get("date"),
        "day_of_week": today.get("day_of_week_en"),
        "location": location.get("name").strip(),
        "location_display": (location.get("display_name") or location.get("name").strip().split(",", 1)[0].split(" (", 1)[0]).strip(),
        "tithi": en.get("tithi_name"),
        "paksha": en.get("paksha"),
        "nakshatra": en.get("nakshatra"),
        "yoga": en.get("yoga"),
        "karana": en.get("karana"),
        "masa_purnimanta": en.get("masa"),
        "sunrise": en.get("sunrise"),
        "sunset": en.get("sunset"),
        # Explicitly authoritative: [] means no festival today.
        "festivals_today": deepcopy(today.get("festivals_today", [])),
        # Kept for the upcoming-festival adapter/tests, never used as today's festival
        # when festivals_today is explicitly present.
        "upcoming_festivals": deepcopy(daily_panchang.get("upcoming_festivals", [])),
    }

    # Prefer the dedicated muhurta file. Its structure is authoritative for windows.
    if isinstance(muhurta_data, Mapping):
        mu_date = muhurta_data.get("date")
        day_date = today.get("date")
        if mu_date != day_date:
            raise DataError(f"muhurta_data.date {mu_date!r} does not match today.date {day_date!r}")
        mh = muhurta_data.get("muhurtas", {})
        ch = muhurta_data.get("choghadiya", {})
    else:
        # Backward-compatible fallback to the duplicated values inside daily_panchang.
        hi = today.get("hindi", {}) if isinstance(today.get("hindi"), Mapping) else {}
        sh = hi.get("shubh_muhurta", {}) if isinstance(hi.get("shubh_muhurta"), Mapping) else {}
        ah = hi.get("ashubh_muhurta", {}) if isinstance(hi.get("ashubh_muhurta"), Mapping) else {}
        mh = {
            "abhijit_muhurta": _window_from_string(sh.get("abhijit")),
            "brahma_muhurta": _window_from_string(sh.get("brahma_muhurta")),
            "godhuli_muhurta": _window_from_string(sh.get("godhuli_muhurta")),
            "rahu_kaal": _window_from_string(ah.get("rahu_kaal")),
            "gulika_kaal": _window_from_string(ah.get("gulika_kaal")),
            "yamaghanta": _window_from_string(ah.get("yamaghanta")),
        }
        ch = today.get("choghadiya", {})

    for source_key, target_key in (
        ("abhijit_muhurta", "abhijit_muhurta"),
        ("brahma_muhurta", "brahma_muhurta"),
        ("godhuli_muhurta", "godhuli_muhurta"),
        ("rahu_kaal", "rahu_kaal"),
        ("gulika_kaal", "gulika_kaal"),
        ("yamaghanta", "yamaghanta"),
    ):
        if isinstance(mh, Mapping) and mh.get(source_key) is not None:
            out_today[target_key] = _normalise_window(mh[source_key])

    if isinstance(ch, Mapping):
        out_today["choghadiya"] = deepcopy(ch)

    # Transits live at the top level in the real workflow. Normalize node motion
    # here so no renderer/caption can accidentally publish the upstream Direct flag.
    transits = deepcopy(daily_panchang.get("transits", {}))
    if isinstance(transits, Mapping):
        for section in ("positions", "major_transits"):
            group = transits.get(section)
            if isinstance(group, Mapping):
                for node in ("rahu", "ketu"):
                    item = group.get(node)
                    if isinstance(item, Mapping):
                        item["is_retrograde"] = True
                        item["motion_en"] = "Retrograde"
                        item["motion_hi"] = "वक्री"
                        normalised_nodes.add(node)
    binding_warnings.extend(f"{node} motion normalised to Retrograde" for node in sorted(normalised_nodes))
    out_today["warnings"] = binding_warnings
    return {"today": out_today, "transits": transits}


def _window_from_string(value: Any):
    if not isinstance(value, str) or "–" not in value:
        return None
    start, end = [x.strip() for x in value.split("–", 1)]
    return {"start": start, "end": end}


def _normalise_window(value: Any):
    if isinstance(value, Mapping):
        return {"start": value.get("start"), "end": value.get("end")}
    return _window_from_string(value)
