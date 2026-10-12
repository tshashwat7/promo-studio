"""Festival card (today or upcoming) on curated scene art, in English and Hindi."""
from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw, ImageOps

from . import card_kit as kit
from . import mock_art
from .card_kit import LANGUAGES, Item, Language, _length, _pick, _text
from .models import PostSpec

COPY = {
    "en": {"today": "FESTIVAL TODAY", "upcoming": "UPCOMING FESTIVAL", "tithi": "TITHI",
           "nakshatra": "NAKSHATRA", "days": "In {n} days", "tomorrow": "Tomorrow",
           "same_day": "Today", "cta": "Check Festival & Muhurat"},
    "hi": {"today": "आज का पर्व", "upcoming": "आगामी पर्व", "tithi": "तिथि",
           "nakshatra": "नक्षत्र", "days": "{n} दिन बाद", "tomorrow": "कल",
           "same_day": "आज", "cta": "पर्व और मुहूर्त देखें"},
}
# Per scene: (left, top, right, lowest bottom) of the parchment panel, read off each scene
# so the deity, lamps, garlands and temples stay visible.
SCENE_PANELS = {
    "content/festivals/Diwali Ghat Glow Template.webp": (250, 140, 800, 880),
    "content/festivals/Divine Dawn by the Sacred River.webp": (30, 55, 600, 850),
    "content/festivals/Krishna and Radha by the Sacred Sunrise.webp": (45, 55, 500, 820),
    "content/festivals/Lord Vishnu by the Lotus Lake.webp": (560, 55, 1040, 820),
    "content/festivals/Serene Vishnu on Sheshnag at Sunrise.webp": (30, 45, 600, 800),
    "content/festivals/Generic festival.webp": (540, 120, 1020, 860),
    "content/festivals/Lord Vishnu at Sunrise by the Lotus Lake.webp": (30, 45, 600, 800),
    "content/festivals/Moonlit Krishna by the Yamuna.webp": (60, 200, 520, 890),
    "content/festivals/Shiva Beneath the Himalayan Moon.png": (35, 55, 565, 850),
    "content/festivals/Shivratri Festive Diptych.webp": (230, 215, 670, 905),
    # Vishnu fills the scene; only the sky band above the serpent hoods (y 430) is open.
    "content/festivals/Vishnu on Shesha Beneath a Cosmic Sky.webp": (270, 24, 1050, 416),
    "content/festivals/Vishnu by the Lotus Lake at Dawn.webp": (550, 45, 1050, 800),
    "content/festivals/navratri_festival.webp": (520, 130, 1030, 860),
    "content/festivals/saraswati_festival.webp": (530, 130, 1030, 860),
    "content/festivals/Hanuman Over Golden Temple Valley.webp": (100, 190, 530, 880),
    "content/festivals/Holi Festive Diptych.webp": (330, 160, 810, 810),
}
PAD, LOGO = 36, 56
# Panels at least this wide (inside the padding) use the one-band layout.
WIDE = 640
NAME_SIZES = {"en": (60, 52), "hi": (54, 46)}
# Name line step as a multiple of size; Devanagari matras need more room.
LEADING = {"en": 1.2, "hi": 1.45}
# (date gap, fact label baseline, fact value baseline, fact row height)
SPACING = {"en": (50, 40, 84, 96), "hi": (58, 40, 90, 104)}


class PanelOverflow(ValueError):
    """The copy needs more height than the scene's clear sky allows."""


def festival_name(lang: Language, facts: dict) -> str:
    if lang.source == "hi":
        return facts["festival_hi"]
    name = facts["festival"]
    return name[:-len(" (Start)")] + " Begins" if name.endswith(" (Start)") else name


def _name_lines(draw, lang: Language, value: str, width: int):
    """One line at an approved size if possible, else two; never shrink further."""
    sizes = NAME_SIZES[lang.code]
    for size in sizes:
        font = kit.font_for(lang, "title", size)
        if _length(draw, value, font) <= width:
            return size, font, [value]
    for size in sizes:
        font = kit.font_for(lang, "title", size)
        try:
            lines = kit.wrap(draw, value, font, width)
        except ValueError:
            continue
        if len(lines) <= 2:
            return size, font, lines
    raise ValueError(f"{value!r} does not fit two lines at approved sizes {sizes}")


def _countdown(copy: dict, days: int) -> str:
    if days == 0:
        return copy["same_day"]
    return copy["tomorrow"] if days == 1 else copy["days"].format(n=days)


def plan(draw: ImageDraw.ImageDraw, facts: dict, when: date, art: str,
         language: str = "en") -> list[Item]:
    lang, copy = LANGUAGES[language], COPY[language]
    # Allow looking up normalized path without extension if exact match isn't present
    panel_box = SCENE_PANELS.get(art)
    if panel_box is None:
        art_alt = art.replace(".png", ".webp") if art.endswith(".png") else art.replace(".webp", ".png")
        panel_box = SCENE_PANELS.get(art_alt, (540, 120, 1020, 860))
    left, top, right, lowest = panel_box
    date_gap, label_base, value_base, row = SPACING[language]
    x, width = left + PAD, right - left - 2 * PAD
    wide = width >= WIDE
    y = top + (24 if wide else PAD)
    upcoming = facts.get("upcoming", False)
    cta, cta_font = copy["cta"], kit.font_for(lang, "button", 22)
    button_width = round(_length(draw, cta, cta_font)) + 64
    if button_width > width:
        raise ValueError(f"{cta!r} is wider than the festival panel")
    label_width = width - LOGO - 16 - (button_width + 24 if wide else 0)
    items = [Item("logo", (x, y + 4, x + LOGO, y + 4 + LOGO), "logo"),
             kit.label_item(draw, lang, x + LOGO + 16, y + 42,
                            copy["upcoming" if upcoming else "today"], label_width,
                            "label:festival")]
    if wide:
        items.append(Item("button", (x + width - button_width, y, x + width, y + 64), "button",
                          cta, cta_font, kit.BUTTON_TEXT))
    y += 64 + 12
    items.append(Item("rule", (x, y, x + width, y + 2), "rule:top", fill=kit.DIVIDER))
    base = y + 2
    size, font, lines = _name_lines(draw, lang, festival_name(lang, facts), width)
    for i, line in enumerate(lines):
        base += round(size * LEADING[language])
        items.append(_text(draw, x, base, line, font, kit.MAROON, f"name:{i}"))
    day_text = f"{when.day} {lang.month(when)} {when.year}"
    city = kit.city_of(lang, facts)
    base += date_gap
    date_font = kit.font_for(lang, "date", 28)
    if wide:
        line = f"{lang.weekday(when)}, {day_text}" + (f" · {city}" if city else "")
        items.append(_text(draw, x, base, line, _pick(draw, lang, "date", line, width, (28, 26)),
                           kit.INK, "date"))
    else:
        # Narrow panels: the longest weekday + month ("Wednesday, 30 September") cannot share a line.
        place = f"{lang.weekday(when)} · {city}" if city else lang.weekday(when)
        items.append(_text(draw, x, base, day_text, date_font, kit.INK, "date"))
        base += 38
        if _length(draw, place, date_font) > width:
            items.append(_text(draw, x, base, lang.weekday(when), date_font, kit.INK, "weekday"))
            base += 38
            place = city
        items.append(_text(draw, x, base, place, _pick(draw, lang, "date", place, width, (28, 26)),
                           kit.INK, "place"))
    y = base + (20 if wide else 26)
    items.append(Item("rule", (x, y, x + width, y + 2), "rule:facts", fill=kit.DIVIDER))
    y += 2
    if upcoming:
        value = _countdown(copy, facts["days_away"])
        items.append(_text(draw, x, y + 64, value,
                           _pick(draw, lang, "value", value, width, lang.sizes["hero"]),
                           kit.MAROON, "countdown"))
        y += 88
    else:
        source = lang.source == "en"
        column = (width - 32) // 2 if wide else width
        for i, (key, value) in enumerate((
                ("tithi", facts["tithi"] if source else facts["tithi_hi"]),
                ("nakshatra", facts["nakshatra"] if source else facts["nakshatra_hi"]))):
            fx = x + i * (column + 32) if wide else x
            items.append(kit.label_item(draw, lang, fx, y + label_base, copy[key], column,
                                        f"label:{key}"))
            items.append(_text(draw, fx, y + value_base, value,
                               _pick(draw, lang, "value", value, column, lang.sizes["compact"]),
                               kit.MAROON, f"value:{key}"))
            if not wide or i:
                y += row
    if wide:
        bottom = y + 20
    else:
        y += 20
        items.append(Item("button", (x, y, x + button_width, y + 64), "button", cta, cta_font,
                          kit.BUTTON_TEXT))
        bottom = y + 64 + PAD
    if bottom > lowest:
        raise PanelOverflow(f"Festival panel would reach y {bottom}, past {lowest} on {art}")
    return [Item("panel", (left, top, right, bottom), "panel")] + items


def render_festival(spec: PostSpec, art: str, language: str = "en") -> Image.Image:
    image = ImageOps.fit(mock_art._open(art), (mock_art.W, mock_art.H),
                         method=Image.Resampling.LANCZOS)
    items = plan(ImageDraw.Draw(image), spec.to_dict()["facts"], date.fromisoformat(spec.date),
                 art, language)
    image = kit.draw_items(image, items)
    if (mock_art.ROOT / mock_art.LOGO).is_file() or mock_art._resolve_path(mock_art.LOGO).is_file():
        x, y = next(i for i in items if i.kind == "logo").box[:2]
        emblem, mask = kit._logo_medallion(LOGO)
        image.paste(emblem, (x, y), mask)
        ImageDraw.Draw(image).ellipse((x - 1, y - 1, x + LOGO, y + LOGO), outline=kit.LOGO_RING,
                                      width=2)
    return image
