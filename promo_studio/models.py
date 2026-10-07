"""Validated daily facts; never calculate missing astronomical values."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from types import MappingProxyType
from typing import Any, Mapping
import re


class DataError(ValueError):
    """Input is stale, missing, or self-contradictory; do not publish."""


_TIME = re.compile(r"^(1[0-2]|[1-9]):([0-5]\d) ([AP]M)$")


def text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise DataError(f"{field} must be nonempty text (at most 120 characters)")
    return value.strip()


def time(value: Any, field: str) -> str:
    value = text(value, field)
    if not _TIME.fullmatch(value):
        raise DataError(f"{field} must be a 12-hour time such as 6:20 AM")
    return value


def window(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise DataError(f"{field} must contain start and end times")
    return {part: time(value.get(part), f"{field}.{part}") for part in ("start", "end")}


def minutes(value: str) -> int:
    match = _TIME.fullmatch(value)
    if not match:
        raise DataError(f"{value!r} is not a 12-hour time")
    hour, minute, half = int(match[1]) % 12, int(match[2]), match[3]
    return (hour + (12 if half == "PM" else 0)) * 60 + minute


def end_date(day: date, end: str, sunrise: str) -> date:
    """A Panchang day runs sunrise to sunrise, so an end before sunrise is the next morning."""
    return day + timedelta(days=1) if minutes(end) < minutes(sunrise) else day


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class PostSpec:
    kind: str
    date: str
    facts: Mapping[str, Any]
    illustrative: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts", _freeze(dict(self.facts)))

    def to_dict(self) -> dict:
        return {"post_type": self.kind, "date": self.date,
                "facts": _thaw(self.facts), "illustrative": self.illustrative}
