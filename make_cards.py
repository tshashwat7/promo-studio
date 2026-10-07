"""Create six original Instagram cards inspired by the supplied layouts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from graphics.artwork import festival_artwork
from graphics.effects import glow
from graphics.renderer import Canvas
from make_post import ROOT, find_font

W, H = 1080, 1350
PAPER = "#FFF1D8"
WINE = "#82272A"
GOLD = "#C58A42"
INK = "#382B29"
MUTED = "#826F63"
NAVY = "#102638"


def sun(d: ImageDraw.ImageDraw, x: int, y: int, radius: int = 90,
        color: str = "#E4A64C") -> None:
    for i in range(16):
        a = i * math.tau / 16
        d.line((x + (radius+15)*math.cos(a), y + (radius+15)*math.sin(a),
                x + (radius+42)*math.cos(a), y + (radius+42)*math.sin(a)), fill=color, width=4)
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)


def card_panchang(data: dict, muhu: dict, font: Path) -> Image.Image:
    c = Canvas(font, "panchang")
    d = c.draw
    t = data["today"]
    e, h = t["english"], t["hindi"]
    glow(c.image, (868, 400), 210)
    c.motif("moon", 681, 211, 375)
    c.text("Today's", 75, 209, 90, PAPER, True)
    c.text("Panchang", 75, 297, 88, "#F1C48B", True)
    c.text(date.fromisoformat(t["date"]).strftime("%d %B %Y").upper(), 79, 408, 31, PAPER, sans=True)
    c.text(f"{t['day_of_week_en'].upper()}  /  {e['paksha'].upper()} PAKSHA", 79, 449, 23, "#E2C39C", sans=True)
    c.panel((68, 561, 1012, 939), fill="#F9EBD2", outline="#DCB989", radius=29)
    c.motif("mandala", 760, 560, 250, opacity=.13)
    for y, number, label, value, ending in (
        (595, "01", "TITHI", h["tithi_name"], e["tithi_end"]),
        (752, "02", "NAKSHATRA", h["nakshatra"], e["nakshatra_end"]),
    ):
        d.ellipse((100, y+13, 183, y+96), fill="#F1D2A7")
        c.text(number, 118, y+37, 29, WINE, True)
        c.text(label, 215, y+9, 24, WINE, True)
        c.hi(value, 215, y+91, 46, INK)
        c.text("Ends " + ending, 214, y+103, 23, MUTED, sans=True)
    d.line((214, 744, 952, 744), fill="#DDC4A1", width=2)
    c.motif("temple", 676, 930, 288)
    sun(d, 147, 1082, 27)
    c.text(f"SUNRISE   {e['sunrise']}", 250, 1017, 27, PAPER, sans=True)
    c.text(f"SUNSET     {e['sunset']}", 250, 1061, 27, PAPER, sans=True)
    c.flourish(160, 1155, .85)
    c.footer(data["metadata"]["location"]["name"].split(",", 1)[0] + "  |  Times in IST")
    return c.image


def card_plan(data: dict, muhu: dict, font: Path) -> Image.Image:
    c = Canvas(font, "plan")
    d = c.draw
    c.motif("zodiac", 717, 194, 315, opacity=.40)
    c.text("Plan Your", 87, 212, 86, WINE, True)
    c.text("Day Wisely", 87, 300, 86, WINE, True)
    c.text("Auspicious timings for a more harmonious day.", 91, 409, 30, MUTED)
    c.flourish(92, 466, .8)
    entries = [
        ("abhijit_muhurta", "Abhijit Muhurta", "#285940", "An auspicious mid-day window."),
        ("rahu_kaal", "Rahu Kaal", WINE, "Traditionally avoided for new starts."),
    ]
    good = [s for s in muhu["choghadiya"]["day"] if s["is_auspicious"]]
    if good:
        slot = good[0]
        entries.append((None, f"Choghadiya ({slot['name_en']})", "#9E651E", "An auspicious daytime window."))
    for i, (key, label, color, description) in enumerate(entries):
        y = 505 + 215*i
        c.panel((79, y, 1001, y+190), fill="#FFF4E2", outline="#D8B989", radius=25)
        d.ellipse((103, y+49, 196, y+142), fill=color, outline="#DAA85B", width=3)
        c.motif(("lotus", "moon", "diya")[i], 114, y+62, 70, opacity=.92)
        c.text(label, 224, y+24, 42, color, True)
        entry = muhu["muhurtas"][key] if key else slot
        c.text(f"{entry['start']} – {entry['end']}", 226, y+79, 30, INK, sans=True)
        c.text(description, 227, y+132, 25, MUTED)
    c.motif("mandala", 86, 1072, 140, opacity=.23)
    c.flourish(376, 1155, 1.15)
    c.footer("Explore daily windows in Siddhanta")
    return c.image


def card_festival(data: dict, muhu: dict, font: Path, featured: dict | None = None) -> Image.Image:
    c = Canvas(font, "festival")
    d = c.draw
    today = date.fromisoformat(data["today"]["date"])
    festivals = [f for f in data.get("upcoming_festivals", []) if date.fromisoformat(f["date"]) >= today]
    if not festivals and featured is None:
        raise ValueError("No upcoming festival in data.json; cannot generate the festival card")
    festival = featured if featured is not None else next((f for f in festivals if f["category"] == "major"), festivals[0])
    when = date.fromisoformat(festival["date"])
    days = (when - today).days
    title = festival["name_en"].replace(" (Start)", " Begins")
    c.text("FESTIVAL TODAY" if featured is not None else "UPCOMING FESTIVAL", 86, 213, 27, GOLD, True, True)
    c.text(title, 83, 277, 67 if len(title) < 24 else 52, WINE, True, max_width=906)
    c.text(when.strftime("%d %B %Y").upper(), 87, 362, 32, INK, True, True)
    c.hi(festival["name_hi"], 88, 445, 38, MUTED)
    c.panel((78, 494, 1004, 1170), fill="#F9E6C8", outline="#DBB584", radius=38)
    art = festival_artwork(festival, ROOT, (530, 550))
    if art is None:
        c.motif("lotus", 444, 568, 540, opacity=.95)
        c.motif("diya", 652, 702, 205)
    else:
        c.motif("mandala", 445, 583, 540, opacity=.26)
        c.image.alpha_composite(art, dest=(456 + (530-art.width)//2,
                                           560 + (550-art.height)//2))
    c.text("A MOMENT TO CELEBRATE", 117, 557, 24, WINE, True, True)
    c.text("Tradition", 116, 633, 53, INK, True)
    c.text("& devotion", 116, 693, 53, INK, True)
    c.text("A special day is", 116, 826, 27, MUTED)
    c.text("on the horizon.", 116, 864, 27, MUTED)
    d.rounded_rectangle((112, 1004, 375, 1091), radius=20, fill=WINE)
    c.text("Today" if days == 0 else f"In {days} day{'s' if days != 1 else ''}", 137, 1021, 40, PAPER, True)
    c.footer("Explore more festivals with Siddhanta", cta=True)
    return c.image


def card_kundli(data: dict, muhu: dict, font: Path) -> Image.Image:
    """Static service promotion. Diagram is decorative, never a person's chart."""
    c = Canvas(font, "kundli")
    d = c.draw
    c.centered("Your Kundli", 213, 89, WINE, True)
    c.centered("A deeper understanding of your unique journey.", 319, 28, MUTED)
    c.panel((90, 395, 990, 1055), fill="#FFF1D7", outline="#C49659", radius=20)
    c.motif("mandala", 191, 415, 700, opacity=.20)
    c.motif("kundli", 193, 408, 693)
    d.ellipse((460, 655, 620, 807), fill="#F5DFC0", outline="#BD945B", width=3)
    c.centered("YOUR", 670, 24, WINE, True)
    c.centered("STORY", 711, 27, WINE, True)
    c.centered("A personal chart begins with your birth details.", 1085, 28, MUTED)
    c.footer("Create your personal Kundli", cta=True)
    return c.image


def card_chakra(data: dict, muhu: dict, font: Path) -> Image.Image:
    """Static wellness promotion. No fabricated balance score."""
    c = Canvas(font, "chakra")
    d = c.draw
    c.centered("Balance Your", 214, 78, PAPER, True)
    c.centered("Inner Energy", 294, 78, "#F1C18A", True)
    c.centered("Explore the seven chakras", 397, 29, PAPER)
    c.centered("A moment to reconnect with yourself.", 436, 27, "#C6B7A4")
    c.motif("mandala", 214, 477, 700, opacity=.27)
    # A stylized meditating silhouette behind the seven decorative energy centers.
    d.ellipse((426, 512, 654, 740), fill="#142033", outline="#8C684E", width=2)
    d.polygon([(462, 714), (617, 714), (722, 1065), (356, 1065)], fill="#142033")
    d.ellipse((283, 1003, 797, 1136), fill="#142033", outline="#876744", width=3)
    cx = 540
    colors = ["#8955B3", "#536AC3", "#37A2AA", "#41A66C", "#E2BD3D", "#E78A42", "#CE5559"]
    names = ["Crown", "Third Eye", "Throat", "Heart", "Solar Plexus", "Sacral", "Root"]
    for i, (color, name) in enumerate(zip(colors, names)):
        y = 578 + i*79
        glow(c.image, (cx, y), 34, tuple(bytes.fromhex(color.lstrip("#"))))
        for petal in range(8):
            a = petal*math.tau/8
            px, py = cx+29*math.cos(a), y+29*math.sin(a)
            d.ellipse((px-18, py-18, px+18, py+18), fill=color)
        d.ellipse((cx-24, y-24, cx+24, y+24), fill=PAPER)
        d.ellipse((cx-12, y-12, cx+12, y+12), fill=color)
        c.text(name, 634, y-21, 28, PAPER, sans=True)
        d.line((250, y, 423, y), fill="#876D52", width=2)
    c.centered("Discover practices for mindful balance", 1161, 27, "#CFBC9C")
    c.footer("Explore your chakras", cta=True)
    return c.image


def card_transit(data: dict, muhu: dict, font: Path, featured_planet: str = "jupiter") -> Image.Image:
    c = Canvas(font, "transit")
    d = c.draw
    positions = data["transits"]["positions"]
    planet = positions[featured_planet]
    name = planet.get("name_en") or featured_planet.title()
    glow(c.image, (823, 510), 227)
    c.motif("zodiac", 621, 265, 435, opacity=.69)
    c.motif("planet", 681, 348, 290)
    c.text("JYOTISH INSIGHT", 89, 214, 26, "#F3C485", True, True)
    c.text(f"{name} in", 85, 272, 87, PAPER, True, max_width=550)
    c.text(planet["rashi_en"], 85, 358, 90, "#F1BF82", True)
    c.text(date.fromisoformat(data["today"]["date"]).strftime("%d %B %Y").upper(),
           91, 483, 29, PAPER, sans=True)
    c.text("A VIEW OF TODAY'S SKY", 88, 640, 24, GOLD, True, True)
    lines = [
        ("SIGN", planet["rashi_en"]),
        ("MOTION", planet["motion_en"]),
        ("POSITION", f"{planet['degree_in_rashi']:.2f}° in {planet['rashi_en']}"),
        ("MOON", positions["moon"]["rashi_en"]),
    ]
    for i, (label, value) in enumerate(lines):
        y = 717 + i*111
        c.panel((81, y, 1000, y+87), fill="#20384A", outline="#526070", radius=18)
        c.text(label, 107, y+25, 22, "#F0BD7C", True, True)
        c.text(value, 378, y+15, 39 if len(value) < 18 else 31, PAPER, True, max_width=582)
    c.footer("Planetary positions  |  " + data["metadata"]["location"]["name"].split(",", 1)[0])
    return c.image


CARDS = (
    ("01-daily-panchang", card_panchang),
    ("02-plan-your-day", card_plan),
    ("03-upcoming-festival", card_festival),
    ("04-kundli-promo", card_kundli),
    ("05-chakra-promo", card_chakra),
    ("06-planetary-transit", card_transit),
)


def _mockup_spec(name: str, data: dict, muhu: dict):
    """Build preview-only facts without presenting a future festival as today."""
    from promo_studio.adapter import adapt_siddhanta
    from promo_studio.models import PostSpec, end_date

    today = date.fromisoformat(data["today"]["date"])
    clean, windows = adapt_siddhanta(data, muhu, today)
    en = clean["today"]["english"]
    base = {"location": clean["metadata"]["location"]["name"],
            "tithi": f"{en['paksha'].title()} {en['tithi_name']}",
            "nakshatra": en["nakshatra"]}
    if name == "01-daily-panchang":
        facts = {**base, **{key: en[key] for key in (
            "yoga", "karana", "sunrise", "sunset", "masa",
            "tithi_end", "nakshatra_end", "moonrise")}}
        for key in ("tithi_end", "nakshatra_end"):
            facts[f"{key}_date"] = end_date(today, en[key], en["sunrise"]).isoformat()
        for key, label in (("abhijit_muhurta", "abhijit"), ("rahu_kaal", "rahu")):
            if key in windows["muhurtas"]:
                slot = windows["muhurtas"][key]
                facts[label] = f"{slot['start']} – {slot['end']}"
                if "is_auspicious" in slot:
                    facts[f"{label}_auspicious"] = slot["is_auspicious"]
        return PostSpec("panchang", today.isoformat(), facts)
    if name == "02-plan-your-day":
        from promo_studio.selector import muhurta_facts

        facts = muhurta_facts(clean, windows)
        return None if facts is None else PostSpec("muhurta", today.isoformat(), {**base, **facts})
    if name == "03-upcoming-festival":
        upcoming = [f for f in data.get("upcoming_festivals", [])
                    if date.fromisoformat(f["date"]) >= today]
        if not upcoming:
            return None
        festival = next((f for f in upcoming if f["category"] == "major"), upcoming[0])
        when = date.fromisoformat(festival["date"])
        from promo_studio.models import text
        return PostSpec("festival", when.isoformat(), {
            "festival": text(festival["name_en"], "upcoming festival name"),
            "festival_hi": text(festival["name_hi"], "upcoming festival Hindi name"),
            "location": base["location"], "upcoming": True,
            "days_away": (when - today).days})
    if name == "04-kundli-promo":
        return PostSpec("kundli", today.isoformat(), {}, True)
    if name == "05-chakra-promo":
        return PostSpec("chakra", today.isoformat(), {}, True)
    if name == "06-planetary-transit":
        from promo_studio.selector import _transit

        chosen = _transit(clean)
        return None if chosen is None else PostSpec("transit", today.isoformat(),
                                                    {**base, **chosen[1]})
    raise ValueError(f"Unknown six-card preview {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data.json")
    parser.add_argument("--muhurta", type=Path, default=ROOT / "muhu.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--date", help="Archived date YYYY-MM-DD (default: today at the source location)")
    parser.add_argument("--hindi-font", type=Path)
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    muhu = json.loads(args.muhurta.read_text(encoding="utf-8"))
    timezone = data["metadata"]["location"]["timezone"]
    expected = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo(timezone)).date()
    data_date = date.fromisoformat(data["today"]["date"])
    muhu_date = date.fromisoformat(muhu["date"])
    if data_date != expected or muhu_date != expected:
        parser.error(f"Requested {expected}; data.json is {data_date}, muhu.json is {muhu_date}. "
                     "Update both inputs or use --date for an archived set.")
    font = find_font([r"C:\Windows\Fonts\Nirmala.ttc",
                      "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"],
                     args.hindi_font)
    from promo_studio.adapter import adapt_siddhanta
    from promo_studio.mock_art import brand, render as render_mock_art

    for warning in adapt_siddhanta(data, muhu, expected)[1]["warnings"]:
        print(f"WARNING: {warning}", file=sys.stderr)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, renderer in CARDS:
        path = args.output_dir / f"{name}-{expected}.png"
        spec = _mockup_spec(name, data, muhu)
        artwork = render_mock_art(spec) if spec is not None else None
        image = artwork if artwork is not None else renderer(data, muhu, font)
        brand(image, spec.kind if artwork is not None else None).save(path, optimize=True)
        print(path)
    caption = args.output_dir / f"caption-{expected}.txt"
    caption.write_text(data["today"]["hindi"]["ready_caption"] + "\n", encoding="utf-8")
    print(caption)


if __name__ == "__main__":
    main()
