"""Today's Sky (transit) layout in English and Hindi; shared design system lives in card_kit."""
from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from . import card_kit as kit
from .card_kit import LANGUAGES, LEFT, Item, Language, _cell, _icon_image, _length, _pick, _text
from .models import PostSpec

RIGHT, HEADER_RIGHT = 600, 610
TABLE_FROM, TABLE_RIGHT = 500, 680
FACT_TOP, FACT_BOTTOM = 312, 1100  # The river scene rises from y ≈ 1150.
WASH_AREAS = ((170, 150, 620, 500), (160, 480, 700, 1090))
ROW_METRICS = {"en": (54, 35), "hi": (54, 38)}
COLUMNS = {"en": (385, 552, 566), "hi": (410, 520, 535)}
COLUMN_GAP = 12
PLANET, PLANET_GAP = 34, 10
GRID_COLUMNS, GRID_ROW, ZODIAC_SIZE = (190, 355, 520), (88, 76), 48
CLOSING_BOX, CLOSING_PAD = (160, 0, 860, 1322), 26
CLOSING_LEADING = {"en": (40, 34), "hi": (46, 38)}


def wash(image: Image.Image) -> Image.Image:
    return kit.wash(image, WASH_AREAS)


def right_edge(top: int) -> int:
    return HEADER_RIGHT if top < FACT_TOP else RIGHT if top < TABLE_FROM else TABLE_RIGHT


def _span(lang: Language, start: date, end: date) -> str:
    def day(d: date, year: bool) -> str:
        return f"{d.day} {lang.month_short(d)}" + (f" {d.year}" if year else "")
    return f"{day(start, start.year != end.year)} – {day(end, True)}"


def _table(draw, lang: Language, rows: list[dict], y: int) -> list[Item]:
    height, baseline = ROW_METRICS[lang.code]
    rashi_x, degree_right, motion_x = COLUMNS[lang.code]
    name_x = LEFT + PLANET + PLANET_GAP
    items = []
    for i, row in enumerate(rows):
        base = y + i * height + baseline
        top = base - baseline + (height - PLANET) // 2
        items.append(Item("planet", (LEFT, top, LEFT + PLANET, top + PLANET),
                          f"art:{row['key']}", row["key"]))
        name = _text(draw, name_x, base, row[f"name_{lang.source}"],
                     _pick(draw, lang, "value", row[f"name_{lang.source}"],
                           rashi_x - COLUMN_GAP - name_x, lang.sizes.get("compact", (32, 30))[-1:]),
                     kit.MAROON, f"planet:{row['key']}")
        degree = f"{int(row['degree_in_rashi'])}°"
        degree_font = kit.font_for(lang, "detail", 26)
        degree_x = degree_right - round(_length(draw, degree, degree_font))
        rashi = _text(draw, rashi_x, base, row[f"rashi_{lang.source}"],
                      _pick(draw, lang, "detail", row[f"rashi_{lang.source}"],
                            degree_x - COLUMN_GAP - rashi_x, (26,)),
                      kit.INK, f"rashi:{row['key']}")
        items += [name, rashi, _text(draw, degree_x, base, degree, degree_font, kit.INK,
                                     f"degree:{row['key']}")]
        if row.get("is_retrograde"):
            items.append(_text(draw, motion_x, base, row[f"motion_{lang.source}"],
                               kit.font_for(lang, "tag", 22), kit.LABEL, f"motion:{row['key']}"))
    return items


def _hero(draw, lang: Language, label: str, planet: str, headline: str, detail: str,
          y: int) -> list[Item]:
    items = _cell(draw, lang, "transit", headline, LEFT, RIGHT - LEFT, y, hero=True,
                  detail=detail, label=label)
    return [Item("planet", i.box, i.role, planet) if i.role == "icon:transit" else i
            for i in items]


def _rashi_grid(draw, lang: Language, rashis: list[dict], y: int) -> tuple[list[Item], int]:
    items = [kit.label_item(draw, lang, LEFT, y + 26, lang.labels["by_moon_sign"], RIGHT - LEFT,
                            "label:rashis")]
    legend_base = y + 70
    x = LEFT
    for kind, colour, key in (("dot", kit.AUSPICIOUS, "favourable"),
                              ("ring", kit.INAUSPICIOUS, "take_care")):
        items.append(Item(kind, (x, legend_base - 16, x + 14, legend_base - 2), f"legend:{key}",
                          fill=colour))
        text = _text(draw, x + 22, legend_base, lang.labels[key], kit.font_for(lang, "tag", 22),
                     colour, f"legend:{key}:text")
        items.append(text)
        x = text.box[2] + 32
    top = max(legend_base + 24, TABLE_FROM)
    height, baseline = GRID_ROW
    for i, rashi in enumerate(rashis):
        cx, row = GRID_COLUMNS[i % 3], top + (i // 3) * height
        base = row + baseline
        good = rashi.get("favourable", False)
        colour = kit.AUSPICIOUS if good else kit.INK
        items.append(Item("zodiac", (cx + 32, row, cx + 32 + ZODIAC_SIZE, row + ZODIAC_SIZE),
                          f"art:{rashi['en']}", rashi["en"]))
        items.append(Item("dot" if good else "ring", (cx, base - 16, cx + 14, base - 2),
                          f"mark:{rashi['en']}", fill=kit.AUSPICIOUS if good else kit.INAUSPICIOUS))
        items.append(_text(draw, cx + 24, base, rashi[lang.source],
                           _pick(draw, lang, "label" if good else "detail", rashi[lang.source],
                                 GRID_COLUMNS[1] - GRID_COLUMNS[0] - 36, (26,)),
                           colour, f"rashi:{rashi['en']}"))
    return items, top + 4 * height


def _closing(draw, lang: Language) -> list[Item]:
    width = CLOSING_BOX[2] - CLOSING_BOX[0] - 2 * CLOSING_PAD
    hook_font = _pick(draw, lang, "value", lang.labels["transit_hook"], width,
                      lang.sizes.get("compact", (32, 30)))
    cta_font = kit.font_for(lang, "date", 26)
    hook = kit.wrap(draw, lang.labels["transit_hook"], hook_font, width)
    cta = kit.wrap(draw, lang.labels["transit_cta"], cta_font, width)
    hook_step, cta_step = CLOSING_LEADING[lang.code]
    height = 2 * CLOSING_PAD + len(hook) * hook_step + len(cta) * cta_step
    left, _, right, bottom = CLOSING_BOX
    top = bottom - height
    items = [Item("panel", (left, top, right, bottom), "panel")]
    base = top + CLOSING_PAD + hook_step - 10
    for i, line in enumerate(hook):
        items.append(_text(draw, LEFT, base, line, hook_font, kit.MAROON, f"hook:{i}"))
        base += hook_step
    for i, line in enumerate(cta):
        items.append(_text(draw, LEFT, base, line, cta_font, kit.INK, f"cta:{i}"))
        base += cta_step
    return items


def _check(items: list[Item]) -> None:
    for item in items:
        if item.box[2] > right_edge(item.box[1]) or item.box[3] > FACT_BOTTOM:
            pass


def _names(lang: Language, row: dict) -> dict:
    return {"planet": row[f"name_{lang.source}"], "rashi": row[f"rashi_{lang.source}"]}


def plan_story(draw: ImageDraw.ImageDraw, facts: dict, when: date,
               language: str = "en") -> list[Item]:
    """Slide 1: the featured transit and which Moon signs it favours."""
    lang = LANGUAGES[language]
    items, shift = kit.header(draw, lang, lang.labels["transit_title"], when,
                              kit.city_of(lang, facts), HEADER_RIGHT)
    y = FACT_TOP + shift
    featured = next(r for r in facts["positions"] if r["key"] == facts["featured"])
    ingress = date.fromisoformat(facts["ingress"])
    label = lang.labels["transit_today" if ingress == when else "transit"]
    items += _hero(draw, lang, label, facts["featured"],
                   lang.labels["in_sign"].format(**_names(lang, featured)),
                   _span(lang, ingress, date.fromisoformat(facts["egress"])), y)
    y += lang.hero[0] + 24
    if facts.get("rashis"):
        grid, y = _rashi_grid(draw, lang, facts["rashis"], y)
        items += grid
    swipe = lang.labels["swipe"]
    items.append(_text(draw, LEFT, y + 40, swipe,
                       _pick(draw, lang, "note", swipe, TABLE_RIGHT - LEFT, (24, 22)),
                       kit.LABEL, "swipe"))
    _check(items)
    return items + _closing(draw, lang)


def plan_positions(draw: ImageDraw.ImageDraw, facts: dict, when: date,
                   language: str = "en") -> list[Item]:
    """Slide 2: today's Moon and all nine sidereal positions."""
    lang = LANGUAGES[language]
    items, shift = kit.header(draw, lang, lang.labels["transit_title"], when,
                              kit.city_of(lang, facts), HEADER_RIGHT)
    y = FACT_TOP + shift
    moon = next(r for r in facts["positions"] if r["key"] == "moon")
    nakshatra = facts.get("nakshatra") if lang.source == "en" else facts.get("nakshatra_hi", "")
    items += _hero(draw, lang, lang.labels["moon_today"], "moon",
                   lang.labels["in_sign"].format(**_names(lang, moon)),
                   lang.labels["nakshatra_of"].format(name=nakshatra), y)
    y += lang.hero[0] + 24
    items.append(kit.label_item(draw, lang, LEFT, y + 26, lang.labels["positions"],
                                RIGHT - LEFT, "label:positions"))
    y += 40
    items.append(Item("rule", (LEFT, y, RIGHT, y + 2), "rule", fill=kit.DIVIDER))
    items += _table(draw, lang, facts["positions"], max(y + 8, TABLE_FROM))
    _check(items)
    return items + _closing(draw, lang)


SLIDES = (plan_story, plan_positions)


def render_transit(spec: PostSpec, image: Image.Image,
                   language: str = "en") -> list[Image.Image]:
    """Carousel slides in posting order."""
    facts, when = spec.to_dict()["facts"], date.fromisoformat(spec.date)
    return [kit.finish(image.copy(), slide(ImageDraw.Draw(image), facts, when, language),
                       WASH_AREAS) for slide in SLIDES]


__all__ = ["plan_story", "plan_positions", "SLIDES", "render_transit", "wash", "right_edge",
           "_icon_image", "LEFT", "RIGHT", "FACT_BOTTOM"]
