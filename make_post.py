"""Render a daily Panchang Instagram image from data.json and muhu.json."""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import freetype
    import uharfbuzz as hb
except ImportError:
    freetype = None
    hb = None
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SIZE = (1080, 1350)
INK = "#142B32"
CREAM = "#FFF3DF"
MUTED = "#9CB5B1"
GOLD = "#F3C881"
ORANGE = "#D37B50"


def find_font(candidates: list[str], override: Path | None = None) -> Path:
    if override is not None:
        if not override.is_file():
            raise FileNotFoundError(f"Font not found: {override}")
        return override
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path
    # Look for bundled fonts if system fonts are not found
    bundled = [
        ROOT / "assets" / "fonts" / "Hind-Medium.ttf",
        ROOT / "assets" / "fonts" / "Hind-Regular.ttf",
        ROOT / "assets" / "fonts" / "Lora-Regular.ttf",
        ROOT / "assets" / "fonts" / "hind" / "Hind-Medium.ttf",
        ROOT / "assets" / "fonts" / "hind" / "Hind-Regular.ttf",
        ROOT / "assets" / "fonts" / "lora" / "Lora-Variable.ttf",
    ]
    for b in bundled:
        if b.is_file():
            return b
    raise FileNotFoundError("No suitable font found; use --hindi-font to supply a Devanagari font")


class HindiText:
    """Shape Devanagari text, then paint FreeType's glyph masks onto Pillow."""

    def __init__(self, font_path: Path):
        self.font_path = font_path
        if freetype is not None and hb is not None:
            self.face = freetype.Face(str(font_path))
            self.hb_face = hb.Face(font_path.read_bytes())
            self.font = hb.Font(self.hb_face)
            hb.ot_font_set_funcs(self.font)
            self._has_hb = True
        else:
            self._has_hb = False

    def draw(self, image: Image.Image, x: int, baseline: int, text: str,
             size: int, color: str) -> int:
        if not self._has_hb:
            font = ImageFont.truetype(str(self.font_path), size)
            draw = ImageDraw.Draw(image)
            draw.text((x, baseline), text, font=font, fill=color, anchor="ls")
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0]
        self.face.set_pixel_sizes(0, size)
        self.font.scale = (self.face.size.x_ppem * 64, self.face.size.y_ppem * 64)
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.font, buffer)
        pen_x = 0
        pen_y = 0
        for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions):
            self.face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
            glyph = self.face.glyph
            bitmap = glyph.bitmap
            if bitmap.width and bitmap.rows:
                mask = Image.frombytes("L", (bitmap.width, bitmap.rows), bytes(bitmap.buffer))
                tile = Image.new("RGB", mask.size, color)
                image.paste(tile, (round(x + (pen_x + pos.x_offset) / 64 + glyph.bitmap_left),
                                   round(baseline - (pen_y + pos.y_offset) / 64 - glyph.bitmap_top)), mask)
            pen_x += pos.x_advance
            pen_y += pos.y_advance
        return round(pen_x / 64)


def background() -> Image.Image:
    image = Image.new("RGB", SIZE)
    pixels = image.load()
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        for x in range(SIZE[0]):
            glow = max(0, 1 - math.hypot((x - 840) / 1020, (y - 160) / 780)) * 0.42
            pixels[x, y] = (round(13 + 14 * glow + 5 * t),
                            round(35 + 13 * glow + 5 * t),
                            round(43 + 12 * glow + 2 * t))
    d = ImageDraw.Draw(image)
    rng = random.Random(42)
    for _ in range(70):
        x, y = rng.randrange(30, 1050), rng.randrange(30, 1290)
        r = rng.choice((1, 1, 1, 2))
        d.ellipse((x-r, y-r, x+r, y+r), fill="#51615D")
    for radius in (230, 268, 306):
        d.arc((805-radius, 167-radius, 805+radius, 167+radius), 20, 160,
              fill="#385451", width=2)
    return image


def render(data: dict, muhu: dict, hindi_font: Path) -> Image.Image:
    image = background()
    d = ImageDraw.Draw(image)
    hi = HindiText(hindi_font)
    regular_path = find_font([r"C:\Windows\Fonts\segoeui.ttf",
                              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    bold_path = find_font([r"C:\Windows\Fonts\segoeuib.ttf",
                           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])

    def latin(text: str, x: int, y: int, size: int = 25,
              color: str = CREAM, bold: bool = False) -> None:
        font = ImageFont.truetype(str(bold_path if bold else regular_path), size)
        d.text((x, y), text, font=font, fill=color)

    def rule(x1: int, y: int, x2: int, fill: str = "#D8D4C6") -> None:
        d.line((x1, y, x2, y), fill=fill, width=2)

    def panel(box: tuple[int, int, int, int], fill: str, outline: str | None = None) -> None:
        d.rounded_rectangle(box, radius=34, fill=fill, outline=outline, width=2)

    record = data["today"]
    h = record["hindi"]
    e = record["english"]
    event_date = date.fromisoformat(record["date"])
    auspicious = muhu["muhurtas"]

    # Masthead and date.
    d.ellipse((64, 70, 106, 112), outline=GOLD, width=3)
    d.arc((74, 80, 96, 102), 0, 180, fill=GOLD, width=3)
    latin("SIDDHANTA", 121, 66, 32, GOLD, True)
    latin("VEDIC PANCHANG  /  UJJAIN", 122, 106, 18, MUTED)
    panel((807, 72, 1016, 125), "#304947")
    latin(event_date.strftime("%d  %b  %Y").upper(), 836, 83, 22, CREAM, True)

    hi.draw(image, 65, 225, "आज का पंचांग", 76, CREAM)
    latin(event_date.strftime("%A  •  %d %B %Y").upper(), 69, 263, 25, GOLD, True)

    # Main tithi feature.
    panel((55, 324, 1025, 618), CREAM)
    latin("TODAY'S TITHI", 91, 355, 22, "#98613E", True)
    hi.draw(image, 91, 445, h["tithi"], 47, INK)
    rule(91, 478, 665, "#DED1BC")
    latin("NAKSHATRA", 91, 503, 19, "#8B7565", True)
    hi.draw(image, 91, 575, h["nakshatra"], 37, INK)
    latin("until " + e["nakshatra_end"], 239, 537, 21, "#6C6860")
    # Etched sunrise ornament (no external assets).
    d.ellipse((747, 364, 967, 584), outline="#DFB77F", width=2)
    d.ellipse((778, 395, 936, 553), outline="#E7C89B", width=2)
    d.ellipse((819, 436, 895, 512), fill=GOLD)
    d.line((785, 515, 929, 515), fill="#B88057", width=3)
    for deg in range(0, 360, 30):
        angle = math.radians(deg)
        cx, cy = 857, 474
        d.line((cx + math.cos(angle)*92, cy + math.sin(angle)*92,
                cx + math.cos(angle)*101, cy + math.sin(angle)*101),
               fill="#D6A96F", width=2)

    # Two short glanceable detail cards.
    panel((55, 643, 525, 899), "#24413F", "#40605A")
    panel((550, 643, 1025, 899), "#24413F", "#40605A")
    latin("PANCHANG DETAILS", 85, 667, 21, GOLD, True)
    rule(85, 710, 495, "#49605B")
    latin("YOGA", 85, 732, 17, MUTED, True)
    hi.draw(image, 276, 763, h["yoga"], 30, CREAM)
    latin("KARANA", 85, 783, 17, MUTED, True)
    hi.draw(image, 276, 815, h["karana"], 30, CREAM)
    latin("MOON SIGN", 85, 835, 17, MUTED, True)
    hi.draw(image, 276, 867, h["chandra_rashi"], 30, CREAM)

    latin("SUN & MOON", 581, 667, 21, GOLD, True)
    rule(581, 710, 995, "#49605B")
    latin("SUNRISE", 581, 732, 17, MUTED, True)
    latin(e["sunrise"], 775, 726, 26, CREAM, True)
    latin("SUNSET", 581, 783, 17, MUTED, True)
    latin(e["sunset"], 775, 777, 26, CREAM, True)
    latin("MOONRISE", 581, 835, 17, MUTED, True)
    latin(e["moonrise"], 775, 829, 26, CREAM, True)

    # Muhurta timings from the second JSON file.
    panel((55, 925, 1025, 1238), "#F1E4CE")
    latin("MUHURTA  /  TODAY'S WINDOWS", 90, 948, 21, "#865F46", True)
    d.line((540, 1010, 540, 1205), fill="#D8C7AB", width=2)
    latin("AUSPICIOUS", 90, 1008, 21, "#366B60", True)
    latin("AVOID", 576, 1008, 21, "#B5694B", True)

    def timing(key: str, label: str, x: int, y: int, color: str) -> None:
        entry = auspicious[key]
        d.ellipse((x, y+10, x+9, y+19), fill=color)
        latin(label, x+21, y, 21, INK, True)
        latin(f"{entry['start']} – {entry['end']}", x+21, y+32, 19, "#655F56")

    timing("brahma_muhurta", "Brahma Muhurta", 91, 1051, "#47917C")
    timing("abhijit_muhurta", "Abhijit Muhurta", 91, 1132, "#47917C")
    timing("rahu_kaal", "Rahu Kaal", 578, 1051, ORANGE)
    timing("yamaghanta", "Yamaganda", 578, 1132, ORANGE)

    latin("SIDDHANTA  •  DAILY VEDIC PANCHANG", 62, 1281, 20, GOLD, True)
    latin("Times in IST  |  Ujjain, India", 732, 1282, 19, MUTED)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data.json")
    parser.add_argument("--muhurta", type=Path, default=ROOT / "muhu.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--date", help="Render this YYYY-MM-DD date instead of today in the location's timezone")
    parser.add_argument("--hindi-font", type=Path, help="Devanagari TTF or TTC font path")
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    muhu = json.loads(args.muhurta.read_text(encoding="utf-8"))
    timezone = data["metadata"]["location"]["timezone"]
    expected = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo(timezone)).date()
    actual = date.fromisoformat(data["today"]["date"])
    muhu_date = date.fromisoformat(muhu["date"])
    if actual != expected or muhu_date != expected:
        parser.error(f"Requested {expected}, but data.json is for {actual} and muhu.json is for {muhu_date}. "
                     "Update the inputs, or choose a matching --date for an archive post.")

    font = find_font([r"C:\Windows\Fonts\Nirmala.ttc",
                      "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"],
                     args.hindi_font)
    image = render(data, muhu, font)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    png = args.output_dir / f"panchang-{expected}.png"
    caption = args.output_dir / f"caption-{expected}.txt"
    image.save(png, optimize=True)
    caption.write_text(data["today"]["hindi"]["ready_caption"] + "\n", encoding="utf-8")
    print(f"Image: {png}\nCaption: {caption}")


if __name__ == "__main__":
    main()
