"""Deterministic design tokens and bundled font resolution."""
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont, features

CREAM = "#F7F0E3"; CREAM_DARK = "#E9DDC9"; MAROON = "#6F2638"; GOLD = "#B88A3B"
GOLD_LIGHT = "#D9B86C"; NAVY = "#10233F"; INK = "#2B2522"; MUTED = "#746B63"; WHITE = "#FFFDF8"
MUTED_DEEP = "#5E554D"   # small muted text drawn directly on the (warm) backgrounds: >= 4.5:1 on every theme
W, H, M = 1080, 1350, 76

# Social-first type scale. Nothing intended for the final artwork falls below 20 px.
TYPE = {
    "title": 64,
    "hero": 44,
    "body": 28,
    "label": 22,
    "minimum": 20,
    "meta": 22,
    "footer": 22,
    "hindi_subtitle": 26,
}

class FontError(RuntimeError):
    pass

_BUNDLED = Path(__file__).parent / "assets" / "fonts"
_DIRS = [_BUNDLED]
# Bundled fonts are the production source of truth. External directories remain only
# as an explicit developer override, never as a silent production dependency.
if os.environ.get("SIDDHANTA_FONT_DIR"):
    _DIRS.insert(0, Path(os.environ["SIDDHANTA_FONT_DIR"]))

_ROLES = {
    "sans": ["NotoSans-Regular.ttf"],
    "sans_bold": ["NotoSans-Bold.ttf"],
    "serif_bold": ["NotoSerif-Bold.ttf"],
    "devanagari": ["NotoSansDevanagari-Regular.ttf"],
    "devanagari_bold": ["NotoSansDevanagari-Bold.ttf"],
    "devanagari_serif": ["NotoSerifDevanagari-Regular.ttf"],
    "devanagari_serif_bold": ["NotoSerifDevanagari-Bold.ttf"],
}

@lru_cache(maxsize=None)
def _path(role: str) -> str:
    for d in _DIRS:
        for name in _ROLES[role]:
            p = d / name
            if p.is_file():
                return str(p)
    raise FontError(f"no bundled font for role {role!r}; expected {_ROLES[role]} in {_BUNDLED}")

@lru_cache(maxsize=256)
def get_font(role: str, size: int):
    return ImageFont.truetype(_path(role), int(size))

def sans(size, bold=False): return get_font("sans_bold" if bold else "sans", int(size))
def serif(size): return get_font("serif_bold", int(size))
def devanagari(size, bold=False): return get_font("devanagari_bold" if bold else "devanagari", int(size))
def devanagari_serif(size, bold=False): return get_font("devanagari_serif_bold" if bold else "devanagari_serif", int(size))

def require_raqm() -> None:
    if not features.check("raqm"):
        raise FontError("Pillow libraqm/Harfbuzz/FriBiDi support is required for Devanagari shaping")
