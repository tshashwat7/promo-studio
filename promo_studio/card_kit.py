"""Shared design system for every daily card: type, colour, languages, cells, wash and footer.

Specification: docs/panchang-design-guide.md. Card modules define only their own layout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from graphics.svg_renderer import rasterize

from . import mock_art
from .shaping import ShapedFont, shaped
from .text_layout import draw_tracked, tracked_width

LEFT = 190
ICON, ICON_GAP = 40, 12
BUTTON_BOX_TOP, BUTTON_BOX_BOTTOM = 1250, 1314  # Below the diya base (y ≈ 1243).

MAROON, INK = "#702A32", "#2C2928"
LABEL = "#8A5418"
DIVIDER = "#C19A66"
AUSPICIOUS, INAUSPICIOUS = "#3B5B2A", "#8A2A2A"
BUTTON_TEXT, BUTTON_OUTLINE = "#FFF1D8", "#B18549"
# Parchment card for text placed over busy artwork (alpha 235 keeps a hint of the scene).
PANEL_FILL, PANEL_OUTLINE = (250, 238, 218, 235), (177, 133, 73, 255)
LOGO_RING = "#B18549"
ICON_SOURCE_COLOUR, ICON_COLOUR = "#8A5418", MAROON

# Feathered parchment haze that calms sky texture behind text only.
WASH_COLOUR, WASH_OPACITY, WASH_BLUR = (250, 238, 218), 0.42, 36

FONT_FILES = {
    "lora": "fonts/lora/Lora-Variable.ttf",
    "martel": "fonts/martel/Martel-Bold.ttf",
    "martel-extrabold": "fonts/martel/Martel-ExtraBold.ttf",
    "hind": "fonts/hind/Hind-Regular.ttf",
    "hind-medium": "fonts/hind/Hind-Medium.ttf",
    "hind-semibold": "fonts/hind/Hind-SemiBold.ttf"
}
ICONS = {name: f"icons/panchang/{name}.svg" for name in (
    "tithi", "nakshatra", "yoga", "karana", "sunrise", "sunset",
    "moonrise", "abhijit", "rahu", "yamaganda", "gulika")}
MAX_SVG_BYTES = 64_000
PLANETS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")
MAX_PLANET_BYTES = 200_000
# Spheres fade out their near-white tile; Rahu/Ketu keep only the black glyph, tinted maroon.
PLANET_KEY = {"sphere": (10, 45), "glyph": (90, 160)}
ZODIAC_ART = dict(zip(
    ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
     "Sagittarius", "Capricorn", "Aquarius", "Pisces"),
    ("mesh", "vrishbha", "mithuna", "karka", "simha", "kanya", "tula",
     "vrischika", "dhanu", "makar", "kumbha", "pisces")))
MAX_ZODIAC_BYTES = 200_000

HINDI_MONTHS = ("जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त",
                "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर")
HINDI_WEEKDAYS = ("सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार")
HINDI_CITIES = {"Ujjain": "उज्जैन"}


@dataclass(frozen=True)
class Language:
    code: str
    brand: str
    title: str
    labels: dict[str, str]
    tags: tuple[str, str]
    cta: str
    masa: str  # {masa} {system}
    until: str  # {time}
    on_day: str  # {time} {day} {month}
    note: str  # {city}
    system: str
    shaped: bool
    tracking: int
    faces: dict[str, str]
    values: Callable[[dict], dict[str, str]]
    month: Callable[[date], str]
    month_short: Callable[[date], str]
    weekday: Callable[[date], str]
    city: Callable[[str], str]
    sizes: dict[str, tuple[int, ...]] = field(default_factory=dict)
    hero: tuple[int, int, int] = (116, 82, 112)
    source: str = "en"
    upper: bool = True


ENGLISH = Language(
    code="en", brand="Siddhanta", title="Daily Panchang",
    labels={"tithi": "TITHI", "nakshatra": "NAKSHATRA", "yoga": "YOGA", "karana": "KARANA",
            "sunrise": "SUNRISE", "sunset": "SUNSET", "moonrise": "MOONRISE",
            "abhijit": "ABHIJIT MUHURTA", "rahu": "RAHU KAAL",
            "muhurta_title": "Plan Your Day", "choghadiya": "TODAY'S CHOGHADIYA",
            "panchang_cta": "Check your city's Panchang on Siddhanta",
            "good": "AUSPICIOUS TIMINGS", "avoid": "INAUSPICIOUS TIMINGS",
            "transit_title": "Today's Sky", "transit": "CURRENT TRANSIT",
            "transit_today": "ENTERS TODAY", "moon_today": "MOON TODAY",
            "nakshatra_of": "{name} Nakshatra", "by_moon_sign": "BY MOON SIGN",
            "favourable": "Favourable", "take_care": "Take care",
            "swipe": "Swipe for all nine planet positions ›",
            "positions": "SIDEREAL POSITIONS", "in_sign": "{planet} in {rashi}",
            "transit_hook": "Every Kundli feels this transit differently.",
            "transit_cta": "Add your birth details in Siddhanta for your personal transit "
                           "reading."},
    tags=("Auspicious", "Inauspicious"), cta="Explore in Siddhanta",
    masa="{masa} Masa ({system})", until="Until {time}", on_day="{time}, {day} {month}",
    note="All times for {city} · IST", system="Purnimanta", shaped=False, tracking=2,
    faces={"brand": "lora", "title": "lora", "value": "lora", "button": "lora",
           "label": "hind-semibold", "tag": "hind-semibold",
           "date": "hind-medium", "detail": "hind-medium", "note": "hind-medium"},
    values=lambda f: {k: f[k] for k in ("tithi", "nakshatra", "yoga", "karana", "masa")},
    month=lambda d: f"{d:%B}", month_short=lambda d: f"{d:%b}",
    weekday=lambda d: f"{d:%A}", city=lambda c: c,
    sizes={"brand": (40,), "title": (72,), "hero": (44, 40), "compact": (32, 30),
           "detail": (24, 22)})

HINDI = Language(
    code="hi", brand="सिद्धान्त", title="दैनिक पंचांग",
    labels={"tithi": "तिथि", "nakshatra": "नक्षत्र", "yoga": "योग", "karana": "करण",
            "sunrise": "सूर्योदय", "sunset": "सूर्यास्त", "moonrise": "चंद्रोदय",
            "abhijit": "अभिजित मुहूर्त", "rahu": "राहुकाल",
            "muhurta_title": "आज के मुहूर्त", "choghadiya": "आज का चौघड़िया",
            "panchang_cta": "अपने शहर का पंचांग सिद्धान्त पर देखें",
            "good": "शुभ मुहूर्त", "avoid": "अशुभ काल",
            "transit_title": "आज का गोचर", "transit": "वर्तमान गोचर",
            "transit_today": "आज से गोचर", "moon_today": "आज चंद्रमा",
            "nakshatra_of": "{name} नक्षत्र", "by_moon_sign": "चंद्र राशि अनुसार",
            "favourable": "शुभ फल", "take_care": "सावधानी",
            "swipe": "सभी नौ ग्रहों की स्थिति के लिए स्वाइप करें ›",
            "positions": "निरयण ग्रह स्थिति", "in_sign": "{planet} {rashi} राशि में",
            "transit_hook": "हर कुंडली पर इस गोचर का असर अलग होता है।",
            "transit_cta": "सिद्धान्त में जन्म विवरण डालें और अपना व्यक्तिगत गोचर फल देखें।"},
    tags=("शुभ", "अशुभ"), cta="सिद्धान्त पर देखें",
    masa="{masa} मास ({system})", until="समाप्ति: {time}", on_day="{time}, {day} {month}",
    note="सभी समय {city} के अनुसार · IST", system="पूर्णिमांत", shaped=True, tracking=0,
    faces={"brand": "martel-extrabold", "title": "martel-extrabold", "value": "martel",
           "button": "martel", "label": "hind-semibold", "tag": "hind-semibold",
           "date": "hind-medium", "detail": "hind-medium", "note": "hind-medium"},
    values=lambda f: {"tithi": f"{f.get('paksha_hi', '')} {f.get('tithi_name_hi', '')}".strip() or f.get('tithi_hi', ''),
                      "nakshatra": f.get("nakshatra_hi", ""), "yoga": f.get("yoga_hi", ""),
                      "karana": f.get("karana_hi", ""), "masa": f.get("masa_hi", "")},
    month=lambda d: HINDI_MONTHS[d.month - 1], month_short=lambda d: HINDI_MONTHS[d.month - 1],
    weekday=lambda d: HINDI_WEEKDAYS[d.weekday()], city=lambda c: HINDI_CITIES.get(c, c),
    sizes={"brand": (38,), "title": (64,), "hero": (36, 34), "compact": (30, 28),
           "detail": (22,)},
    hero=(124, 77, 115), source="hi", upper=False)

LANGUAGES = {"en": ENGLISH, "hi": HINDI}


@dataclass
class Item:
    kind: str  # text | icon | planet | zodiac | panel | rule | dot | ring | bar | button
    box: tuple[int, int, int, int]
    role: str = ""
    value: str = ""
    font: Any = None  # ImageFont.FreeTypeFont or ShapedFont
    fill: str = ""
    tracking: int = 0
    origin: tuple[int, int] = (0, 0)  # (x, baseline) for text


def _find_font_path(face: str) -> Path:
    rel = FONT_FILES.get(face, face)
    fonts_dir = mock_art.ROOT / "fonts"
    cands = [
        mock_art.ROOT / rel,
        fonts_dir / Path(rel).name,
    ]
    for c in cands:
        if c.exists() and c.is_file():
            return c

    # Fallbacks strictly within the project's bundled fonts directory
    if face in ("martel", "martel-extrabold"):
        cands_fallback = [
            fonts_dir / "NotoSansDevanagari-Regular.ttf",
            fonts_dir / "LibreBaskerville-Bold.ttf",
            fonts_dir / "DMSans-Bold.ttf",
        ]
    elif face == "lora":
        cands_fallback = [
            fonts_dir / "LibreBaskerville-Bold.ttf",
            fonts_dir / "DMSans-Bold.ttf",
            fonts_dir / "NotoSansDevanagari-Regular.ttf",
        ]
    elif face in ("hind", "hind-medium", "hind-semibold"):
        cands_fallback = [
            fonts_dir / "NotoSansDevanagari-Regular.ttf",
            fonts_dir / "DMSans-SemiBold.ttf",
            fonts_dir / "DMSans-Medium.ttf",
            fonts_dir / "DMSans-Regular.ttf",
        ]
    else:
        cands_fallback = [
            fonts_dir / "DMSans-Regular.ttf",
            fonts_dir / "NotoSansDevanagari-Regular.ttf",
        ]
    for c in cands_fallback:
        if c.exists() and c.is_file():
            return c

    for c in [
        Path(r"C:\Windows\Fonts\Nirmala.ttc"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\georgia.ttf"),
    ]:
        if c.exists():
            return c
    return Path(r"C:\Windows\Fonts\segoeui.ttf")


@lru_cache(maxsize=None)
def _pillow_font(face: str, size: int) -> ImageFont.FreeTypeFont:
    font_path = _find_font_path(face)
    try:
        font = ImageFont.truetype(str(font_path), size)
        if face == "lora":
            try:
                font.set_variation_by_axes([700])
            except Exception:
                pass
        return font
    except Exception:
        return ImageFont.load_default()


def font_for(lang: Language, role: str, size: int):
    face = lang.faces[role]
    font_path = _find_font_path(face)
    if lang.shaped:
        try:
            return shaped(str(font_path), size)
        except Exception:
            return _pillow_font(face, size)
    return _pillow_font(face, size)


@lru_cache(maxsize=None)
def _icon_image(name: str, size: int) -> Image.Image:
    candidates = [
        mock_art.ROOT / ICONS.get(name, f"icons/panchang/{name}.svg"),
        mock_art.ROOT / "icons" / f"{name}.svg",
        mock_art.ROOT / "icons" / "panchang" / f"{name}.svg",
        Path(__file__).resolve().parent / "assets" / "icons" / "panchang" / f"{name}.svg",
    ]
    for path in candidates:
        if path.is_file():
            markup = path.read_text(encoding="utf-8").replace(ICON_SOURCE_COLOUR, ICON_COLOUR)
            return rasterize(markup, size)
    # Rasterized fallback
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), outline=MAROON, width=2)
    return img


@lru_cache(maxsize=None)
def planet_image(name: str, width: int, height: int) -> Image.Image:
    if name not in PLANETS:
        raise ValueError(f"no curated art for planet {name!r}")
    cands = [
        mock_art.ROOT / "icons" / "planets" / f"{name}.webp",
        mock_art.ROOT / "icons" / "planets" / f"{name}.png",
        Path(__file__).resolve().parent / "assets" / "icons" / "planets" / f"{name}.webp",
        Path(r"D:\AI My Projects\Production\panchang_master_app\assets\illustrations\planets") / f"{name}.webp",
    ]
    for p in cands:
        if p.is_file():
            try:
                source = Image.open(p).convert("RGB")
                distance = ImageChops.difference(source, Image.new("RGB", source.size, source.getpixel((0, 0))))
                distance = ImageChops.lighter(ImageChops.lighter(*distance.split()[:2]), distance.split()[2])
                glyph = name in ("rahu", "ketu")
                low, high = PLANET_KEY["glyph" if glyph else "sphere"]
                alpha = distance.point(lambda v: 0 if v <= low else 255 if v >= high
                                       else round((v - low) * 255 / (high - low)))
                art = Image.new("RGB", source.size, ICON_COLOUR) if glyph else source
                art = art.convert("RGBA")
                art.putalpha(alpha)
                box = alpha.getbbox()
                if box:
                    art = art.crop(box)
                art = ImageOps.contain(art, (width, height), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (width, height))
                canvas.paste(art, ((width - art.width) // 2, (height - art.height) // 2), art)
                return canvas
            except Exception:
                pass
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).ellipse((2, 2, width - 2, height - 2), fill=LABEL)
    return canvas


@lru_cache(maxsize=None)
def zodiac_image(name: str, size: int) -> Image.Image:
    if name not in ZODIAC_ART:
        raise ValueError(f"no curated zodiac art for {name!r}")
    cands = [
        mock_art.ROOT / "icons" / "festivals" / f"{ZODIAC_ART[name]}.webp",
        mock_art.ROOT / "icons" / "festivals" / f"{ZODIAC_ART[name]}.png",
        Path(__file__).resolve().parent / "assets" / "icons" / "festivals" / f"{ZODIAC_ART[name]}.webp",
        Path(r"D:\AI My Projects\Production\panchang_master_app\assets\illustrations\festivals") / f"{ZODIAC_ART[name]}.webp",
    ]
    for path in cands:
        if path.is_file():
            try:
                with Image.open(path) as source:
                    art = source.convert("RGBA")
                scale = 4
                mask = Image.new("L", (art.width * scale, art.height * scale), 0)
                ImageDraw.Draw(mask).ellipse((scale, scale, art.width * scale - scale - 1,
                                             art.height * scale - scale - 1), fill=255)
                mask = mask.resize(art.size, Image.Resampling.LANCZOS)
                art.putalpha(ImageChops.multiply(art.getchannel("A"), mask))
                return art.resize((size, size), Image.Resampling.LANCZOS)
            except Exception:
                pass
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).ellipse((2, 2, size - 2, size - 2), outline=LABEL, width=2)
    return canvas


def _length(draw: ImageDraw.ImageDraw, value: str, font, tracking: int = 0) -> float:
    if isinstance(font, ShapedFont):
        return font.getlength(value)
    return tracked_width(draw, value, font, tracking) if tracking else draw.textlength(value, font=font)


def _pick(draw, lang: Language, role: str, value: str, width: int, sizes: tuple[int, ...],
          tracking: int = 0):
    """Use the first approved size that fits; refuse rather than shrink further."""
    for size in sizes:
        font = font_for(lang, role, size)
        if _length(draw, value, font, tracking) <= width:
            return font
    raise ValueError(f"{value!r} does not fit {width}px at approved sizes {sizes}")


def _text(draw, x: int, baseline: int, value: str, font, fill: str, role: str,
          tracking: int = 0) -> Item:
    if isinstance(font, ShapedFont):
        x += x - font.bbox(x, baseline, value)[0]
        box = font.bbox(x, baseline, value)
    else:
        box = draw.textbbox((x, baseline), value, font=font, anchor="ls")
        if tracking:
            box = (box[0], box[1], x + tracked_width(draw, value, font, tracking), box[3])
    return Item("text", box, role, value, font, fill, tracking, (x, baseline))


def wrap(draw, value: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in value.split():
        trial = f"{line} {word}".strip()
        if line and _length(draw, trial, font) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines or [value]


def label_item(draw, lang: Language, x: int, baseline: int, value: str, width: int,
               role: str) -> Item:
    return _text(draw, x, baseline, value,
                 _pick(draw, lang, "label", value, width, (26, 24), lang.tracking),
                 LABEL, role, lang.tracking)


def _cell(draw, lang: Language, key: str, value: str, x: int, width: int, y: int, *,
          hero: bool = False, detail: str | None = None,
          auspicious: bool | None = None, label: str | None = None) -> list[Item]:
    label = label or lang.labels.get(key, key.upper())
    label_x = x + ICON + ICON_GAP
    items = [Item("icon", (x, y, x + ICON, y + ICON), f"icon:{key}", key),
             label_item(draw, lang, label_x, y + 29, label, width - ICON - ICON_GAP,
                        f"label:{key}")]
    _, hero_value, hero_detail = lang.hero
    sizes, baseline = ((lang.sizes.get("hero", (44, 40)), y + hero_value) if hero
                       else (lang.sizes.get("compact", (32, 30)), y + 74))
    items.append(_text(draw, x, baseline, value, _pick(draw, lang, "value", value, width, sizes),
                       MAROON, f"value:{key}"))
    if detail:
        items.append(_text(draw, x, y + hero_detail, detail,
                           _pick(draw, lang, "detail", detail, width, lang.sizes.get("detail", (24, 22))),
                           INK, f"detail:{key}"))
    if auspicious is not None:
        colour = AUSPICIOUS if auspicious else INAUSPICIOUS
        items.append(Item("dot" if auspicious else "ring", (x, y + 90, x + 14, y + 104),
                          f"dot:{key}", fill=colour))
        items.append(_text(draw, x + 22, y + 104, lang.tags[0 if auspicious else 1],
                           font_for(lang, "tag", 22), colour, f"tag:{key}"))
    return items


def header(draw, lang: Language, title: str, when: date, city: str,
           right: int) -> tuple[list[Item], int]:
    items = [_text(draw, LEFT, 110, lang.brand, font_for(lang, "brand", lang.sizes.get("brand", (40,))[0]),
                   MAROON, "brand"),
             _text(draw, LEFT, 216, title, font_for(lang, "title", lang.sizes.get("title", (72,))[0]),
                   MAROON, "title")]
    date_text = f"{lang.weekday(when)}, {when.day} {lang.month(when)} {when.year}"
    line = f"{date_text} · {city}" if city else date_text
    width = right - LEFT
    for drop in range(0, 41, 2):
        if _length(draw, line, font_for(lang, "date", 30)) <= width:
            dated = [_text(draw, LEFT, 270 + drop, line, font_for(lang, "date", 30), INK, "date")]
            extra = drop
        else:
            dated = [_text(draw, LEFT, 264 + drop, date_text,
                           _pick(draw, lang, "date", date_text, width, (30,)), INK, "date"),
                     _text(draw, LEFT, 296 + drop, city,
                           _pick(draw, lang, "date", city, width, (26,)), INK, "place")]
            extra = 30 + drop
        if dated[0].box[1] >= items[1].box[3] + 8:
            return items + dated, extra
    raise ValueError("Title descenders leave no room for the date line")


def city_of(lang: Language, facts: dict) -> str:
    source_city = str(facts.get("location", "")).split(",", 1)[0].strip()
    return lang.city(source_city) if source_city else ""


def button(draw, lang: Language, text: str | None = None) -> Item:
    text = text or lang.cta
    font = font_for(lang, "button", 28)
    width = round(_length(draw, text, font)) + 64
    return Item("button", (LEFT, BUTTON_BOX_TOP, LEFT + width, BUTTON_BOX_BOTTOM),
                "button", text, font, BUTTON_TEXT)


def wash(image: Image.Image, areas: tuple[tuple[int, int, int, int], ...]) -> Image.Image:
    if not areas:
        return image
    mask = Image.new("L", image.size, 0)
    shapes = ImageDraw.Draw(mask)
    for box in areas:
        shapes.rectangle(box, fill=round(255 * WASH_OPACITY))
    mask = mask.filter(ImageFilter.GaussianBlur(WASH_BLUR))
    return Image.composite(Image.new("RGB", image.size, WASH_COLOUR), image, mask)


def _logo_medallion(size: int) -> tuple[Image.Image, Image.Image]:
    source = mock_art._open(mock_art.LOGO)
    side = min(source.size)
    inset = round(side * 0.03)
    square = ImageOps.fit(source, (side, side)).crop((inset, inset, side - inset, side - inset))
    emblem = square.resize((size, size), Image.Resampling.LANCZOS)
    scale = 4
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
    return emblem, mask.resize((size, size), Image.Resampling.LANCZOS)


def _draw_text(image: Image.Image, draw: ImageDraw.ImageDraw, item: Item) -> None:
    if isinstance(item.font, ShapedFont):
        item.font.draw(image, item.origin, item.value, item.fill)
    elif item.tracking:
        draw_tracked(draw, item.origin, item.value, item.font, item.fill, item.tracking)
    else:
        draw.text(item.origin, item.value, font=item.font, fill=item.fill, anchor="ls")


def draw_items(image: Image.Image, items: list[Item]) -> Image.Image:
    draw = ImageDraw.Draw(image)
    for item in items:
        if item.kind == "text":
            _draw_text(image, draw, item)
        elif item.kind == "icon":
            icon = _icon_image(item.value, item.box[2] - item.box[0])
            image.paste(icon, item.box[:2], icon)
        elif item.kind == "planet":
            art = planet_image(item.value, item.box[2] - item.box[0], item.box[3] - item.box[1])
            image.paste(art, item.box[:2], art)
        elif item.kind == "zodiac":
            art = zodiac_image(item.value, item.box[2] - item.box[0])
            image.paste(art, item.box[:2], art)
        elif item.kind == "panel":
            layer = Image.new("RGBA", image.size)
            ImageDraw.Draw(layer).rounded_rectangle(item.box, radius=24, fill=PANEL_FILL,
                                                    outline=PANEL_OUTLINE, width=2)
            image.paste(Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB"))
            draw = ImageDraw.Draw(image)
        elif item.kind in ("rule", "bar"):
            draw.rectangle(item.box, fill=item.fill)
        elif item.kind == "dot":
            draw.ellipse(item.box, fill=item.fill)
        elif item.kind == "ring":
            draw.ellipse(item.box, outline=item.fill, width=3)
        elif item.kind == "button":
            left, top, right, bottom = item.box
            draw.rounded_rectangle(item.box, radius=(bottom - top) // 2, fill=MAROON,
                                   outline=BUTTON_OUTLINE, width=2)
            if not isinstance(item.font, ShapedFont):
                draw.text((left + 32, (top + bottom) // 2), item.value, font=item.font,
                          fill=item.fill, anchor="lm")
                continue
            ink = item.font.bbox(0, 0, item.value)
            baseline = (top + bottom) // 2 - (ink[1] + ink[3]) // 2
            item.font.draw(image, (left + 32, baseline), item.value, item.fill)
    return image


def finish(image: Image.Image, items: list[Item],
           wash_areas: tuple[tuple[int, int, int, int], ...]) -> Image.Image:
    """Wash, logo medallion, then every planned item."""
    image = wash(image, wash_areas)
    if (mock_art.ROOT / mock_art.LOGO).is_file() or mock_art._resolve_path(mock_art.LOGO).is_file():
        emblem, mask = _logo_medallion(88)
        image.paste(emblem, (84, 52), mask)
        ImageDraw.Draw(image).ellipse((83, 51, 172, 140), outline=LOGO_RING, width=2)
    return draw_items(image, items)
