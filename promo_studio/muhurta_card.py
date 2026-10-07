"""Plan Your Day (Muhurta) layout in English and Hindi; shared design system lives in card_kit."""
from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from . import card_kit as kit
from .card_kit import LANGUAGES, LEFT, Item, Language, _cell, _icon_image, _length, _pick, _text
from .models import PostSpec, minutes

RIGHT, RULE_RIGHT = 864, 840
HEADER_RIGHT = 900  # The carved pillar starts near x = 990.
FACT_TOP, FACT_BOTTOM = 312, 1060  # Distant temples rise from y ≈ 1090.
TWO_COLUMNS = ((190, 317), (547, 317))
BAR_HEIGHT, BAR_GAP = 20, 3
TAGGED_HEIGHT, ROW_GAP = 114, 12
WASH_AREAS = ((170, 150, 900, 300), (160, 290, 880, 1040))
QUALITY_COLOURS = {"Best": "#3B5B2A", "Auspicious": "#6F8A3C",
                   "Neutral": "#C9A66B", "Inauspicious": "#8A2A2A"}
SLOT_METRICS = {"en": (64, 30, 58), "hi": (72, 34, 64)}
WINDOW_ORDER = ("abhijit", "rahu", "yamaganda", "gulika")


def wash(image: Image.Image) -> Image.Image:
    return kit.wash(image, WASH_AREAS)


def _label(lang: Language, facts: dict, key: str) -> str:
    name = facts.get(f"{key}_name_{lang.source}") or lang.labels.get(key, key.upper())
    return name.upper() if lang.upper else name


def _timeline(draw, lang: Language, facts: dict, y: int) -> tuple[list[Item], int]:
    """Section label, a proportional sunrise-to-sunset bar, and the two end times."""
    items = [kit.label_item(draw, lang, LEFT, y + 26, lang.labels["choghadiya"], RIGHT - LEFT,
                            "label:choghadiya")]
    rise, sset = minutes(facts["sunrise"]), minutes(facts["sunset"])
    scale = (RIGHT - LEFT) / (sset - rise)
    top = y + 44
    for i, slot in enumerate(facts["choghadiya"]):
        x0 = LEFT + round((minutes(slot["start"]) - rise) * scale)
        x1 = LEFT + round((minutes(slot["end"]) - rise) * scale) - (BAR_GAP if i < 7 else 0)
        items.append(Item("bar", (x0, top, x1, top + BAR_HEIGHT), f"bar:{i}",
                          slot["name_en"], fill=QUALITY_COLOURS.get(slot["quality_en"], "#6F8A3C")))
    baseline = top + BAR_HEIGHT + 34
    font = _pick(draw, lang, "detail", facts["sunrise"], 200, lang.sizes.get("detail", (24, 22)))
    items.append(Item("icon", (LEFT, baseline - 28, LEFT + 32, baseline + 4), "icon:sunrise",
                      "sunrise"))
    items.append(_text(draw, LEFT + 40, baseline, facts["sunrise"], font, kit.INK, "sunrise"))
    sunset_x = RIGHT - round(_length(draw, facts["sunset"], font))
    items.append(Item("icon", (sunset_x - 40, baseline - 28, sunset_x - 8, baseline + 4),
                      "icon:sunset", "sunset"))
    items.append(_text(draw, sunset_x, baseline, facts["sunset"], font, kit.INK, "sunset"))
    return items, baseline + 18


def _slots(draw, lang: Language, facts: dict, y: int) -> tuple[list[Item], int]:
    """Eight Choghadiya in two time-ordered columns: morning left, afternoon right."""
    height, name_base, time_base = SLOT_METRICS[lang.code]
    items = []
    for i, slot in enumerate(facts["choghadiya"]):
        (x, width), row = TWO_COLUMNS[i // 4], i % 4
        top = y + row * height
        colour = QUALITY_COLOURS.get(slot["quality_en"], "#6F8A3C")
        items.append(Item("bar", (x, top + 8, x + 8, top + height - 8), f"swatch:{i}",
                          slot["name_en"], fill=colour))
        text_x, text_width = x + 22, width - 22
        name = slot.get(f"name_{lang.source}", slot["name_en"])
        quality = slot.get(f"quality_{lang.source}", slot["quality_en"])
        quality = quality.upper() if lang.upper else quality
        name_item = _text(draw, text_x, top + name_base, name,
                          _pick(draw, lang, "value", name, text_width, lang.sizes.get("compact", (32, 30))),
                          kit.MAROON, f"slot:{i}")
        quality_x = name_item.box[2] + 14
        quality_item = _text(draw, quality_x, top + name_base, quality,
                             kit.font_for(lang, "tag", 22), kit.LABEL, f"quality:{i}",
                             lang.tracking)
        times = f"{slot['start']} – {slot['end']}"
        items += [name_item, quality_item,
                  _text(draw, text_x, top + time_base, times,
                        _pick(draw, lang, "detail", times, text_width, lang.sizes.get("detail", (24, 22))),
                        kit.INK, f"time:{i}")]
    return items, y + 4 * height


def plan(draw: ImageDraw.ImageDraw, facts: dict, when: date,
         language: str = "en") -> list[Item]:
    """Every element with its box; raises instead of truncating or overlapping art."""
    lang = LANGUAGES[language]
    city = kit.city_of(lang, facts)
    items, shift = kit.header(draw, lang, lang.labels["muhurta_title"], when, city, HEADER_RIGHT)
    y = FACT_TOP + shift

    timeline, y = _timeline(draw, lang, facts, y)
    slots, y = _slots(draw, lang, facts, y + 8)
    items += timeline + slots

    y += 16
    items.append(Item("rule", (LEFT, y, RULE_RIGHT, y + 2), "rule", fill=kit.DIVIDER))
    y += 22
    present = [key for key in WINDOW_ORDER if key in facts]
    for index, key in enumerate(present):
        x, width = TWO_COLUMNS[index % 2]
        top = y + (index // 2) * (TAGGED_HEIGHT + ROW_GAP)
        items += _cell(draw, lang, key, facts[key], x, width, top,
                       auspicious=facts.get(f"{key}_auspicious"),
                       label=_label(lang, facts, key))
    y += 2 * TAGGED_HEIGHT + ROW_GAP

    if city:
        note = lang.note.format(city=city)
        y += 16
        items.append(_text(draw, LEFT, y + 22, note,
                           _pick(draw, lang, "note", note, RIGHT - LEFT, (24, 22)),
                           kit.INK, "note"))
    items.append(kit.button(draw, lang))
    return items


def render_muhurta(spec: PostSpec, image: Image.Image, language: str = "en") -> Image.Image:
    facts = spec.to_dict()["facts"]
    items = plan(ImageDraw.Draw(image), facts, date.fromisoformat(spec.date), language)
    return kit.finish(image, items, WASH_AREAS)


__all__ = ["plan", "render_muhurta", "wash", "_icon_image", "LEFT", "RIGHT", "HEADER_RIGHT",
           "FACT_BOTTOM"]
