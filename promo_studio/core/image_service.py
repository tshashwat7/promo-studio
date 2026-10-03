"""Per-platform image preparation with Pillow. Originals are never modified."""
from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps


@dataclass(frozen=True)
class Rule:
    min_ratio: float | None = None   # width / height
    max_ratio: float | None = None
    max_width: int = 2048
    min_width: int = 0
    max_bytes: int | None = None


# Working defaults: verify against each platform's current image specs.
RULES = {
    "instagram": Rule(min_ratio=0.8, max_ratio=1.91, max_width=1080, min_width=320, max_bytes=8_000_000),
    "facebook": Rule(max_width=2048),
    "x": Rule(max_width=1600, max_bytes=5_000_000),
    "reddit": Rule(max_width=2048),
}
_MARGIN = 0.005  # stay slightly inside the ratio limits so rounding never pushes us out


class ImageService:
    def __init__(self, temp_dir=None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "promo_studio"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def check(self, platform: str, path: str) -> list[str]:
        if not path or not os.path.exists(path):
            return ["Image file not found."]
        try:
            with Image.open(path) as im:
                width = im.size[0]
        except Exception:
            return ["The image could not be opened."]
        rule = RULES[platform]
        if width < rule.min_width:
            return [f"Image is {width}px wide; {platform} needs at least {rule.min_width}px."]
        return []

    def prepare(self, platform: str, path: str) -> str:
        rule = RULES[platform]
        with Image.open(path) as opened:
            image = self._flatten(ImageOps.exif_transpose(opened))
        image = self._fit_ratio(image, rule)
        if image.width > rule.max_width:
            height = max(1, round(image.height * rule.max_width / image.width))
            image = image.resize((rule.max_width, height), Image.LANCZOS)
        out = self.temp_dir / f"{platform}_{uuid.uuid4().hex}.jpg"
        quality = 90
        while True:
            image.save(out, "JPEG", quality=quality, optimize=True)
            if not rule.max_bytes or out.stat().st_size <= rule.max_bytes or quality <= 50:
                break
            quality -= 10
        return str(out)

    def discard(self, path: str | None) -> None:
        """Delete a prepared temp file (only inside our temp folder)."""
        try:
            if path and Path(path).parent == self.temp_dir:
                os.remove(path)
        except OSError:
            pass

    @staticmethod
    def _flatten(image: Image.Image) -> Image.Image:
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        return image.convert("RGB")

    @staticmethod
    def _fit_ratio(image: Image.Image, rule: Rule) -> Image.Image:
        w, h = image.size
        ratio = w / h
        if rule.min_ratio and ratio < rule.min_ratio:
            new_h = int(w / (rule.min_ratio * (1 + _MARGIN)))
            top = (h - new_h) // 2
            return image.crop((0, top, w, top + new_h))
        if rule.max_ratio and ratio > rule.max_ratio:
            new_w = int(h * rule.max_ratio * (1 - _MARGIN))
            left = (w - new_w) // 2
            return image.crop((left, 0, left + new_w, h))
        return image
