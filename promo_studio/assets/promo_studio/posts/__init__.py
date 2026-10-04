"""Post registry. Add a post type = add one module with @register. Nothing else changes."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from ..models import Day
from ..spec import PostSpec

@dataclass(frozen=True)
class PostType:
    kind: str
    build: Callable[[Day], Optional[PostSpec]]   # None => prerequisites unmet, selector falls back
    render: Callable[[PostSpec], "Image.Image"]

REGISTRY: Dict[str, PostType] = {}

def register(kind, build):
    def deco(render):
        REGISTRY[kind] = PostType(kind, build, render); return render
    return deco

from . import panchang, muhurta, festival, transit, showcases  # noqa: E402,F401  (populate registry)
