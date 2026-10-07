"""Bilingual, explicitly illustrative Chakra promotion (no personal reading or score)."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from graphics.ornament_engine import ornament

from . import card_kit as kit
from .card_kit import Item, _pick, _text

COPY = {
    "en": {"title": ("Balance Your", "Inner Energy"), "subtitle": "Explore the seven chakras",
           "names": ("Crown", "Third Eye", "Throat", "Heart", "Solar Plexus", "Sacral", "Root"),
           "disclaimer": "Illustrative guide · not a personal assessment",
           "button": "Explore in Siddhanta"},
    "hi": {"title": ("अपनी आंतरिक ऊर्जा", "को संतुलित करें"), "subtitle": "सात चक्रों को जानें",
           "names": ("सहस्रार", "आज्ञा", "विशुद्ध", "अनाहत", "मणिपूर", "स्वाधिष्ठान", "मूलाधार"),
           "disclaimer": "केवल चित्रण · यह व्यक्तिगत आकलन नहीं है",
           "button": "सिद्धान्त पर देखें"},
}
COLOURS = ("#A25ACC", "#6567CE", "#43AFC5", "#4DAC78", "#E4BE3F", "#EC8D3E", "#CE5156")
CHAKRA_Y = tuple(543 + i * 76 for i in range(7))
NAME_X = 762


def plan(draw: ImageDraw.ImageDraw, language: str = "en") -> list[Item]:
    lang, text = kit.LANGUAGES[language], COPY[language]
    title_step = 76 if language == "en" else 84
    items = [_text(draw, kit.LEFT, 110, lang.brand,
                   kit.font_for(lang, "brand", lang.sizes["brand"][0]), kit.MAROON, "brand")]
    for i, line in enumerate(text["title"]):
        items.append(_text(draw, kit.LEFT, 216 + i * title_step, line,
                           _pick(draw, lang, "title", line, 800, lang.sizes["title"]),
                           kit.MAROON, f"title:{i}"))
    items.append(_text(draw, kit.LEFT, 216 + len(text["title"]) * title_step - 10,
                       text["subtitle"],
                       _pick(draw, lang, "date", text["subtitle"], 800, (30, 28)),
                       kit.INK, "subtitle"))
    for i, (name, y) in enumerate(zip(text["names"], CHAKRA_Y)):
        items.append(_text(draw, NAME_X, y + 10, name,
                           _pick(draw, lang, "value", name, 1040 - NAME_X, (30, 28)),
                           kit.MAROON, f"chakra:{i}"))
    items.append(_text(draw, 120, 1203, text["disclaimer"],
                       _pick(draw, lang, "detail", text["disclaimer"], 840, (24, 22)),
                       kit.MAROON, "disclaimer"))
    items.append(kit.button(draw, lang, text["button"]))
    return items


def _figure(image: Image.Image) -> Image.Image:
    """Decorative meditating silhouette with seven glowing centres."""
    halo = ornament("mandala", 710).copy()
    halo.putalpha(halo.getchannel("A").point(lambda a: a // 3))
    image.paste(halo, (35, 416), halo)
    draw, dark = ImageDraw.Draw(image), "#273046"
    draw.ellipse((225, 1020, 640, 1145), fill=dark)
    draw.polygon([(352, 667), (468, 667), (561, 1060), (259, 1060)], fill=dark)
    draw.ellipse((315, 467, 505, 681), fill=dark)
    draw.line([(341, 757), (242, 941), (186, 1008)], fill=dark, width=38, joint="curve")
    draw.line([(479, 757), (578, 941), (633, 1008)], fill=dark, width=38, joint="curve")
    draw.ellipse((78, 995, 406, 1128), fill=dark)
    draw.ellipse((414, 995, 740, 1128), fill=dark)
    light = Image.new("RGBA", image.size)
    glow = ImageDraw.Draw(light)
    for y, colour in zip(CHAKRA_Y, COLOURS):
        glow.ellipse((361, y - 49, 459, y + 49), fill=colour)
    light = light.filter(ImageFilter.GaussianBlur(27))
    image = Image.alpha_composite(image.convert("RGBA"), light).convert("RGB")
    draw = ImageDraw.Draw(image)
    for y, colour in zip(CHAKRA_Y, COLOURS):
        draw.ellipse((381, y - 28, 439, y + 30), fill=colour, outline="#FFF0CF", width=4)
        draw.ellipse((400, y - 9, 420, y + 11), fill="#FFFAE9")
        draw.line((466, y, NAME_X - 24, y), fill="#B99163", width=2)
    return image


def render_chakra(image: Image.Image, language: str = "en") -> Image.Image:
    items = plan(ImageDraw.Draw(image), language)
    return kit.finish(_figure(image), items, ())
