"""Daily Panchang layout (English and Hindi); shared design system lives in card_kit."""
from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from . import card_kit as kit
from .card_kit import ICON, ICONS, LANGUAGES, LEFT, Item, Language, _cell, _icon_image, _pick, _text
from .models import PostSpec

__all__ = ["ICON", "ICONS", "LEFT", "RIGHT", "HEADER_RIGHT", "FACT_BOTTOM", "Item",
           "_icon_image", "plan", "render_panchang", "wash"]

RIGHT, RULE_RIGHT = 864, 840
HEADER_RIGHT = 740  # The moon occupies x >= 740 above y = 330.
FACT_TOP, FACT_BOTTOM = 312, 1024  # Distant temples rise from y ≈ 1030.
TWO_COLUMNS = ((190, 317), (547, 317))
THREE_COLUMNS = ((190, 202), (424, 202), (658, 202))
HERO_GAP, COMPACT_HEIGHT, TAGGED_HEIGHT = 14, 86, 114
MIN_GAP, MAX_GAP = 12, 36
NOTE_GAP, NOTE_HEIGHT = 20, 28
WASH_AREAS = ((170, 150, 740, 300), (160, 290, 820, 1000))


def wash(image: Image.Image) -> Image.Image:
    return kit.wash(image, WASH_AREAS)


def _until(lang: Language, facts: dict, key: str, when: date) -> str:
    end = facts.get(f"{key}_end", "")
    end_day = facts.get(f"{key}_end_date")
    if end_day and date.fromisoformat(end_day) != when:
        end_day = date.fromisoformat(end_day)
        end = lang.on_day.format(time=end, day=end_day.day, month=lang.month_short(end_day))
    return lang.until.format(time=end)


def plan(draw: ImageDraw.ImageDraw, facts: dict, when: date,
         language: str = "en") -> list[Item]:
    """Every element with its box; raises instead of truncating or overlapping art."""
    lang = LANGUAGES[language]
    values = lang.values(facts)
    city = kit.city_of(lang, facts)
    items, shift = kit.header(draw, lang, lang.title, when, city, HEADER_RIGHT)
    top = FACT_TOP + shift

    muhurta = [key for key in ("abhijit", "rahu") if key in facts]
    hero_height = lang.hero[0]
    sections = (COMPACT_HEIGHT, COMPACT_HEIGHT, TAGGED_HEIGHT)
    fixed = (2 * hero_height + HERO_GAP + sum(sections) + 2 * len(sections)
             + NOTE_GAP + NOTE_HEIGHT)
    gap = min(MAX_GAP, (FACT_BOTTOM - top - fixed) // (2 * len(sections)))
    if gap < MIN_GAP:
        gap = MIN_GAP

    y = top
    full = RIGHT - LEFT
    masa = lang.masa.format(masa=values.get("masa", ""), system=lang.system)
    items += _cell(draw, lang, "tithi", values["tithi"], LEFT, full, y, hero=True,
                   detail=f"{masa} · {_until(lang, facts, 'tithi', when)}")
    y += hero_height + HERO_GAP
    items += _cell(draw, lang, "nakshatra", values["nakshatra"], LEFT, full, y, hero=True,
                   detail=_until(lang, facts, "nakshatra", when))
    y += hero_height

    rows = [[("yoga", values.get("yoga", "")), ("karana", values.get("karana", ""))],
            [("sunrise", facts.get("sunrise", "")), ("sunset", facts.get("sunset", "")),
             ("moonrise", facts.get("moonrise", ""))]]
    for cells, height in zip(rows, sections):
        y += gap
        items.append(Item("rule", (LEFT, y, RULE_RIGHT, y + 2), "rule", fill=kit.DIVIDER))
        y += 2 + gap
        columns = TWO_COLUMNS if len(cells) == 2 else THREE_COLUMNS
        for (key, value), (x, column_width) in zip(cells, columns):
            items += _cell(draw, lang, key, value, x, column_width, y)
        y += height

    if muhurta:
        y += gap
        items.append(Item("rule", (LEFT, y, RULE_RIGHT, y + 2), "rule", fill=kit.DIVIDER))
        y += 2 + gap
        tagged = any(f"{key}_auspicious" in facts for key in muhurta)
        for key, (x, column_width) in zip(muhurta, TWO_COLUMNS):
            items += _cell(draw, lang, key, facts[key], x, column_width, y,
                           auspicious=facts.get(f"{key}_auspicious"))
        y += TAGGED_HEIGHT if tagged else COMPACT_HEIGHT

    if city:
        note = lang.note.format(city=city)
        y += NOTE_GAP
        items.append(_text(draw, LEFT, y + 22, note,
                           _pick(draw, lang, "note", note, full, (24, 22)), kit.INK, "note"))

    items.append(kit.button(draw, lang))
    return items


def render_panchang(spec: PostSpec, image: Image.Image, language: str = "en") -> Image.Image:
    facts = spec.to_dict()["facts"]
    items = plan(ImageDraw.Draw(image), facts, date.fromisoformat(spec.date), language)
    return kit.finish(image, items, WASH_AREAS)
