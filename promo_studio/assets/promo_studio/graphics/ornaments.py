"""Pre-rendered vector ornaments.

SVG sources live in assets/ornaments/src/ and are rasterised ONCE, offline, by
tools/build_ornaments.py (CairoSVG, a dev-only dependency). The resulting PNGs are
committed, so production needs only Pillow: no libcairo, no runtime SVG parsing.
"""
from __future__ import annotations
import re
from functools import lru_cache
from pathlib import Path
from PIL import Image

_DIR = Path(__file__).parent.parent / "assets" / "ornaments"
_NAME = re.compile(r"^[a-z0-9_]+$")


class OrnamentError(RuntimeError):
    pass


@lru_cache(maxsize=32)
def _load(name: str) -> Image.Image:
    if not _NAME.match(name):
        raise OrnamentError(f"invalid ornament name {name!r}")
    path = _DIR / f"{name}.png"
    if not path.is_file():
        raise OrnamentError(f"ornament {name!r} not found; run tools/build_ornaments.py")
    with Image.open(path) as im:
        return im.convert("RGBA")


@lru_cache(maxsize=64)
def ornament(name: str, size: int) -> Image.Image:
    src = _load(name)
    return src.resize((int(size), max(1, round(src.height * size / src.width))), Image.Resampling.LANCZOS)


def paste_ornament(im: Image.Image, name: str, center, size: int, opacity: float = 1.0) -> None:
    art = ornament(name, size)
    if opacity < 1.0:
        art = art.copy(); art.putalpha(art.getchannel("A").point(lambda v: int(v * opacity)))
    im.paste(art, (int(center[0] - art.width / 2), int(center[1] - art.height / 2)), art)
