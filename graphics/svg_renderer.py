"""Use CairoSVG if native Cairo is available, otherwise bundled resvg_py."""

from functools import lru_cache
from io import BytesIO

from PIL import Image


@lru_cache(maxsize=64)
def _png(svg_markup: str, width: int | None) -> bytes:
    try:
        import cairosvg

        png = cairosvg.svg2png(bytestring=svg_markup.encode("utf-8"), output_width=width)
    except (ImportError, OSError):
        try:
            import resvg_py

            png = resvg_py.svg_to_bytes(svg_string=svg_markup, width=width)
        except (ImportError, OSError):
            raise ImportError("Neither cairosvg nor resvg_py is available to render SVGs")
    return png


def rasterize(svg_markup: str, width: int | None = None) -> Image.Image:
    return Image.open(BytesIO(_png(svg_markup, width))).convert("RGBA")
