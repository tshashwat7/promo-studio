"""High-Precision Template Renderer for Siddhanta Social Graphics.

Directly composites daily dynamic astronomical data onto Siddhanta's
official master background templates matching the user's agency mockups:
- Slide 1: Panchang Temple Riverside Template ("Today's Panchang")
- Slide 2: Golden Temple Sunrise with Diyas and Lotuses ("Plan Your Day Wisely")
- Slide 3: Celestial Temple Astrology Poster Template ("Jyotish Insight / Planetary Transits")
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from promo_studio.automation.panchang_engine import DailyPanchang

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
FONTS_DIR = ASSETS_DIR / "fonts"

# ── Color Palette Matching Official Mockups ──────────────────────────────────
COLOR_CRIMSON = (122, 20, 20)          # #7A1414 (Headers & Primary Values)
COLOR_GOLD_TEXT = (180, 115, 30)       # #B4731E (Jyotish Panchang subtitle)
COLOR_DARK = (30, 25, 22)              # #1E1916 (Timings & Primary Dark Text)
COLOR_MUTED = (112, 102, 94)           # #70665E (Labels & Subtitles)
COLOR_CARD_BG = (255, 253, 248, 230)   # Translucent cream card
COLOR_CARD_BORDER = (235, 222, 202)
COLOR_GREEN_TITLE = (36, 105, 68)      # #246944 (Abhijit Muhurta)
COLOR_GREEN_CIRCLE = (220, 245, 230)
COLOR_RED_TITLE = (169, 50, 38)        # #A93226 (Rahu Kaal)
COLOR_RED_CIRCLE = (253, 230, 230)
COLOR_AMBER_TITLE = (183, 121, 31)     # #B7791F (Choghadiya)
COLOR_AMBER_CIRCLE = (254, 243, 220)
COLOR_BTN_RED = (122, 20, 20)          # Bottom action button
WHITE = (255, 255, 255)


def _load_font(name: str, size: int) -> ImageFont.ImageFont:
    p = FONTS_DIR / name
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _font_serif(size: int, bold: bool = True) -> ImageFont.ImageFont:
    return _load_font("LibreBaskerville-Bold.ttf" if bold else "LibreBaskerville-Regular.ttf", size)


def _font_sans(size: int, bold: bool = True) -> ImageFont.ImageFont:
    return _load_font("DMSans-Bold.ttf" if bold else "DMSans-Medium.ttf", size)


def _font_hindi(size: int) -> ImageFont.ImageFont:
    return _load_font("NotoSansDevanagari-Regular.ttf", size)


def _draw_brand_header(canvas: Image.Image, draw: ImageDraw.ImageDraw, x: int = 75, y: int = 55) -> None:
    """Draws the official Siddhanta Jyotish Panchang logo & wordmark."""
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((72, 72), Image.Resampling.LANCZOS)
            canvas.alpha_composite(logo, (x, y))
        except Exception:
            pass

    font_title = _font_serif(34, bold=True)
    font_sub = _font_serif(20, bold=False)
    
    text_x = x + 90
    draw.text((text_x, y + 4), "Siddhanta", fill=COLOR_CRIMSON, font=font_title)
    draw.text((text_x, y + 42), "Jyotish Panchang", fill=COLOR_GOLD_TEXT, font=font_sub)


# ── Illustration Compositing Helpers ──────────────────────────────────────────

def _paste_badge_icon(
    canvas: Image.Image,
    icon_rel_path: str,
    box: tuple[int, int, int, int],
    bg_color: tuple[int, int, int] | tuple[int, int, int, int],
    padding: int = 8,
) -> bool:
    """Renders a circular badge with background color and the illustration centered inside."""
    x1, y1, x2, y2 = box
    draw = ImageDraw.Draw(canvas)
    draw.ellipse(box, fill=bg_color)

    p = ASSETS_DIR / "illustrations" / icon_rel_path
    if not p.exists():
        return False

    try:
        icon = Image.open(p).convert("RGBA")
        inner_w = (x2 - x1) - 2 * padding
        inner_h = (y2 - y1) - 2 * padding
        w, h = icon.size
        scale = min(inner_w / w, inner_h / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        icon = icon.resize((nw, nh), Image.Resampling.LANCZOS)

        corner_r, corner_g, corner_b, _ = icon.getpixel((0, 0))
        if corner_r > 190 and corner_g > 190 and corner_b > 170:
            getter = getattr(icon, "get_flattened_data", icon.getdata)
            datas = list(getter())
            tol_sq = 35 * 35
            new_data = []
            for r, g, b, a in datas:
                dist_sq = (r - corner_r) ** 2 + (g - corner_g) ** 2 + (b - corner_b) ** 2
                if dist_sq < tol_sq:
                    alpha = int(255 * (dist_sq / tol_sq))
                    new_data.append((r, g, b, min(a, alpha)))
                else:
                    new_data.append((r, g, b, a))
            icon.putdata(new_data)

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        canvas.alpha_composite(icon, (cx - nw // 2, cy - nh // 2))
        return True
    except Exception:
        return False


# ── Card Renderers ───────────────────────────────────────────────────────────

def generate_slide_1_hook(p: DailyPanchang, output_path: str | Path) -> str:
    """Slide 1 (Today's Panchang): Matches Mockup 1 layout with pixel accuracy."""
    template_path = TEMPLATES_DIR / "panchang_template.png"
    canvas = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 1. Official Header
    _draw_brand_header(canvas, draw, x=75, y=55)

    # 2. Main Title: Today's Panchang
    draw.text((75, 175), "Today's", fill=COLOR_CRIMSON, font=_font_serif(64, bold=True))
    draw.text((75, 248), "Panchang", fill=COLOR_CRIMSON, font=_font_serif(64, bold=True))

    # Date header
    day_str = p.date.strftime("%d %B %Y").upper()
    draw.text((75, 338), day_str, fill=COLOR_DARK, font=_font_sans(24, bold=True))
    
    paksha_str = f"{p.vara_en.upper()}  •  {p.paksha.upper()} PAKSHA"
    draw.text((75, 372), paksha_str, fill=COLOR_MUTED, font=_font_sans(19, bold=False))

    # 3. Card 1: TITHI
    c1_y = 430
    c_w, c_h = 560, 115
    draw.rounded_rectangle([75, c1_y, 75 + c_w, c1_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER, width=1)
    
    # Official Siddhanta Moon illustration badge
    _paste_badge_icon(canvas, "icons/Moon.webp", (95, c1_y + 22, 165, c1_y + 92), COLOR_AMBER_CIRCLE, padding=12)
    
    draw.text((185, c1_y + 20), "Tithi", fill=COLOR_MUTED, font=_font_sans(17))
    draw.text((185, c1_y + 44), p.tithi_name, fill=COLOR_CRIMSON, font=_font_serif(26, bold=True))
    draw.text((185, c1_y + 80), f"{p.tithi_name_hi}", fill=COLOR_MUTED, font=_font_hindi(18))

    # 4. Card 2: NAKSHATRA
    c2_y = c1_y + 135
    draw.rounded_rectangle([75, c2_y, 75 + c_w, c2_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER, width=1)
    
    # Official Siddhanta Nakshatra star illustration badge
    _paste_badge_icon(canvas, "icons/nakshatra.webp", (95, c2_y + 22, 165, c2_y + 92), COLOR_AMBER_CIRCLE, padding=6)
    
    draw.text((185, c2_y + 20), "Nakshatra", fill=COLOR_MUTED, font=_font_sans(17))
    draw.text((185, c2_y + 44), p.nakshatra_name, fill=COLOR_CRIMSON, font=_font_serif(26, bold=True))
    draw.text((185, c2_y + 80), p.nakshatra_name_hi, fill=COLOR_MUTED, font=_font_hindi(18))

    # 5. Sunrise & Sunset Bottom Strip with Official Siddhanta Icons
    sun_y = 1255
    strip_w = 440
    draw.rounded_rectangle([75, sun_y, 75 + strip_w, sun_y + 75], radius=16, fill=(255, 253, 248, 235), outline=COLOR_CARD_BORDER, width=1)
    
    _paste_badge_icon(canvas, "icons/Sunrise.webp", (90, sun_y + 12, 142, sun_y + 64), COLOR_AMBER_CIRCLE, padding=6)
    draw.text((152, sun_y + 16), "Sunrise", fill=COLOR_MUTED, font=_font_sans(15))
    draw.text((152, sun_y + 38), p.sunrise_str, fill=COLOR_DARK, font=_font_sans(20, bold=True))
    
    draw.line([250, sun_y + 15, 250, sun_y + 60], fill=(225, 210, 190), width=1)

    _paste_badge_icon(canvas, "icons/Sunset.webp", (265, sun_y + 12, 317, sun_y + 64), COLOR_AMBER_CIRCLE, padding=6)
    draw.text((327, sun_y + 16), "Sunset", fill=COLOR_MUTED, font=_font_sans(15))
    draw.text((327, sun_y + 38), p.sunset_str, fill=COLOR_DARK, font=_font_sans(20, bold=True))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


def generate_slide_2_value(p: DailyPanchang, output_path: str | Path) -> str:
    """Slide 2 (Plan Your Day Wisely): Matches Mockup 2 layout with pixel accuracy."""
    template_path = TEMPLATES_DIR / "plan_day_template.png"
    canvas = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # 1. Official Header
    _draw_brand_header(canvas, draw, x=75, y=55)

    # 2. Main Title: Plan Your Day Wisely
    draw.text((75, 175), "Plan Your", fill=COLOR_CRIMSON, font=_font_serif(60, bold=True))
    draw.text((75, 245), "Day Wisely", fill=COLOR_CRIMSON, font=_font_serif(60, bold=True))
    
    draw.text((75, 330), "Auspicious timings for a more harmonious day.", fill=COLOR_MUTED, font=_font_serif(21, bold=False))

    # 3. Card 1: ABHIJIT MUHURTA (Emerald Green with Sacred Kalash)
    c1_y = 395
    c_w, c_h = 580, 130
    draw.rounded_rectangle([75, c1_y, 75 + c_w, c1_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER, width=1)
    _paste_badge_icon(canvas, "icons/kalash.webp", (95, c1_y + 22, 165, c1_y + 92), COLOR_GREEN_CIRCLE, padding=10)

    draw.text((185, c1_y + 20), "Abhijit Muhurta", fill=COLOR_GREEN_TITLE, font=_font_sans(20, bold=True))
    draw.text((185, c1_y + 50), p.abhijit_muhurta, fill=COLOR_DARK, font=_font_sans(26, bold=True))
    draw.text((185, c1_y + 88), "A highly auspicious time for important work.", fill=COLOR_MUTED, font=_font_sans(17))

    # 4. Card 2: RAHU KAAL (Caution Red with Rahu Planet Symbol)
    c2_y = c1_y + 150
    draw.rounded_rectangle([75, c2_y, 75 + c_w, c2_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER, width=1)
    _paste_badge_icon(canvas, "planets/rahu.webp", (95, c2_y + 22, 165, c2_y + 92), COLOR_RED_CIRCLE, padding=12)

    draw.text((185, c2_y + 20), "Rahu Kaal", fill=COLOR_RED_TITLE, font=_font_sans(20, bold=True))
    draw.text((185, c2_y + 50), p.rahu_kaal, fill=COLOR_DARK, font=_font_sans(26, bold=True))
    draw.text((185, c2_y + 88), "Avoid starting new important activities.", fill=COLOR_MUTED, font=_font_sans(17))

    # 5. Card 3: CHOGHADIYA (Warm Amber with Authentic Choghadiya Matrix)
    c3_y = c2_y + 150
    draw.rounded_rectangle([75, c3_y, 75 + c_w, c3_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER, width=1)
    _paste_badge_icon(canvas, "icons/home/choghadiya.webp", (95, c3_y + 22, 165, c3_y + 92), COLOR_AMBER_CIRCLE, padding=8)

    draw.text((185, c3_y + 20), "Choghadiya (Shubh / Labh)", fill=COLOR_AMBER_TITLE, font=_font_sans(20, bold=True))
    draw.text((185, c3_y + 50), "Morning Auspicious Periods", fill=COLOR_DARK, font=_font_sans(24, bold=True))
    draw.text((185, c3_y + 88), "Good for business, finance & travel.", fill=COLOR_MUTED, font=_font_sans(17))

    # 6. Bottom Sign-off Quote (in elegant translucent card)
    quote_y = 860
    draw.rounded_rectangle([75, quote_y, 75 + c_w, quote_y + 60], radius=14, fill=(255, 253, 248, 225), outline=COLOR_CARD_BORDER)
    draw.text((75 + c_w // 2, quote_y + 30), "“Right timing brings the right results.”", fill=COLOR_CRIMSON, font=_font_serif(22, bold=False), anchor="mm")

    # 7. Bottom CTA Button
    btn_y = 940
    draw.rounded_rectangle([75, btn_y, 75 + 460, btn_y + 62], radius=16, fill=COLOR_BTN_RED)
    draw.text((75 + 230, btn_y + 31), "Explore in Siddhanta  ›", fill=WHITE, font=_font_sans(20, bold=True), anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


def generate_combined_card(p: DailyPanchang, output_path: str | Path) -> str:
    """Slide 3 (Planetary Gochar Transit): Uses the Celestial Temple template."""
    template_path = TEMPLATES_DIR / "transit_template.png"
    canvas = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    _draw_brand_header(canvas, draw, x=75, y=55)

    # Pill badge
    draw.rounded_rectangle([75, 160, 290, 198], radius=10, fill=(255, 245, 230), outline=COLOR_CARD_BORDER)
    draw.text((182, 179), "JYOTISH INSIGHT", fill=COLOR_GOLD_TEXT, font=_font_sans(17, bold=True), anchor="mm")

    # Transit Title
    jup_sign = p.gochar.jupiter_sign if p.gochar else "Gemini"
    
    draw.text((75, 220), "Jupiter Transit", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))
    draw.text((75, 285), f"in {jup_sign.split()[0]}", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))

    draw.text((75, 365), f"GURU GOCHAR IN {jup_sign.upper()}", fill=COLOR_MUTED, font=_font_sans(19, bold=True))

    # Bullet Points with Official Siddhanta Illustrations
    bullets_y = 425
    c_w, b_h = 580, 110
    draw.rounded_rectangle([75, bullets_y, 75 + c_w, bullets_y + b_h], radius=16, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)
    _paste_badge_icon(canvas, "planets/jupiter.webp", (95, bullets_y + 25, 155, bullets_y + 85), COLOR_AMBER_CIRCLE, padding=6)
    draw.text((175, bullets_y + 22), "Brings expansion in knowledge", fill=COLOR_DARK, font=_font_sans(20, bold=True))
    draw.text((175, bullets_y + 55), "and spiritual clarity for seekers", fill=COLOR_MUTED, font=_font_sans(17))

    b2_y = bullets_y + 125
    draw.rounded_rectangle([75, b2_y, 75 + c_w, b2_y + b_h], radius=16, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)
    _paste_badge_icon(canvas, "icons/home/transit.webp", (95, b2_y + 25, 155, b2_y + 85), COLOR_GREEN_CIRCLE, padding=8)
    favs = ", ".join(p.gochar.favorable_rashis[:3]) if p.gochar else "Taurus, Cancer, Virgo"
    draw.text((175, b2_y + 22), f"Favorable flow: {favs}", fill=COLOR_GREEN_TITLE, font=_font_sans(20, bold=True))
    draw.text((175, b2_y + 55), "Positive momentum in education & projects", fill=COLOR_MUTED, font=_font_sans(17))

    b3_y = b2_y + 125
    draw.rounded_rectangle([75, b3_y, 75 + c_w, b3_y + b_h], radius=16, fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)
    _paste_badge_icon(canvas, "icons/home/kundli.webp", (95, b3_y + 25, 155, b3_y + 85), COLOR_AMBER_CIRCLE, padding=8)
    dasha_title = p.gochar.dasha_spotlight_title if p.gochar else "Vimshottari Dasha"
    draw.text((175, b3_y + 22), f"Dasha: {dasha_title[:28]}", fill=COLOR_DARK, font=_font_sans(20, bold=True))
    draw.text((175, b3_y + 55), "Check your active Mahadasha in Siddhanta", fill=COLOR_MUTED, font=_font_sans(17))

    # Quote (in soft translucent card matching Mockup 6)
    quote_y = 820
    draw.rounded_rectangle([75, quote_y, 75 + c_w, quote_y + 60], radius=14, fill=(255, 253, 248, 225), outline=COLOR_CARD_BORDER)
    draw.text((75 + c_w // 2, quote_y + 30), "“When Guru moves, wisdom finds a new direction.”", fill=COLOR_CRIMSON, font=_font_serif(21, bold=False), anchor="mm")

    # Button
    btn_y = 900
    draw.rounded_rectangle([75, btn_y, 75 + 460, btn_y + 62], radius=16, fill=COLOR_BTN_RED)
    draw.text((75 + 230, btn_y + 31), "Create Kundli in Siddhanta  ›", fill=WHITE, font=_font_sans(20, bold=True), anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)
