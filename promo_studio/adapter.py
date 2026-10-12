"""Bind real Siddhanta JSON to the values the current card renderer actually uses."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import radians, sin
from typing import Any, Mapping

from .models import DataError, minutes, text, time, window

# Rahu Kaal, Yamaganda and Gulika are these eighths of daylight (1 = first) per weekday.
RAHU_OCTANT = {"Monday": 2, "Tuesday": 7, "Wednesday": 5, "Thursday": 6,
               "Friday": 4, "Saturday": 3, "Sunday": 8}
YAMAGANDA_OCTANT = {"Monday": 4, "Tuesday": 3, "Wednesday": 2, "Thursday": 1,
                    "Friday": 7, "Saturday": 6, "Sunday": 5}
GULIKA_OCTANT = {"Monday": 6, "Tuesday": 5, "Wednesday": 4, "Thursday": 3,
                 "Friday": 2, "Saturday": 1, "Sunday": 7}
OCTANT_WINDOWS = {"rahu_kaal": RAHU_OCTANT, "yamaghanta": YAMAGANDA_OCTANT,
                  "gulika_kaal": GULIKA_OCTANT}
# Choghadiya follow fixed cycles; each weekday's day and night start at a fixed slot.
DAY_CYCLE = ("Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog")
DAY_START = {"Sunday": "Udveg", "Monday": "Amrit", "Tuesday": "Rog", "Wednesday": "Labh",
             "Thursday": "Shubh", "Friday": "Chal", "Saturday": "Kaal"}
NIGHT_CYCLE = ("Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg")
NIGHT_START = {"Sunday": "Shubh", "Monday": "Chal", "Tuesday": "Kaal", "Wednesday": "Udveg",
               "Thursday": "Amrit", "Friday": "Rog", "Saturday": "Labh"}
CHOGHADIYA_QUALITY = {"Amrit": "Best", "Shubh": "Auspicious", "Labh": "Auspicious",
                      "Chal": "Neutral", "Udveg": "Inauspicious", "Kaal": "Inauspicious",
                      "Rog": "Inauspicious"}
ABHIJIT_TOLERANCE, RAHU_TOLERANCE = 5, 2  # minutes
GRAHAS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")
ZODIAC = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces")
ZODIAC_HI = ("मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर",
             "कुंभ", "मीन")
MAX_ELONGATION = {"mercury": 28.5, "venus": 47.5}  # Greatest angular distance from the Sun.
# Houses counted from the Moon sign where each graha's transit is favourable (classical Gochara).
GOCHAR_GOOD = {"sun": (3, 6, 10, 11), "moon": (1, 3, 6, 7, 10, 11), "mars": (3, 6, 11),
               "mercury": (2, 4, 6, 8, 10, 11), "jupiter": (2, 5, 7, 9, 11),
               "venus": (1, 2, 3, 4, 5, 8, 9, 11, 12), "saturn": (3, 6, 11),
               "rahu": (3, 6, 10, 11), "ketu": (3, 6, 10, 11)}
RASHI_LISTS = ("benefited_rashis_en", "benefited_rashis_hi",
               "challenged_rashis_en", "challenged_rashis_hi")
# Tropical minus sidereal Sun: Lahiri-family ayanamsa (~24.2° in 2026) ± one day of solar motion.
AYANAMSA_RANGE = (23.0, 25.5)


def _tropical_sun(day: date) -> float:
    """Low-precision (~0.01°) apparent solar longitude at 12:00 IST."""
    n = (day - date(2000, 1, 1)).days - 0.5 + 6.5 / 24
    g = radians((357.528 + 0.9856003 * n) % 360)
    return (280.460 + 0.9856474 * n + 1.915 * sin(g) + 0.020 * sin(2 * g)) % 360


def _separation(a: float, b: float) -> float:
    gap = abs(a - b) % 360
    return min(gap, 360 - gap)


def _position_problem(positions: Any, en: Mapping, day: date) -> str | None:
    """First reason the nine positions cannot be published, or None."""
    if not isinstance(positions, Mapping):
        return "are missing"
    for key in GRAHAS:
        p = positions.get(key)
        if not isinstance(p, Mapping):
            return f"lack {key}"
        index, degree, total = p.get("rashi_index"), p.get("degree_in_rashi"), p.get("longitude_total")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 12:
            return f"give {key} an invalid rashi_index"
        if (p.get("rashi_en"), p.get("rashi_hi")) != (ZODIAC[index], ZODIAC_HI[index]):
            return f"name {key}'s rashi inconsistently with rashi_index {index}"
        if (isinstance(degree, bool) or not isinstance(degree, (int, float))
            or isinstance(total, bool) or not isinstance(total, (int, float))):
            return f"give {key} a degree that disagrees with its longitude"
        degree_value, total_value = float(degree), float(total)
        if not 0 <= degree_value < 30 or \
            _separation(index * 30 + degree_value, total_value) > 0.02:
            return f"give {key} a degree that disagrees with its longitude"
        if not isinstance(p.get("is_retrograde"), bool) or p.get("motion_en") != (
                "Retrograde" if p["is_retrograde"] else "Direct"):
            return f"give {key} contradictory motion"
        if not all(isinstance(p.get(f), str) and p[f].strip() for f in ("name_en", "name_hi",
                                                                         "motion_hi")):
            return f"lack {key}'s names"
    if positions["sun"]["is_retrograde"] or positions["moon"]["is_retrograde"]:
        return "make the Sun or Moon retrograde"
    sun = positions["sun"]["longitude_total"]
    if abs(_separation(positions["rahu"]["longitude_total"],
                       positions["ketu"]["longitude_total"]) - 180) > 0.1:
        return "do not place Ketu opposite Rahu"
    for key, limit in MAX_ELONGATION.items():
        if _separation(positions[key]["longitude_total"], sun) > limit:
            return f"place {key} farther than {limit}° from the Sun"
    for key, field in (("sun", "sun_rashi"), ("moon", "moon_rashi")):
        if en.get(field) is not None and en[field] != positions[key]["rashi_en"]:
            return f"put the {key} in {positions[key]['rashi_en']} but today.english.{field} " \
                   f"is {en[field]}"
    ayanamsa = (_tropical_sun(day) - sun) % 360
    if not AYANAMSA_RANGE[0] <= ayanamsa <= AYANAMSA_RANGE[1]:
        return f"put the Sun {ayanamsa:.1f}° from its sidereal place for {day.isoformat()}"
    return None


def _rashi_problem(key: str, item: Mapping) -> str | None:
    """Why a transit's favourable/challenging Moon-sign lists cannot be shown, or None."""
    if key not in GOCHAR_GOOD:
        return "are missing"
    good_en = item.get("benefited_rashis_en")
    good_hi = item.get("benefited_rashis_hi")
    hard_en = item.get("challenged_rashis_en")
    hard_hi = item.get("challenged_rashis_hi")
    if (not isinstance(good_en, list) or not isinstance(good_hi, list)
            or not isinstance(hard_en, list) or not isinstance(hard_hi, list)):
        return "are missing"
    at = ZODIAC.index(item["current_rashi_en"])
    expected = {z for i, z in enumerate(ZODIAC) if (at - i) % 12 + 1 in GOCHAR_GOOD[key]}
    if set(good_en) != expected or sorted(good_en + hard_en) != sorted(ZODIAC):
        return "disagree with the Moon-sign rules"
    for english, hindi in ((good_en, good_hi), (hard_en, hard_hi)):
        if [ZODIAC_HI[ZODIAC.index(z)] for z in english] != hindi:
            return "have Hindi names that do not match the English"
    return None


def _transit_warnings(transits: dict, en: Mapping, day: date) -> list[str]:
    """Empty positions that fail physical checks; drop major transits that disagree with them."""
    problem = _position_problem(transits.get("positions"), en, day)
    if problem:
        transits["positions"], transits["major_transits"] = {}, {}
        return [f"Planet positions {problem}; the transit card is not used."]
    major = transits.get("major_transits")
    if not isinstance(major, dict):
        transits["major_transits"] = {}
        return []
    warnings = []
    for key in list(major):
        item, position = major[key], transits["positions"].get(key)
        try:
            current = date.fromisoformat(str(item["ingress_date"])) <= day \
                <= date.fromisoformat(str(item["egress_date"]))
        except (KeyError, TypeError, ValueError):
            current = False
        if not current or not isinstance(position, Mapping) or \
                item.get("current_rashi_en") != position["rashi_en"] or \
                item.get("is_retrograde") != position["is_retrograde"]:
            del major[key]
            warnings.append(f"Major transit {key} disagrees with today's position or dates; "
                            "omitted.")
            continue
        problem = _rashi_problem(key, item)
        if problem:
            for field in RASHI_LISTS:
                item.pop(field, None)
            warnings.append(f"Major transit {key} favourable/challenging rashis {problem}; "
                            "lists omitted.")
    return warnings


def choghadiya_order(cycle: tuple[str, ...], start: str) -> list[str]:
    first = cycle.index(start)
    return [cycle[(first + i) % len(cycle)] for i in range(8)]


def _choghadiya_warnings(slots: list[dict], night: list, sunrise: str, sunset: str,
                         weekday: str) -> list[str]:
    """Empty the day list if it contradicts the weekday cycle or the file's own daylight."""
    rise, sset = minutes(sunrise), minutes(sunset)
    eighth = (sset - rise) / 8
    expected = choghadiya_order(DAY_CYCLE, DAY_START[weekday])
    problem = None
    if [s["name_en"] for s in slots] != expected:
        problem = f"order is not the {weekday} sequence ({', '.join(expected)})"
    elif any(s["quality_en"] != CHOGHADIYA_QUALITY[s["name_en"]] for s in slots):
        problem = "quality labels do not match the slot names"
    elif any(abs(minutes(s["start"]) - (rise + i * eighth)) > RAHU_TOLERANCE
             or abs(minutes(s["end"]) - (rise + (i + 1) * eighth)) > RAHU_TOLERANCE
             for i, s in enumerate(slots)):
        problem = f"slots do not divide sunrise {sunrise} to sunset {sunset} into eighths"
    warnings = []
    if problem:
        slots.clear()
        warnings.append(f"Day Choghadiya {problem}; omitted.")
    names = [s.get("name_en") for s in night if isinstance(s, Mapping)]
    if names and names != choghadiya_order(NIGHT_CYCLE, NIGHT_START[weekday]):
        warnings.append("Night Choghadiya order is not the "
                        f"{weekday} night sequence; it is not used on any card.")
    return warnings


def _window_warnings(windows: dict, sunrise: str, sunset: str, weekday: str) -> list[str]:
    """Drop windows that contradict the same file's sunrise/sunset instead of publishing them."""
    rise, sset = minutes(sunrise), minutes(sunset)
    warnings = []
    abhijit = windows.get("abhijit_muhurta")
    if abhijit:
        centre = (minutes(abhijit["start"]) + minutes(abhijit["end"])) / 2
        noon = (rise + sset) / 2
        if abs(centre - noon) > ABHIJIT_TOLERANCE:
            del windows["abhijit_muhurta"]
            warnings.append(f"Abhijit Muhurta {abhijit['start']} – {abhijit['end']} is centred "
                            f"{centre - noon:+.0f} min from solar noon implied by sunrise "
                            f"{sunrise} and sunset {sunset}; omitted.")
    eighth = (sset - rise) / 8
    for key, octants in OCTANT_WINDOWS.items():
        found = windows.get(key)
        if not found:
            continue
        start = rise + (octants[weekday] - 1) * eighth
        if (abs(minutes(found["start"]) - start) > RAHU_TOLERANCE
                or abs(minutes(found["end"]) - (start + eighth)) > RAHU_TOLERANCE):
            del windows[key]
            name = found.get("name_en", key)
            warnings.append(f"{name} {found['start']} – {found['end']} does not match the "
                            f"{weekday} daylight segment; omitted.")
    return warnings


def adapt_siddhanta(daily: Mapping[str, Any], muhurta: Mapping[str, Any],
                    expected_date: date) -> tuple[dict, dict]:
    if not isinstance(daily, Mapping) or not isinstance(muhurta, Mapping):
        raise DataError("daily and muhurta inputs must be JSON objects")
    today = daily.get("today")
    meta = daily.get("metadata")
    if not isinstance(today, Mapping) or not isinstance(meta, Mapping):
        raise DataError("Siddhanta today and metadata objects are required")
    en, hi = today.get("english"), today.get("hindi")
    location = meta.get("location")
    if not isinstance(en, Mapping) or not isinstance(hi, Mapping) \
            or not isinstance(location, Mapping):
        raise DataError("Siddhanta today.english, today.hindi and metadata.location are required")
    try:
        actual = date.fromisoformat(text(today.get("date"), "today.date"))
    except ValueError as exc:
        raise DataError("today.date must be YYYY-MM-DD") from exc
    if actual != expected_date or muhurta.get("date") != actual.isoformat():
        raise DataError(f"Input dates must both match requested date {expected_date.isoformat()}")
    if today.get("day_of_week_en") != actual.strftime("%A"):
        raise DataError("today.day_of_week_en contradicts today.date")
    location_name = text(location.get("name"), "metadata.location.name")
    if location.get("timezone") != "Asia/Kolkata":
        raise DataError("This renderer supports only Asia/Kolkata source times")
    muhurta_meta = muhurta.get("metadata")
    other = muhurta_meta.get("location") if isinstance(muhurta_meta, Mapping) else None
    if isinstance(other, Mapping):
        for axis in ("latitude", "longitude"):
            a, b = location.get(axis), other.get(axis)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) \
                    or abs(a - b) > 0.001:
                raise DataError(f"data.json and muhu.json {axis} differ; times would not match")
    en_clean = {k: text(en.get(k), f"today.english.{k}") for k in
                ("tithi_name", "nakshatra", "yoga", "karana", "paksha", "masa")}
    if en_clean["paksha"].lower() not in ("shukla", "krishna"):
        raise DataError("today.english.paksha must be shukla or krishna")
    for k in ("sunrise", "sunset", "tithi_end", "nakshatra_end", "moonrise"):
        if en.get(k) is not None:
            en_clean[k] = time(en[k], f"today.english.{k}")
    hi_clean = {k: text(hi.get(k), f"today.hindi.{k}") for k in
                ("tithi_name", "nakshatra", "tithi", "yoga", "karana", "paksha", "masa")}
    chandra = hi.get("chandra_rashi")
    if chandra is not None:
        hi_clean["chandra_rashi"] = text(chandra, "today.hindi.chandra_rashi")
    windows = muhurta.get("muhurtas")
    if not isinstance(windows, Mapping):
        raise DataError("muhurta.muhurtas is required")
    clean_windows: dict[str, dict[str, Any]] = {
        k: window(v, f"muhurtas.{k}") for k, v in windows.items()
        if k in ("abhijit_muhurta", "rahu_kaal", "yamaghanta", "gulika_kaal")
        and v is not None}
    for key, clean in clean_windows.items():
        source_window = windows.get(key)
        if not isinstance(source_window, Mapping):
            continue
        flag = source_window.get("is_auspicious")
        if flag is not None:
            if not isinstance(flag, bool):
                raise DataError(f"muhurtas.{key}.is_auspicious must be true or false")
            clean["is_auspicious"] = flag
        for lang in ("en", "hi"):
            if source_window.get(f"name_{lang}") is not None:
                clean[f"name_{lang}"] = text(source_window[f"name_{lang}"],
                                             f"muhurtas.{key}.name_{lang}")
    warnings = []
    if "sunrise" in en_clean and "sunset" in en_clean:
        warnings = _window_warnings(clean_windows, en_clean["sunrise"], en_clean["sunset"],
                                    actual.strftime("%A"))
    chog = muhurta.get("choghadiya")
    if not isinstance(chog, Mapping) or not isinstance(chog.get("day"), list):
        raise DataError("muhurta.choghadiya.day must be a list")
    slots = []
    for i, slot in enumerate(chog["day"]):
        if not isinstance(slot, Mapping):
            raise DataError(f"choghadiya.day[{i}] must be an object")
        slots.append({"name_en": text(slot.get("name_en"), f"choghadiya.day[{i}].name_en"),
                      "name_hi": text(slot.get("name_hi"), f"choghadiya.day[{i}].name_hi"),
                      "quality_en": text(slot.get("quality_en"), f"choghadiya.day[{i}].quality_en"),
                      "quality_hi": text(slot.get("quality_hi"), f"choghadiya.day[{i}].quality_hi"),
                      **window(slot, f"choghadiya.day[{i}]"),
                      "is_auspicious": slot.get("is_auspicious") is True})
    if "sunrise" in en_clean and "sunset" in en_clean:
        warnings += _choghadiya_warnings(slots, chog.get("night") or [], en_clean["sunrise"],
                                         en_clean["sunset"], actual.strftime("%A"))
    festivals = today.get("festivals_today")
    if not isinstance(festivals, list):
        raise DataError("today.festivals_today must be an explicit list (empty is authoritative)")
    festival_names = [text(f.get("name_en") if isinstance(f, Mapping) else None,
                           "festivals_today.name_en") for f in festivals]
    festival_titles = []
    for festival, name in zip(festivals, festival_names):
        festival_record = festival if isinstance(festival, Mapping) else {}
        raw_id = festival_record.get("id")
        event_id = raw_id.strip() if isinstance(raw_id, str) and raw_id.strip() else None
        raw_hindi_name = festival_record.get("name_hi")
        name_hi = text(raw_hindi_name, "festivals_today.name_hi") \
            if raw_hindi_name else name
        festival_titles.append({"id": event_id, "name_en": name, "name_hi": name_hi,
                                "image": festival_record.get("image")})
    transits = deepcopy(daily.get("transits") or {})
    if not isinstance(transits, dict):
        raise DataError("transits must be an object")
    for section in ("positions", "major_transits"):
        group = transits.get(section)
        if isinstance(group, dict):
            for node in ("rahu", "ketu"):
                if isinstance(group.get(node), dict):
                    group[node].update(is_retrograde=True, motion_en="Retrograde", motion_hi="वक्री")
    warnings += _transit_warnings(transits, en, actual)
    clean_daily = {"metadata": {"location": {"name": location_name, "timezone": "Asia/Kolkata"}},
                   "today": {"date": actual.isoformat(), "day_of_week_en": actual.strftime("%A"),
                             "english": en_clean, "hindi": hi_clean,
                             "festivals_today": festival_titles},
                   "transits": transits, "upcoming_festivals": []}
    clean_muhurta = {"date": actual.isoformat(), "muhurtas": clean_windows,
                     "choghadiya": {"day": slots}, "warnings": warnings}
    return clean_daily, clean_muhurta
