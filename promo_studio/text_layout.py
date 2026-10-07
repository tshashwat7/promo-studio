"""Reusable text placement rules for illustrated cards with protected regions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from PIL import ImageDraw, ImageFont

FontFactory = Callable[[int], ImageFont.FreeTypeFont]


def pick_font(draw: ImageDraw.ImageDraw, value: str, width: int, sizes: tuple[int, ...],
              font_for_size: FontFactory) -> ImageFont.FreeTypeFont:
    """Use the first approved size that fits; refuse rather than shrink further."""
    for size in sizes:
        font = font_for_size(size)
        if draw.textlength(value, font=font) <= width:
            return font
    raise ValueError(f"{value!r} does not fit {width}px at approved sizes {sizes}")


def tracked_width(draw: ImageDraw.ImageDraw, value: str,
                  font: ImageFont.FreeTypeFont, tracking: int) -> int:
    return round(sum(draw.textlength(ch, font=font) for ch in value)
                 + tracking * max(len(value) - 1, 0))


def draw_tracked(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str,
                 font: ImageFont.FreeTypeFont, fill: str, tracking: int) -> None:
    """Letter-spaced text on a baseline; Pillow has no native tracking."""
    x, y = xy
    for ch in value:
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += draw.textlength(ch, font=font) + tracking


def fit_one_line(draw: ImageDraw.ImageDraw, value: str, width: int, height: int,
                 preferred: int, min_size: int, font_for_size: FontFactory
                 ) -> ImageFont.FreeTypeFont:
    """Fit a complete headline or metadata string on exactly one line."""
    for size in range(preferred, min_size - 1, -1):
        font = font_for_size(size)
        if draw.textlength(value, font=font) <= width and size + 8 <= height:
            return font
    raise ValueError(f"Text cannot fit one line in the protected area: {value}")


@dataclass(frozen=True)
class GridRegion:
    """A measured text-safe rectangle; the caller keeps artwork outside it clear."""

    top: int
    bottom: int
    columns: tuple[tuple[int, int], tuple[int, int]]  # (left, available width)
    full_width: tuple[int, int]
    label_height: int = 36
    row_padding: int = 16
    min_pitch: int = 115


def fit_lines(draw: ImageDraw.ImageDraw, value: str, width: int, height: int,
              preferred: int, font_for_size: FontFactory, *, min_size: int = 24,
              max_lines: int = 3) -> tuple[ImageFont.FreeTypeFont, list[str]] | None:
    """Keep time + AM/PM together and refuse text that cannot fit without truncation."""
    if re.search(r"\d{1,2}:\d{2} [AP]M", value):
        for size in range(min(preferred, 36), min_size - 1, -1):
            font = font_for_size(size)
            if draw.textlength(value, font=font) <= width and size + 8 <= height:
                return font, [value]
    words = re.findall(r"\d{1,2}:\d{2}\s+[AP]M|\S+", value)
    for size in range(preferred, min_size - 1, -1):
        font = font_for_size(size)
        lines: list[str] = []
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and draw.textlength(candidate, font=font) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        if (lines and len(lines) <= max_lines and len(lines) * (size + 8) <= height
                and all(draw.textlength(part, font=font) <= width for part in lines)):
            return font, lines
    return None


def paired_rows(draw: ImageDraw.ImageDraw, items: list[tuple[str, str]],
                region: GridRegion, font_for_size: FontFactory,
                preferred_size: Callable[[str], int],
                label_font: ImageFont.FreeTypeFont):
    """Fill safe height with pairs; give either fact a full-width row if needed."""
    if not items:
        return []
    groups = [items[index:index + 2] for index in range(0, len(items), 2)]
    while True:
        pitch = (region.bottom - region.top) // len(groups)
        if pitch < region.min_pitch:
            raise ValueError("Facts cannot fit the card's text-safe region")
        layout = []
        split = False
        for row, group in enumerate(groups):
            cells = []
            for column, (label, value) in enumerate(group):
                x, width = (region.columns[column] if len(group) == 2
                            else region.full_width)
                fit = fit_lines(draw, str(value), width,
                                pitch - region.label_height - region.row_padding,
                                preferred_size(label), font_for_size)
                if fit is None or draw.textlength(label, font=label_font) > width:
                    if len(group) == 1:
                        raise ValueError(f"{label} cannot fit the card's text-safe region")
                    groups[row:row + 1] = [[entry] for entry in group]
                    split = True
                    break
                cells.append((x, width, label, fit))
            if split:
                break
            layout.append((region.top + row * pitch, pitch, cells))
        if not split:
            return layout
