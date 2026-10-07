"""HarfBuzz-shaped text for Pillow builds without libraqm (required for correct Devanagari)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    import freetype
    import uharfbuzz as hb
except ImportError:
    freetype = None
    hb = None

from PIL import Image, ImageFont


class ShapedFont:
    """Duck-types the parts of ImageFont the card uses: path, size, length, bbox, draw."""

    def __init__(self, path: Path, size: int):
        self.path = str(path)
        self.size = size
        if freetype is not None and hb is not None:
            self.face = freetype.Face(self.path)
            self.face.set_pixel_sizes(0, size)
            self.hb_font = hb.Font(hb.Face(Path(path).read_bytes()))
            self.hb_font.scale = (self.face.size.x_ppem * 64, self.face.size.y_ppem * 64)
            self._masks: dict[int, tuple[Image.Image | None, int, int]] = {}
            self.has_hb = True
        else:
            self.has_hb = False
            self.pil_font = ImageFont.truetype(self.path, size)

    def _glyphs(self, text: str):
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.hb_font, buffer)
        pen_x = pen_y = 0
        for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions):
            yield info.codepoint, (pen_x + pos.x_offset) / 64, (pen_y + pos.y_offset) / 64
            pen_x += pos.x_advance
            pen_y += pos.y_advance
        self._advance = pen_x / 64

    def _mask(self, glyph_id: int):
        if glyph_id not in self._masks:
            self.face.load_glyph(glyph_id, freetype.FT_LOAD_RENDER)
            slot = self.face.glyph
            bitmap = slot.bitmap
            mask = (Image.frombytes("L", (bitmap.width, bitmap.rows), bytes(bitmap.buffer))
                    if bitmap.width and bitmap.rows else None)
            self._masks[glyph_id] = (mask, slot.bitmap_left, slot.bitmap_top)
        return self._masks[glyph_id]

    def getlength(self, text: str) -> float:
        if not self.has_hb:
            return self.pil_font.getlength(text)
        for _ in self._glyphs(text):
            pass
        return self._advance

    def covers(self, text: str) -> bool:
        """False if any character would render as the font's missing-glyph box."""
        if not self.has_hb:
            return True
        return all(glyph_id != 0 for glyph_id, _, _ in self._glyphs(text))

    def bbox(self, x: int, baseline: int, text: str) -> tuple[int, int, int, int]:
        if not self.has_hb:
            from PIL import ImageDraw
            img = Image.new("L", (1, 1))
            d = ImageDraw.Draw(img)
            return d.textbbox((x, baseline), text, font=self.pil_font, anchor="ls")
        boxes = []
        for glyph_id, gx, gy in self._glyphs(text):
            mask, left, top = self._mask(glyph_id)
            if mask is not None:
                x0, y0 = round(x + gx + left), round(baseline - gy - top)
                boxes.append((x0, y0, x0 + mask.width, y0 + mask.height))
        if not boxes:
            return x, baseline, x, baseline
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    def draw(self, image: Image.Image, origin: tuple[int, int], text: str, fill: str) -> None:
        if not self.has_hb:
            from PIL import ImageDraw
            d = ImageDraw.Draw(image)
            d.text(origin, text, font=self.pil_font, fill=fill, anchor="ls")
            return
        x, baseline = origin
        for glyph_id, gx, gy in self._glyphs(text):
            mask, left, top = self._mask(glyph_id)
            if mask is not None:
                image.paste(Image.new("RGB", mask.size, fill),
                            (round(x + gx + left), round(baseline - gy - top)), mask)


@lru_cache(maxsize=None)
def shaped(path: str, size: int) -> ShapedFont:
    return ShapedFont(Path(path), size)
