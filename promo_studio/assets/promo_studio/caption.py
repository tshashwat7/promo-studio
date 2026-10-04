"""Factual hand-off contract for an external caption writer such as Gemini."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .spec import PostSpec, _freeze, _thaw

@dataclass(frozen=True)
class CaptionInput:
    post_type: str
    date: str
    facts: Mapping[str, Any]
    illustrative: bool

    def __post_init__(self):
        # Keep the hand-off object itself immutable; to_dict() returns fresh JSON-safe copies.
        object.__setattr__(self, "facts", _freeze(dict(self.facts)))

    def to_dict(self) -> dict:
        return {"post_type": self.post_type, "date": self.date,
                "facts": _thaw(self.facts), "illustrative": self.illustrative}

def caption_input(spec: PostSpec) -> CaptionInput:
    """Create the only content contract that should be supplied to Gemini."""
    return CaptionInput(spec.kind, spec.date, spec.to_dict()["facts"], spec.illustrative)

def system_prompt() -> str:
    return (
        "Write a social caption using ONLY the supplied facts. "
        "Do not invent or infer dates, times, names, scores, astrological claims, "
        "predictions, benefits, or other factual details. Do not turn an upcoming "
        "event into an event happening today. Keep illustrative feature previews "
        "clearly illustrative. If a location is supplied, identify time-sensitive "
        "windows as being for that location. Do not describe Rahu or Ketu as Direct."
    )
