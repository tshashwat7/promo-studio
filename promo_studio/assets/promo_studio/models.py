"""Strict, validated view of the upstream Siddhanta JSON.

Rules enforced here (never in the renderer):
  * required facts missing/invalid  -> DataError (no post is produced)
  * optional facts missing/invalid  -> dropped + recorded in Day.warnings
  * nothing is ever computed or guessed; values are only checked and normalised
"""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass, field
from datetime import date as _date, datetime
from typing import Any, Mapping, Optional, Tuple


class DataError(ValueError):
    """Upstream payload is unusable or self-contradictory. Do not post."""


@dataclass(frozen=True)
class Window:
    start: str
    end: str


@dataclass(frozen=True)
class Festival:
    name_en: str
    date: _date


@dataclass(frozen=True)
class Day:
    date: _date
    weekday: str
    location: Optional[str]
    location_display: Optional[str]
    tithi: str
    paksha: str
    nakshatra: str
    yoga: Optional[str] = None
    karana: Optional[str] = None
    masa: Optional[str] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    rahu_kaal: Optional[Window] = None
    gulika_kaal: Optional[Window] = None
    yamaghanta: Optional[Window] = None
    abhijit: Optional[Window] = None
    brahma_muhurta: Optional[Window] = None
    godhuli_muhurta: Optional[Window] = None
    choghadiya: Optional[Mapping[str, Any]] = None
    festivals_today: Tuple[Festival, ...] = ()
    raw_transit: Optional[Mapping[str, Any]] = None  # opaque; only a transit post may read it
    warnings: Tuple[str, ...] = field(default=())


_CTRL = re.compile(r"[\x00-\x1f\x7f]")
_TIME = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$")
MAX_NAME = 80


def _text(v: Any, maxlen: int = 60) -> Optional[str]:
    if not isinstance(v, str):
        return None
    s = unicodedata.normalize("NFC", _CTRL.sub(" ", v)).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:maxlen] if s else None


def _time(v: Any) -> Optional[str]:
    if not isinstance(v, str):
        return None
    m = _TIME.match(v)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if not (1 <= h <= 12 and 0 <= mi <= 59):
        return None
    return f"{h}:{mi:02d} {m.group(3).upper()}"


def _parse_date(v: Any, what: str) -> _date:
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").date()
    except ValueError:
        raise DataError(f"{what}: expected YYYY-MM-DD, got {v!r}") from None


def parse_day(payload: Mapping[str, Any]) -> Day:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("today"), Mapping):
        raise DataError("payload must be an object with a 'today' object")
    raw = payload["today"]
    warnings: list[str] = list(raw.get("warnings") or []) if isinstance(raw.get("warnings"), list) else []

    d = _parse_date(raw.get("date"), "today.date")
    weekday = d.strftime("%A")
    claimed = _text(raw.get("day_of_week"))
    if claimed and claimed.lower() != weekday.lower():
        raise DataError(f"day_of_week {claimed!r} contradicts date {d} ({weekday})")

    location = _text(raw.get("location"), MAX_NAME)
    location_display = _text(raw.get("location_display"), MAX_NAME)
    tithi, nak = _text(raw.get("tithi")), _text(raw.get("nakshatra"))
    paksha = (_text(raw.get("paksha")) or "").lower()
    if not tithi:
        raise DataError("today.tithi missing")
    if not nak:
        raise DataError("today.nakshatra missing")
    if paksha not in ("shukla", "krishna"):
        raise DataError(f"today.paksha must be shukla|krishna, got {raw.get('paksha')!r}")

    def opt_text(key):
        v = _text(raw.get(key))
        if raw.get(key) is not None and v is None:
            warnings.append(f"{key}: ignored invalid value")
        return v

    def opt_time(key):
        if raw.get(key) is None:
            return None
        t = _time(raw.get(key))
        if t is None:
            warnings.append(f"{key}: ignored invalid time {raw.get(key)!r}")
        return t

    def opt_window(key):
        w = raw.get(key)
        if w is None:
            return None
        if not isinstance(w, Mapping):
            warnings.append(f"{key}: ignored (not an object)")
            return None
        s, e = _time(w.get("start")), _time(w.get("end"))
        if s is None or e is None:
            warnings.append(f"{key}: ignored invalid window {dict(w)!r}")
            return None
        return Window(s, e)

    festivals = _festivals_today(raw, d, warnings)
    transit = payload.get("transits") if isinstance(payload.get("transits"), Mapping) else None

    return Day(d, weekday, location, location_display, tithi, paksha, nak,
               opt_text("yoga"), opt_text("karana"), opt_text("masa_purnimanta"),
               opt_time("sunrise"), opt_time("sunset"),
               opt_window("rahu_kaal"), opt_window("gulika_kaal"), opt_window("yamaghanta"),
               opt_window("abhijit_muhurta"), opt_window("brahma_muhurta"), opt_window("godhuli_muhurta"),
               raw.get("choghadiya") if isinstance(raw.get("choghadiya"), Mapping) else None,
               festivals, transit, tuple(warnings))


def _festivals_today(raw: Mapping[str, Any], today: _date, warnings: list) -> Tuple[Festival, ...]:
    """A festival is 'today' only on explicit upstream evidence.

    Preferred: raw['festivals_today'] = [{"name_en": ...}] (ask upstream to add this).
    Fallback : an entry in upcoming_festivals whose date == today AND days_away == 0.
    Conflicting evidence (one true, the other false) is rejected, never resolved by guessing.
    """
    out: list[Festival] = []
    explicit = raw.get("festivals_today")
    if explicit is not None:
        if not isinstance(explicit, list):
            raise DataError("today.festivals_today must be a list when supplied")
        for x in explicit:
            name = _text(x.get("name_en") if isinstance(x, Mapping) else None, MAX_NAME)
            if name:
                out.append(Festival(name, today))
            else:
                warnings.append("festivals_today: skipped entry without name_en")
        # An explicit list is authoritative, including an explicit empty list.
        return tuple(out)
    for x in raw.get("upcoming_festivals") or []:
        if not isinstance(x, Mapping):
            warnings.append("upcoming_festivals: skipped non-object entry"); continue
        name = _text(x.get("name_en"), MAX_NAME)
        try:
            fd = datetime.strptime(str(x.get("date")), "%Y-%m-%d").date()
        except ValueError:
            continue  # unparseable upcoming entries can never become a 'today' festival
        days_away = x.get("days_away")
        is_today_by_date = fd == today
        is_today_by_count = days_away == 0 and not isinstance(days_away, bool)
        if is_today_by_date and is_today_by_count and name:
            out.append(Festival(name, fd))
        elif is_today_by_date != is_today_by_count:
            warnings.append(f"festival {name!r}: date/days_away disagree - NOT treated as today")
    return tuple(out)


def post_warnings(day: Day, *, include_node_motion: bool = False) -> Tuple[str, ...]:
    """Return warnings relevant to a post type. Node normalization is transit-only."""
    if include_node_motion:
        return tuple(day.warnings)
    return tuple(w for w in day.warnings if "motion normalised to Retrograde" not in w)
