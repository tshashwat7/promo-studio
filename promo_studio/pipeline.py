"""Offline, single-post generation with an atomic write and factual caption hand-off."""
from __future__ import annotations

import hashlib
import io
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from PIL import ImageDraw, ImageFont

try:
    from make_cards import card_chakra, card_festival, card_kundli, card_panchang, card_plan, card_transit
    from make_post import find_font
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from make_cards import card_chakra, card_festival, card_kundli, card_panchang, card_plan, card_transit
    from make_post import find_font

from .adapter import adapt_siddhanta
from .mock_art import brand, slides as render_slides
from .models import DataError
from .selector import select


CAPTION_SYSTEM_PROMPT = (
    "Write a social caption using ONLY the supplied facts. Do not infer dates, events, "
    "planetary effects, predictions, health benefits, or personal scores. "
    "Keep illustrative feature previews clearly illustrative. "
    "Attribute time-sensitive windows to their location."
)


CAROUSEL_SLIDES = {"transit": 2}


class PromoStudio:
    def __init__(self, output_dir: str | Path = "output"):
        self.output_dir = Path(output_dir)

    def generate(self, daily: Mapping[str, Any], muhurta_data: Mapping[str, Any], *,
                 expected_date: date | None = None, overwrite: bool = True,
                 hindi_font: Path | None = None, language: str = "en",
                 card: str | None = None) -> dict:
        if expected_date is None:
            expected_date = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
        data, muhu = adapt_siddhanta(daily, muhurta_data, expected_date)
        spec = select(data, muhu, card)
        suffix = "" if language == "en" else f"_{language}"
        paths = self._paths(spec, suffix, CAROUSEL_SLIDES.get(spec.kind, 1))
        caption = spec.to_dict()
        result = {"post_type": spec.kind, "language": language, "path": str(paths[0]),
                  "paths": [str(p) for p in paths], "illustrative": spec.illustrative,
                  "caption_input": caption, "caption_system_prompt": CAPTION_SYSTEM_PROMPT,
                  "warnings": list(muhu.get("warnings", []))}
        if all(p.exists() for p in paths) and not overwrite:
            result.update(sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest(), skipped=True)
            return result
        font = find_font([r"C:\Windows\Fonts\Nirmala.ttc",
                          "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"], hindi_font)
        images = render_slides(spec, language)
        if images is None and language != "en":
            raise DataError(f"The {language!r} card needs the curated Panchang template")
        curated = images is not None
        image = images[0] if images else None
        if image is not None:
            pass
        elif spec.kind == "panchang":
            image = card_panchang(data, muhu, font)
        elif spec.kind == "muhurta":
            featured = [s for s in spec.to_dict()["facts"]["choghadiya"] if s["is_auspicious"]]
            muhu["choghadiya"]["day"] = featured
            # The existing card requires Abhijit and Rahu; do not invent missing windows.
            if not all(k in muhu["muhurtas"] for k in ("abhijit_muhurta", "rahu_kaal")):
                raise DataError("This Muhurta renderer needs both Abhijit and Rahu Kaal windows")
            image = card_plan(data, muhu, font)
        elif spec.kind == "festival":
            image = card_festival(data, muhu, font, featured={
                "date": spec.date, "name_en": caption["facts"]["festival"],
                "name_hi": data["today"]["festivals_today"][0]["name_hi"], "category": "major"})
        elif spec.kind == "transit":
            from .selector import _transit
            key, _ = _transit(data)
            if not isinstance(data["transits"].get("positions", {}).get("moon"), dict):
                raise DataError("transit renderer needs a Moon position")
            image = card_transit(data, muhu, font, featured_planet=key)
        elif spec.kind == "kundli":
            image = card_kundli(data, muhu, font)
        else:
            image = card_chakra(data, muhu, font)
        if spec.illustrative and not curated and spec.kind != "chakra":
            label_font = ImageFont.truetype(str(find_font([
                r"C:\Windows\Fonts\segoeuib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])), 24)
            ImageDraw.Draw(image).text((image.width // 2, 1136), "Illustrative feature preview",
                                       fill="#FFF1D8" if spec.kind == "chakra" else "#82272A",
                                       font=label_font, anchor="ma")
        if not curated:
            images = [image]
            paths = self._paths(spec, suffix, 1)
            result.update(path=str(paths[0]), paths=[str(paths[0])])
        images = [brand(i, spec.kind if curated else None) for i in images]
        self.output_dir.mkdir(parents=True, exist_ok=True)
        digests = [self._write(i, p) for i, p in zip(images, paths)]
        result.update(sha256=digests[0], sha256s=digests, skipped=False,
                      width=images[0].width, height=images[0].height)
        return result

    def _paths(self, spec, suffix: str, count: int) -> list[Path]:
        stem = f"{spec.date}_{spec.kind}{suffix}"
        if count == 1:
            return [self.output_dir / f"{stem}_1080x1350.png"]
        return [self.output_dir / f"{stem}_{i}_1080x1350.png" for i in range(1, count + 1)]

    def _write(self, image, path: Path) -> str:
        """Atomic replace, so a crash never leaves a half-written post."""
        stream = io.BytesIO()
        image.save(stream, format="PNG", optimize=True)
        content = stream.getvalue()
        fd, temp = tempfile.mkstemp(dir=self.output_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(content)
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        return hashlib.sha256(content).hexdigest()
