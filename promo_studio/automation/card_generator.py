"""Dynamic visual card generator for Siddhanta Daily Cosmic Blueprint.

Renders pixel-perfect Material 3 Saffron & Gold Vedic visual cards (1080x1350)
using Pillow:
- Slide 1: The Visual Hook (Date, Masa, Tithi, Nakshatra, Vara, Sunrise/Sunset)
- Slide 2: The Value Add (Abhijit Muhurta, Rahu Kaal, Spiritual Focus)
- Combined Card: Both slides unified into one high-impact 4:5 Instagram portrait.
"""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from promo_studio.automation.panchang_engine import DailyPanchang

# ── Color Palette (Material 3 Saffron & Vedic Gold) ──────────────────────────

BG_TOP = (25, 9, 3)          # Very deep midnight saffron
BG_BOTTOM = (48, 16, 4)       # Warm deep vermilion
CARD_BG = (42, 18, 8, 220)    # Translucent card background
CARD_BORDER = (224, 90, 27)   # Vibrant saffron
GOLD_PRIMARY = (245, 176, 65) # Warm Vedic Gold
GOLD_LIGHT = (254, 235, 200)  # Cream Gold
WHITE = (255, 255, 255)
GREEN_AUSPICIOUS = (52, 211, 153) # Jade emerald for Abhijit
RED_RAHU = (248, 113, 113)        # Coral amber for Rahu Kaal
MUTED_TEXT = (209, 175, 155)


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Finds best system font (Arial, Segoe UI, Roboto, DejaVuSans) with fallback."""
    font_names = ["segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"]
    if bold:
        font_names = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"] + font_names

    # Check Windows fonts directory
    windir = os.environ.get("WINDIR", "C:\\Windows")
    for name in font_names:
        full_path = os.path.join(windir, "Fonts", name)
        if os.path.exists(full_path):
            try:
                return ImageFont.truetype(full_path, size)
            except Exception:
                pass

    # Check Linux / standard paths
    linux_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in linux_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass

    return ImageFont.load_default()


def _draw_gradient(img: Image.Image, c1: tuple, c2: tuple) -> None:
    """Draws vertical gradient background."""
    w, h = img.size
    base = Image.new("RGBA", (w, h), c1)
    top_r, top_g, top_b = c1
    bot_r, bot_g, bot_b = c2
    
    pixels = base.load()
    for y in range(h):
        r = int(top_r + (bot_r - top_r) * (y / h))
        g = int(top_g + (bot_g - top_g) * (y / h))
        b = int(top_b + (bot_b - top_b) * (y / h))
        for x in range(w):
            pixels[x, y] = (r, g, b, 255)
    img.paste(base, (0, 0))


def _draw_top_branding(draw: ImageDraw.ImageDraw, p: DailyPanchang, subtext: str = "THE DAILY COSMIC BLUEPRINT") -> None:
    # Pill background
    font_brand = _load_font(24, bold=True)
    pill_text = f"SIDDHANTA  •  {subtext}"
    draw.rounded_rectangle([200, 50, 880, 105], radius=25, fill=(60, 22, 9), outline=CARD_BORDER, width=2)
    draw.text((540, 77), pill_text, fill=GOLD_PRIMARY, font=font_brand, anchor="mm")

    # Date header
    font_date = _load_font(42, bold=True)
    draw.text((540, 160), p.date_formatted, fill=WHITE, font=font_date, anchor="mm")

    # Masa + Paksha subtitle
    font_sub = _load_font(28)
    sub_line = f"Month: {p.masa_name} Masa  |  Paksha: {p.paksha}  |  {p.vara_sa}"
    draw.text((540, 215), sub_line, fill=GOLD_LIGHT, font=font_sub, anchor="mm")

    # Decorative divider
    draw.line([250, 245, 830, 245], fill=CARD_BORDER, width=2)


def _draw_footer(draw: ImageDraw.ImageDraw) -> None:
    # Footer branding
    draw.line([100, 1260, 980, 1260], fill=(70, 28, 12), width=2)
    font_foot = _load_font(24, bold=True)
    draw.text((540, 1295), "SIDDHANTA APP  •  Vedic Panchang & Kundli  •  Google Play", fill=MUTED_TEXT, font=font_foot, anchor="mm")


def generate_slide_1_hook(p: DailyPanchang, output_path: str | Path) -> str:
    """Slide 1 (The Visual Hook): Date, Masa, Big 3 (Tithi, Nakshatra, Vara), Sunrise/Sunset."""
    w, h = 1080, 1350
    img = Image.new("RGBA", (w, h))
    _draw_gradient(img, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    _draw_top_branding(draw, p, "THE DAILY COSMIC BLUEPRINT")

    # Festival Banner if active
    top_offset = 290
    if p.is_festival:
        draw.rounded_rectangle([80, top_offset, 1000, top_offset + 120], radius=20, fill=(90, 25, 10), outline=GOLD_PRIMARY, width=3)
        font_fest = _load_font(34, bold=True)
        draw.text((540, top_offset + 42), f"✨ {p.festival_name} ✨", fill=GOLD_PRIMARY, font=font_fest, anchor="mm")
        font_fest_sub = _load_font(22)
        draw.text((540, top_offset + 85), p.festival_note[:70], fill=WHITE, font=font_fest_sub, anchor="mm")
        top_offset += 150

    # The Big 3: TITHI, NAKSHATRA, VARA
    # Card 1: Tithi
    card1_y = top_offset
    draw.rounded_rectangle([80, card1_y, 1000, card1_y + 190], radius=22, fill=(45, 17, 7), outline=CARD_BORDER, width=2)
    font_lbl = _load_font(24, bold=True)
    draw.text((120, card1_y + 35), "TODAY'S TITHI", fill=GOLD_PRIMARY, font=font_lbl)
    font_val = _load_font(52, bold=True)
    draw.text((120, card1_y + 105), p.tithi_name, fill=WHITE, font=font_val)

    # Card 2: Nakshatra
    card2_y = card1_y + 215
    draw.rounded_rectangle([80, card2_y, 1000, card2_y + 190], radius=22, fill=(45, 17, 7), outline=CARD_BORDER, width=2)
    draw.text((120, card2_y + 35), "ACTIVE NAKSHATRA", fill=GOLD_PRIMARY, font=font_lbl)
    draw.text((120, card2_y + 105), f"{p.nakshatra_name} (Moon in {p.moon_rashi.split()[0]})", fill=WHITE, font=font_val)

    # Card 3: Vara (Weekday) & Deity
    card3_y = card2_y + 215
    draw.rounded_rectangle([80, card3_y, 1000, card3_y + 190], radius=22, fill=(45, 17, 7), outline=CARD_BORDER, width=2)
    draw.text((120, card3_y + 35), f"VARA: {p.vara_sa.upper()} ({p.vara_en.upper()})", fill=GOLD_PRIMARY, font=font_lbl)
    font_deity = _load_font(40, bold=True)
    draw.text((120, card3_y + 100), f"Active Deity: {p.deity}", fill=GOLD_LIGHT, font=font_deity)

    # Sunrise & Sunset Strip
    sun_y = card3_y + 215
    draw.rounded_rectangle([80, sun_y, 1000, sun_y + 90], radius=18, fill=(35, 13, 5), outline=(75, 28, 12), width=1)
    font_sun = _load_font(28, bold=True)
    sun_text = f"Sunrise: {p.sunrise_str}    |    Sunset: {p.sunset_str}"
    draw.text((540, sun_y + 45), sun_text, fill=WHITE, font=font_sun, anchor="mm")

    # Swipe CTA
    font_swipe = _load_font(24, bold=True)
    draw.text((540, 1220), "👉 SWIPE FOR AUSPICIOUS & RAHU KAAL WINDOWS", fill=GOLD_PRIMARY, font=font_swipe, anchor="mm")

    _draw_footer(draw)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return str(output_path)


def generate_slide_2_value(p: DailyPanchang, output_path: str | Path) -> str:
    """Slide 2 (The Value Add): Abhijit Muhurta, Rahu Kaal, Spiritual Guidance."""
    w, h = 1080, 1350
    img = Image.new("RGBA", (w, h))
    _draw_gradient(img, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    _draw_top_branding(draw, p, "ACTIONABLE DAILY WINDOWS")

    top_y = 290
    # Auspicious Card: Abhijit Muhurta
    draw.rounded_rectangle([80, top_y, 1000, top_y + 240], radius=24, fill=(20, 45, 30), outline=GREEN_AUSPICIOUS, width=3)
    font_badge = _load_font(26, bold=True)
    draw.text((120, top_y + 45), "⭐  ABHIJIT MUHURTA (MOST AUSPICIOUS)", fill=GREEN_AUSPICIOUS, font=font_badge)
    font_time = _load_font(60, bold=True)
    draw.text((120, top_y + 125), p.abhijit_muhurta, fill=WHITE, font=font_time)
    font_desc = _load_font(24)
    draw.text((120, top_y + 195), "Ideal for new beginnings, contracts, sacred purchases & travel.", fill=(200, 240, 220), font=font_desc)

    # Inauspicious Card: Rahu Kaal
    rahu_y = top_y + 270
    draw.rounded_rectangle([80, rahu_y, 1000, rahu_y + 240], radius=24, fill=(45, 18, 18), outline=RED_RAHU, width=3)
    draw.text((120, rahu_y + 45), "⚠️  RAHU KAAL (AVOID CRITICAL INITIATIVES)", fill=RED_RAHU, font=font_badge)
    draw.text((120, rahu_y + 125), p.rahu_kaal, fill=WHITE, font=font_time)
    draw.text((120, rahu_y + 195), "Postpone signing contracts, new purchases & starting journeys.", fill=(245, 205, 205), font=font_desc)

    # Day's Cosmic Focus & Planetary Transit Radar
    guidance_y = rahu_y + 250
    draw.rounded_rectangle([80, guidance_y, 1000, guidance_y + 300], radius=24, fill=(45, 17, 7), outline=CARD_BORDER, width=2)
    
    draw.text((120, guidance_y + 35), "🪐  PLANETARY TRANSIT RADAR (GOCHAR)", fill=GOLD_PRIMARY, font=font_badge)
    
    font_gochar_bold = _load_font(28, bold=True)
    font_gochar_sub = _load_font(24)
    
    if p.gochar:
        transit_line = f"Guru in {p.gochar.jupiter_sign.split()[0]}  •  Shani in {p.gochar.saturn_sign.split()[0]}  •  Rahu in {p.gochar.rahu_sign.split()[0]}"
        draw.text((120, guidance_y + 80), transit_line, fill=WHITE, font=font_gochar_bold)
        
        fav_line = f"✨ High Alignment Rashis: {', '.join(p.gochar.favorable_rashis)}"
        draw.text((120, guidance_y + 130), fav_line, fill=GOLD_LIGHT, font=font_gochar_bold)
        
        dasha_line = f"📌 {p.gochar.dasha_spotlight_title}: {p.gochar.dasha_spotlight_desc[:65]}..."
        draw.text((120, guidance_y + 180), dasha_line, fill=MUTED_TEXT, font=font_gochar_sub)
        
        hook_line = "Check your personal birth Kundli & active Dasha in Siddhanta!"
        draw.text((120, guidance_y + 225), hook_line, fill=GREEN_AUSPICIOUS, font=font_gochar_bold)
    else:
        draw.text((120, guidance_y + 100), p.remedy[:80], fill=WHITE, font=font_gochar_bold)

    # App CTA Banner
    cta_y = guidance_y + 325
    draw.rounded_rectangle([150, cta_y, 930, cta_y + 70], radius=15, fill=(60, 22, 9), outline=GOLD_PRIMARY, width=1)
    font_cta = _load_font(24, bold=True)
    draw.text((540, cta_y + 35), "📲 Get Your Exact Birth Kundli & Dasha on Siddhanta App", fill=GOLD_PRIMARY, font=font_cta, anchor="mm")

    _draw_footer(draw)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return str(output_path)


def generate_combined_card(p: DailyPanchang, output_path: str | Path) -> str:
    """Combined 2-in-1 High-Impact Card (1080x1350 4:5 Instagram Portrait)."""
    w, h = 1080, 1350
    img = Image.new("RGBA", (w, h))
    _draw_gradient(img, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    _draw_top_branding(draw, p, "DAILY COSMIC BLUEPRINT")

    # Section 1: Core Panchang
    y = 270
    draw.rounded_rectangle([70, y, 1010, y + 360], radius=22, fill=(45, 17, 7), outline=CARD_BORDER, width=2)
    font_head = _load_font(26, bold=True)
    draw.text((110, y + 35), "TODAY'S SACRED ENERGIES", fill=GOLD_PRIMARY, font=font_head)
    
    font_bold = _load_font(38, bold=True)
    draw.text((110, y + 95), f"Tithi: {p.tithi_name}", fill=WHITE, font=font_bold)
    draw.text((110, y + 160), f"Nakshatra: {p.nakshatra_name} (in {p.moon_rashi.split()[0]})", fill=WHITE, font=font_bold)
    draw.text((110, y + 225), f"Vara: {p.vara_sa} ({p.vara_en})", fill=GOLD_LIGHT, font=font_bold)
    
    font_sun = _load_font(26)
    draw.text((110, y + 295), f"🌅 Sunrise: {p.sunrise_str}    |    🌇 Sunset: {p.sunset_str}", fill=MUTED_TEXT, font=font_sun)

    # Section 2: Actionable Windows
    y_win = y + 390
    draw.rounded_rectangle([70, y_win, 520, y_win + 220], radius=20, fill=(20, 45, 30), outline=GREEN_AUSPICIOUS, width=2)
    font_win_lbl = _load_font(22, bold=True)
    draw.text((95, y_win + 28), "⭐ ABHIJIT MUHURTA", fill=GREEN_AUSPICIOUS, font=font_win_lbl)
    font_win_time = _load_font(34, bold=True)
    draw.text((95, y_win + 85), p.abhijit_muhurta, fill=WHITE, font=font_win_time)
    font_win_sub = _load_font(18)
    draw.text((95, y_win + 155), "Most Auspicious Window", fill=(190, 240, 210), font=font_win_sub)

    draw.rounded_rectangle([560, y_win, 1010, y_win + 220], radius=20, fill=(45, 18, 18), outline=RED_RAHU, width=2)
    draw.text((585, y_win + 28), "⚠️ RAHU KAAL", fill=RED_RAHU, font=font_win_lbl)
    draw.text((585, y_win + 85), p.rahu_kaal, fill=WHITE, font=font_win_time)
    draw.text((585, y_win + 155), "Avoid New Beginnings", fill=(245, 195, 195), font=font_win_sub)

    # Section 3: Spiritual Remedy / Deity Guidance
    y_guide = y_win + 245
    draw.rounded_rectangle([70, y_guide, 1010, y_guide + 260], radius=20, fill=(40, 15, 6), outline=CARD_BORDER, width=2)
    deity_title = f"🕉️ DEITY & REMEDY: {p.deity.upper()}"
    draw.text((110, y_guide + 30), deity_title[:45], fill=GOLD_PRIMARY, font=font_head)
    
    font_rem = _load_font(26)
    # wrap remedy text
    words = p.remedy.split()
    lines, curr = [], []
    for w_word in words:
        curr.append(w_word)
        if len(" ".join(curr)) > 50:
            lines.append(" ".join(curr[:-1]))
            curr = [w_word]
    if curr:
        lines.append(" ".join(curr))

    r_y = y_guide + 85
    for l in lines[:3]:
        draw.text((110, r_y), l, fill=WHITE, font=font_rem)
        r_y += 40

    _draw_footer(draw)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return str(output_path)
