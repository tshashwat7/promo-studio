"""Procedural backgrounds (NumPy). Deterministic, offline, no AI generation.

Design rules that keep output byte-reproducible across machines:
  * only + - * / sqrt and polynomial falloffs (no sin/cos/exp: libm results can differ);
  * no random numbers: bokeh positions come from an R2 low-discrepancy sequence;
  * quantise once, at the end, with rint.
Backgrounds stay light so the maroon/ink text and white cards keep their contrast
(enforced by tests/test_studio.py).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence, Tuple
import numpy as np
from PIL import Image
from ..theme import W, H, CREAM, GOLD_LIGHT


def _rgb(hex_color: str) -> np.ndarray:
    h = hex_color.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def _smooth(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


@dataclass(frozen=True)
class Glow:
    cx: float; cy: float; radius: float; color: str; strength: float


@dataclass(frozen=True)
class Theme:
    stops: Sequence[Tuple[float, str]] = ()          # vertical gradient: (0..1, colour)
    glows: Sequence[Glow] = ()
    bokeh: int = 0                                   # number of faint gold discs
    bokeh_strength: float = 0.10


THEMES = {
    "cream": Theme(),                                # flat brand cream (identical to v3)
    # Panchang: cream sky warming towards a low sun.
    "sunrise": Theme(
        stops=((0.0, CREAM), (0.55, CREAM), (1.0, "#F2DFBE")),
        glows=(Glow(540, 1350, 950, GOLD_LIGHT, 0.34),),
    ),
    # Muhurta: a soft high sun behind the header.
    "solar": Theme(
        stops=((0.0, "#F9F1DF"), (0.5, CREAM), (1.0, "#F3E7D0")),
        glows=(Glow(540, 70, 760, GOLD_LIGHT, 0.38),),
    ),
    # Festival: warm glow with a sparse scatter of bokeh.
    "festival_glow": Theme(
        stops=((0.0, CREAM), (1.0, "#F4E4C6")),
        glows=(Glow(540, 520, 820, GOLD_LIGHT, 0.26),),
        bokeh=36,
    ),
}


def _frac(x: float) -> float:
    return x - float(int(x))


class BackgroundEngine:
    @staticmethod
    def create(theme: str = "cream", width: int = W, height: int = H) -> Image.Image:
        try:
            spec = THEMES[theme]
        except KeyError:
            raise ValueError(f"unknown background theme {theme!r}; available: {sorted(THEMES)}") from None
        if not (spec.stops or spec.glows or spec.bokeh):
            return Image.new("RGB", (width, height), CREAM)

        ys = np.arange(height, dtype=np.float64)
        xs = np.arange(width, dtype=np.float64)
        if spec.stops:
            pos = np.array([p for p, _ in spec.stops], dtype=np.float64)
            cols = np.stack([_rgb(c) for _, c in spec.stops])
            t = ys / max(1, height - 1)
            column = np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], axis=1)   # (H, 3)
            img = np.repeat(column[:, None, :], width, axis=1)
        else:
            img = np.empty((height, width, 3), dtype=np.float64); img[:] = _rgb(CREAM)

        for g in spec.glows:
            d = np.sqrt((xs[None, :] - g.cx) ** 2 + (ys[:, None] - g.cy) ** 2) / g.radius
            a = g.strength * (1.0 - _smooth(d))
            img = img * (1.0 - a[..., None]) + _rgb(g.color) * a[..., None]

        for i in range(spec.bokeh):
            # R2 sequence: deterministic, evenly spread, no RNG.
            bx = _frac((i + 1) * 0.7548776662466927) * width
            by = _frac((i + 1) * 0.5698402909980532) * height
            br = 14.0 + 40.0 * _frac((i + 1) * 0.6180339887498949)
            x0, x1 = max(0, int(bx - br)), min(width, int(bx + br) + 1)
            y0, y1 = max(0, int(by - br)), min(height, int(by + br) + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            d = np.sqrt((xs[None, x0:x1] - bx) ** 2 + (ys[y0:y1, None] - by) ** 2) / br
            a = spec.bokeh_strength * (1.0 - _smooth(d))
            img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1.0 - a[..., None]) + _rgb(GOLD_LIGHT) * a[..., None]

        return Image.fromarray(np.rint(np.clip(img, 0, 255)).astype(np.uint8), "RGB")
