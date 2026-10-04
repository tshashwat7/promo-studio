"""Which post? Pure function of validated Day + registry. No Pillow, no I/O."""
from __future__ import annotations
from typing import Callable, List, Optional
from .models import Day, DataError
from .posts import REGISTRY
from .spec import PostSpec

# Ordered candidate kinds per rule; first one that is registered AND can build a spec wins.
def _festival(day): return ["festival"] if day.festivals_today else []
WEEKDAY_RULES = {
    "Tuesday": ["muhurta"], "Thursday": ["muhurta"], "Saturday": ["kundli"], "Wednesday": ["chakra"],
    "Friday": ["transit"],
    "Sunday": ["panchang"], "Monday": ["panchang"],
}
FALLBACK = "panchang"

def candidates(day: Day) -> List[str]:
    return _festival(day) + WEEKDAY_RULES.get(day.weekday, []) + [FALLBACK]

def select(day: Day) -> PostSpec:
    for kind in candidates(day):
        pt = REGISTRY.get(kind)
        if pt is None:
            continue                                   # e.g. 'transit' not implemented yet
        spec = pt.build(day)
        if spec is not None:
            return spec
    raise DataError("no post type could be built from this payload")
