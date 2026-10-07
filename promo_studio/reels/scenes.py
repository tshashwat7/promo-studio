"""Daily Reel storyboard: five independent, video-safe 9:16 still scenes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from PIL import Image, ImageDraw

from graphics.svg_renderer import rasterize
from promo_studio import card_kit as kit
from promo_studio import mock_art
from promo_studio.models import DataError

WIDTH, HEIGHT = 1080, 1920
SAFE = (80, 250, 1000, 1570)
CONTENT = (116, 432, 964, 1418)
DURATIONS = (2, 5, 5, 7, 4)  # 23 seconds; future video timing, not yet an MP4.
BACKGROUND = "svg/reels-universe.svg"
MAX_BACKGROUND_BYTES = 100_000
GOLD, WHITE, MUTED = "#F5CC84", "#FFF9EC", "#DFD2BA"
LABELS = {
    "en": {"series": "TODAY'S PANCHANG", "title": "Panchang + Muhurta",
           "calendar": "Today's date", "tithi": "TITHI", "nakshatra": "NAKSHATRA",
           "until": "Until", "sun": "Sunrise & sunset", "sunrise": "SUNRISE",
           "sunset": "SUNSET", "windows": "Today's time windows",
           "auspicious": "AUSPICIOUS WINDOW", "rahu": "RAHU KAAL · INAUSPICIOUS",
           "reminder": "Times are local to", "save": "Save today's timings",
           "review": "Daily timings · check your location"},
    "hi": {"series": "आज का पंचांग", "title": "पंचांग और मुहूर्त",
           "calendar": "आज की तारीख", "tithi": "तिथि", "nakshatra": "नक्षत्र",
           "until": "समाप्ति", "sun": "सूर्योदय और सूर्यास्त", "sunrise": "सूर्योदय",
           "sunset": "सूर्यास्त", "windows": "आज के समय",
           "auspicious": "शुभ समय", "rahu": "राहुकाल · अशुभ",
           "reminder": "समय इस स्थान के अनुसार", "save": "आज के समय सहेजें",
           "review": "स्थानीय समय · अपना स्थान जाँचें"},
}


@dataclass
class Scene:
    image: Image.Image
    # Text and its measured ink bounds, for automated layout review.
    text_boxes: list[tuple[str, tuple[int, int, int, int]]]
    duration: int


@lru_cache(maxsize=1)
def _vector_background() -> Image.Image:
    """Rasterize the original 9:16 SVG once; never stretch portrait card artwork."""
    root = mock_art.ROOT.resolve()
    path = (root / BACKGROUND).resolve()
    if not path.is_relative_to(root) or path.stat().st_size > MAX_BACKGROUND_BYTES:
        raise DataError("Reel background must be a small curated SVG inside assets")
    image = rasterize(path.read_text(encoding="utf-8"), WIDTH)
    if image.size != (WIDTH, HEIGHT):
        raise DataError("Reel background must have a 1080 × 1920 artboard")
    return image.convert("RGB")


class _Canvas:
    def __init__(self, language: str, spec: dict):
        self.image = _vector_background().copy()
        self.draw = ImageDraw.Draw(self.image)
        self.lang = kit.LANGUAGES[language]
        self.labels = LABELS[language]
        self.spec = spec
        self.boxes: list[tuple[str, tuple[int, int, int, int]]] = []

    def text(self, value: str, x: int, baseline: int, width: int, bottom: int, *,
             sizes: tuple[int, ...], role: str = "value", colour: str = WHITE,
             lines: int = 1) -> None:
        """Measure shaped ink, allow approved sizes, refuse overflow or missing glyphs."""
        if not value or not isinstance(value, str):
            raise DataError("A Reel text field is missing")
        for size in sizes:
            font = kit.font_for(self.lang, role, size)
            if self.lang.shaped and not font.covers(value):
                latin = kit._pillow_font("lora" if role == "title" else "hind", size)
                if latin and all(ord(c) < 128 or c in ' ·–—' for c in value):
                    font = latin
                else:
                    raise DataError(f"Reel font lacks glyphs for {value!r}")
            try:
                parts = kit.wrap(self.draw, value, font, width) if lines > 1 else [value]
            except ValueError:
                continue  # A long word may fit at the next approved size.
            if len(parts) > lines:
                continue
            pitch = size + 19
            items = [kit._text(self.draw, x, baseline + index * pitch, part, font, colour,
                               role) for index, part in enumerate(parts)]
            if all(x <= item.box[0] and item.box[2] <= x + width and
                   SAFE[1] <= item.box[1] and item.box[3] <= bottom <= SAFE[3]
                   for item in items):
                kit.draw_items(self.image, items)
                self.boxes.extend((item.value, item.box) for item in items)
                return
        raise DataError(f"Reel text cannot fit the video-safe area: {value!r}")

    def chrome(self, heading: str, number: int) -> None:
        self.text(self.lang.brand, 116, 330, 440, 359, sizes=(44, 40), role="brand",
                  colour=GOLD)
        self.text(f"{number + 1:02d} / 05", 800, 330, 154, 359,
                  sizes=(29,), role="date", colour=MUTED)
        self.text(heading, 156, 542, 766, 641, sizes=(66, 60, 54, 48),
                  role="title", lines=2, colour=GOLD)

    def finish(self, duration: int) -> Scene:
        return Scene(self.image.convert("RGBA"), self.boxes, duration)


def _when(spec: dict) -> tuple[date, str]:
    when = date.fromisoformat(spec["date"])
    lang = kit.LANGUAGES[spec["language"]]
    return when, f"{when.day} {lang.month(when)} {when.year}"


def _place(canvas: _Canvas, y: int, *, width: int = 754) -> None:
    canvas.text(canvas.spec["location"], 162, y, width, y + 129,
                role="note", sizes=(38, 34, 30), lines=3, colour=MUTED)
    canvas.text("Asia/Kolkata · IST", 162, y + 170, width, y + 215,
                role="note", sizes=(31,), colour=GOLD)


def _fact(canvas: _Canvas, label: str, value: str, y: int, detail: str | None = None) -> None:
    canvas.text(label, 162, y, 740, y + 30, sizes=(30, 28), role="label", colour=GOLD)
    canvas.text(value, 162, y + 90, 754, y + 187, sizes=(62, 56, 50, 44), lines=2)
    if detail:
        canvas.text(detail, 162, y + 224, 754, y + 292, sizes=(34, 30),
                    role="detail", lines=2, colour=MUTED)


def _end(canvas: _Canvas, facts: dict, key: str) -> str | None:
    if key not in facts:
        return None
    date_text = facts[f"{key}_date"]
    when = date.fromisoformat(date_text)
    day = date.fromisoformat(canvas.spec["date"])
    suffix = f", {when.day} {canvas.lang.month_short(when)}" if when != day else ""
    return f"{canvas.labels['until']}: {facts[key]}{suffix}"


def render_daily(spec: dict) -> list[Scene]:
    """Render the *validated planner's* daily deliverable only, never an approval artifact."""
    if spec.get("kind") != "daily" or spec.get("language") not in LABELS or \
            spec.get("timezone") != "Asia/Kolkata":
        raise DataError("Only validated daily plans in Asia/Kolkata have a Reel scene template")
    facts, language = spec["facts"], spec["language"]
    when, date_text = _when(spec)

    cover = _Canvas(language, spec)
    cover.chrome(cover.labels["title"], 0)
    cover.text(cover.labels["calendar"], 162, 794, 740, 837,
               sizes=(32,), role="label", colour=MUTED)
    cover.text(date_text, 162, 897, 754, 990, sizes=(70, 64, 58), lines=2)
    _place(cover, 1066)

    panchang = _Canvas(language, spec)
    panchang.chrome(panchang.labels["series"], 1)
    _fact(panchang, panchang.labels["tithi"], facts[f"tithi_{language}"], 738,
          _end(panchang, facts, "tithi_end"))
    _fact(panchang, panchang.labels["nakshatra"], facts[f"nakshatra_{language}"],
          1082, _end(panchang, facts, "nakshatra_end"))

    sun = _Canvas(language, spec)
    sun.chrome(sun.labels["sun"], 2)
    _fact(sun, sun.labels["sunrise"], facts["sunrise"], 785)
    _fact(sun, sun.labels["sunset"], facts["sunset"], 1120)

    timings = _Canvas(language, spec)
    timings.chrome(timings.labels["windows"], 3)
    good, rahu = facts["auspicious_window"], facts["rahu_kaal"]
    if rahu["is_auspicious"] is not False:
        raise DataError("Rahu Kaal cannot be presented as auspicious")
    _fact(timings, f"{timings.labels['auspicious']} · {good[f'name_{language}']}",
          f"{good['start']} – {good['end']}", 755)
    _fact(timings, timings.labels["rahu"], f"{rahu['start']} – {rahu['end']}", 1110)

    close = _Canvas(language, spec)
    close.chrome(close.labels["save"], 4)
    close.text(close.labels["reminder"], 162, 839, 754, 924,
               sizes=(44, 40, 36), lines=2, colour=MUTED)
    _place(close, 961)
    close.text(close.labels["review"], 162, 1350, 754, 1390,
               sizes=(31, 28), role="note", colour=MUTED)
    return [scene.finish(duration) for scene, duration in
            zip((cover, panchang, sun, timings, close), DURATIONS)]
