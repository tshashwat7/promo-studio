"""Bilingual, explicitly illustrative Kundli feature preview (never a birth chart)."""
from __future__ import annotations

from PIL import Image, ImageDraw

from graphics.ornament_engine import ornament

from . import card_kit as kit
from .card_kit import Item, _length, _pick, _text


COPY = {
    "en": {
        "title": "Your Kundli",
        "subtitle": "A personal chart starts with your birth details",
        "sample": "SAMPLE",
        "features": ("Lagna chart", "Navamsa chart", "Dasha periods", "Yogas"),
        "disclaimer": "Decorative example · not a calculated birth chart",
        "button": "Explore in Siddhanta",
    },
    "hi": {
        "title": "आपकी कुंडली",
        "subtitle": "आपकी जन्म जानकारी से व्यक्तिगत कुंडली बनती है",
        "sample": "नमूना",
        "features": ("लग्न कुंडली", "नवांश कुंडली", "दशा अवधि", "योग"),
        "disclaimer": "केवल चित्रण · यह गणना की हुई जन्म कुंडली नहीं है",
        "button": "सिद्धान्त पर देखें",
    },
}

CHART_BOX = (173, 330, 908, 1065)
FEATURE_BOXES = ((114, 1020, 527, 1081), (548, 1020, 961, 1081),
                 (114, 1092, 527, 1153), (548, 1092, 961, 1153))


def plan(draw: ImageDraw.ImageDraw, language: str = "en") -> list[Item]:
    """Measure all copy; keep it clear of the sample chart and the footer."""
    lang = kit.LANGUAGES[language]
    text = COPY[language]
    items = [
        _text(draw, 190, 110, lang.brand, kit.font_for(lang, "brand", lang.sizes["brand"][0]),
            kit.MAROON, "brand"),
        _text(draw, 190, 216, text["title"],
            _pick(draw, lang, "title", text["title"], 550, lang.sizes["title"]),
            kit.MAROON, "title"),
        _text(draw, 190, 291, text["subtitle"],
            _pick(draw, lang, "date", text["subtitle"], 780, (30, 28, 26)),
            kit.INK, "subtitle"),
    ]
    sample = text["sample"]
    sample_font = _pick(draw, lang, "label", sample, 112, (26, 24))
    items.append(_text(draw, round(540 - _length(draw, sample, sample_font) / 2), 706,
                       sample, sample_font, kit.MAROON, "sample"))
    for index, (label, box) in enumerate(zip(text["features"], FEATURE_BOXES)):
        left, top, right, bottom = box
        items.append(Item("panel", box, f"feature-panel:{index}"))
        items.append(_text(draw, left + 28, top + 41, label,
                           _pick(draw, lang, "value", label, right - left - 56,
                                 (29, 27, 25) if language == "hi" else (29, 27)),
                           kit.MAROON, f"feature:{index}"))
    disclaimer = text["disclaimer"]
    items.append(_text(draw, 120, 1203, disclaimer,
                       _pick(draw, lang, "detail", disclaimer, 840, (24, 22)),
                       kit.MAROON, "disclaimer"))
    items.append(kit.button(draw, lang, text["button"]))
    for item in items:
        if item.kind == "text":
            left, top, right, bottom = item.box
            if left < 80 or right > 990 or top < 42 or bottom > 1220:
                raise ValueError(f"Kundli {item.role} is outside the safe text region")
    return items


def render_kundli(image: Image.Image, language: str = "en") -> Image.Image:
    """Compose a decorative *empty* chart, never invented houses or placements."""
    items = plan(ImageDraw.Draw(image), language)
    image = kit.draw_items(image, [Item("panel", (130, 374, 950, 997), "chart-panel")])
    chart = ornament("kundli", CHART_BOX[2] - CHART_BOX[0])
    image.paste(chart, CHART_BOX[:2], chart)
    return kit.finish(image, items, ())
