"""Siddhanta 6-Card Universe Generator.

Pixel-accurate rendering engine matching the agency mockups in media_1791060503794.jpg:
1. Daily Panchang (Clean, elegant overview with key details)
2. Plan Your Day (Muhurta, Rahu Kaal and Choghadiya)
3. Festival (Navratri / Festival Announcement)
4. Kundli (Core features with clean chart motif)
5. Chakra (Balance Your Inner Energy with 7 chakras)
6. Jyotish Insight (Jupiter Transit / Planetary movements)
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
ILLUST_DIR = ASSETS_DIR / "illustrations"
IMAGES_DIR = ASSETS_DIR / "images"

# Standard Tall Portrait Dimensions matching the Mockup
CARD_W = 1080
CARD_H = 2160

# Palette
COLOR_CRIMSON = (122, 20, 20)           # #7A1414 (Main Titles & Accents)
COLOR_GOLD = (180, 115, 30)            # #B4731E (Subtitles & Gold Accents)
COLOR_DARK = (30, 25, 22)               # #1E1916 (Timings & Headers)
COLOR_MUTED = (112, 102, 94)            # #70665E (Descriptions)
COLOR_CARD_BG = (255, 253, 248, 235)    # Translucent Cream
COLOR_BORDER = (235, 222, 202)
COLOR_GREEN = (30, 107, 63)             # #1E6B3F (Abhijit)
COLOR_RED = (138, 28, 20)               # #8A1C14 (Rahu)
COLOR_AMBER = (180, 115, 30)            # #B4731E (Choghadiya)
WHITE = (255, 255, 255)


def _font_serif(size: int, bold: bool = True, italic: bool = False) -> ImageFont.ImageFont:
    if italic:
        f = "LibreBaskerville-Italic.ttf"
    elif bold:
        f = "LibreBaskerville-Bold.ttf"
    else:
        f = "LibreBaskerville-Regular.ttf"
    p = FONTS_DIR / f
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _font_sans(size: int, bold: bool = True) -> ImageFont.ImageFont:
    f = "DMSans-Bold.ttf" if bold else "DMSans-Medium.ttf"
    p = FONTS_DIR / f
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _font_hindi(size: int) -> ImageFont.ImageFont:
    p = FONTS_DIR / "NotoSansDevanagari-Regular.ttf"
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _clean_transparency(img: Image.Image) -> Image.Image:
    """Removes near-white/cream corner background for crisp overlay."""
    img = img.convert("RGBA")
    corner_r, corner_g, corner_b, _ = img.getpixel((0, 0))
    if corner_r > 190 and corner_g > 190 and corner_b > 170:
        getter = getattr(img, "get_flattened_data", img.getdata)
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
        img.putdata(new_data)
    return img


def _paste_icon_badge(
    canvas: Image.Image,
    icon_path: Path,
    box: tuple[int, int, int, int],
    badge_fill: tuple[int, int, int] | tuple[int, int, int, int],
    padding: int = 16,
    badge_outline: tuple[int, int, int] | None = None,
) -> None:
    """Draws a circular badge and composites an illustration centered inside."""
    x1, y1, x2, y2 = box
    draw = ImageDraw.Draw(canvas)
    draw.ellipse(box, fill=badge_fill, outline=badge_outline, width=2 if badge_outline else 0)

    if not icon_path.exists():
        return

    try:
        icon = Image.open(icon_path)
        icon = _clean_transparency(icon)
        inner_w = (x2 - x1) - 2 * padding
        inner_h = (y2 - y1) - 2 * padding
        w, h = icon.size
        scale = min(inner_w / w, inner_h / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        icon = icon.resize((nw, nh), Image.Resampling.LANCZOS)

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        canvas.alpha_composite(icon, (cx - nw // 2, cy - nh // 2))
    except Exception:
        pass


def _draw_brand_header(canvas: Image.Image, draw: ImageDraw.ImageDraw, y: int = 70) -> None:
    """Draws the official Siddhanta Jyotish Panchang header with ornamental divider."""
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((96, 96), Image.Resampling.LANCZOS)
            canvas.alpha_composite(logo, (75, y))
        except Exception:
            pass

    font_title = _font_serif(44, bold=True)
    font_sub = _font_serif(26, bold=False)

    text_x = 75 + 115
    draw.text((text_x, y + 4), "Siddhanta", fill=COLOR_CRIMSON, font=font_title)
    draw.text((text_x, y + 54), "Jyotish Panchang", fill=COLOR_GOLD, font=font_sub)

    # Ornamental divider: ─── ◆ ───
    div_y = y + 130
    draw.line([75, div_y, 490, div_y], fill=(210, 180, 130, 140), width=2)
    draw.line([590, div_y, 1005, div_y], fill=(210, 180, 130, 140), width=2)
    # Diamond at center
    cx, cy = 540, div_y
    draw.polygon([(cx, cy - 8), (cx + 8, cy), (cx, cy + 8), (cx - 8, cy)], fill=COLOR_GOLD)


def _draw_cta_button(canvas: Image.Image, draw: ImageDraw.ImageDraw, text: str, y: int = 1920) -> None:
    """Draws the official rounded crimson CTA button matching Mockups 3, 4, 5."""
    btn_box = [75, y, 1005, y + 105]
    draw.rounded_rectangle(btn_box, radius=24, fill=COLOR_CRIMSON)

    # Phone icon (vector)
    ph_x, ph_y = 125, y + 32
    draw.rounded_rectangle([ph_x, ph_y, ph_x + 28, ph_y + 44], radius=5, outline=WHITE, width=3)
    draw.line([ph_x + 9, ph_y + 36, ph_x + 19, ph_y + 36], fill=WHITE, width=2)

    # Label & Arrow
    font_btn = _font_sans(30, bold=True)
    draw.text((540, y + 52), text, fill=WHITE, font=font_btn, anchor="mm")
    draw.text((955, y + 52), "›", fill=WHITE, font=_font_serif(44, bold=True), anchor="mm")


def _prepare_canvas(template_name: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Prepares a standard 1080x2160 canvas with the background template fitted."""
    t_path = TEMPLATES_DIR / template_name
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (255, 252, 245, 255))
    if t_path.exists():
        t_img = Image.open(t_path).convert("RGBA")
        # Cover 1080x2160 preserving aspect ratio
        scale = max(CARD_W / t_img.width, CARD_H / t_img.height)
        nw = int(t_img.width * scale)
        nh = int(t_img.height * scale)
        t_img = t_img.resize((nw, nh), Image.Resampling.LANCZOS)
        # Center crop
        crop_x = (nw - CARD_W) // 2
        crop_y = (nh - CARD_H) // 2
        cropped = t_img.crop((crop_x, crop_y, crop_x + CARD_W, crop_y + CARD_H))
        canvas.alpha_composite(cropped, (0, 0))
    draw = ImageDraw.Draw(canvas)
    return canvas, draw


# ═════════════════════════════════════════════════════════════════════════════
# 1. DAILY PANCHANG (Clean, elegant overview with key details)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_1_panchang(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_canvas("panchang_template.png")
    _draw_brand_header(canvas, draw, y=70)

    # Title
    draw.text((75, 280), "Today's", fill=COLOR_CRIMSON, font=_font_serif(84, bold=True))
    draw.text((75, 375), "Panchang", fill=COLOR_CRIMSON, font=_font_serif(84, bold=True))

    # Date
    day_str = p.date.strftime("%d %B %Y").upper()
    draw.text((75, 510), day_str, fill=COLOR_DARK, font=_font_sans(32, bold=True))
    paksha_str = f"{p.vara_en.upper()}  •  {p.paksha.upper()} PAKSHA"
    draw.text((75, 555), paksha_str, fill=COLOR_MUTED, font=_font_sans(24, bold=False))

    # Tithi Item (badge on left, clean text on right - NO big white box)
    t_y = 760
    _paste_icon_badge(
        canvas,
        ILLUST_DIR / "icons" / "Moon.webp",
        (75, t_y, 205, t_y + 130),
        badge_fill=(254, 243, 220),
        badge_outline=(230, 210, 180),
        padding=18,
    )
    draw.text((245, t_y + 8), "Tithi", fill=COLOR_MUTED, font=_font_sans(26))
    draw.text((245, t_y + 45), p.tithi_name, fill=COLOR_CRIMSON, font=_font_serif(42, bold=True))
    draw.text((245, t_y + 95), "Until 3:12 PM", fill=COLOR_MUTED, font=_font_sans(24))
    draw.text((410, t_y + 95), "•", fill=COLOR_MUTED, font=_font_sans(24))
    draw.text((435, t_y + 95), p.tithi_name_hi, fill=COLOR_MUTED, font=_font_hindi(22))

    # Nakshatra Item
    n_y = 980
    _paste_icon_badge(
        canvas,
        ILLUST_DIR / "icons" / "nakshatra.webp",
        (75, n_y, 205, n_y + 130),
        badge_fill=(254, 243, 220),
        badge_outline=(230, 210, 180),
        padding=14,
    )
    draw.text((245, n_y + 8), "Nakshatra", fill=COLOR_MUTED, font=_font_sans(26))
    draw.text((245, n_y + 45), p.nakshatra_name, fill=COLOR_CRIMSON, font=_font_serif(42, bold=True))
    draw.text((245, n_y + 95), "Until 12:14 AM (Next Day)", fill=COLOR_MUTED, font=_font_sans(24))
    draw.text((565, n_y + 95), "•", fill=COLOR_MUTED, font=_font_sans(24))
    draw.text((590, n_y + 95), p.nakshatra_name_hi, fill=COLOR_MUTED, font=_font_hindi(22))

    # Floating Sunrise & Sunset Strip near bottom
    s_y = 1820
    draw.rounded_rectangle([75, s_y, 1005, s_y + 130], radius=24, fill=(255, 253, 248, 235), outline=COLOR_BORDER, width=2)

    # Sunrise
    _paste_icon_badge(
        canvas,
        ILLUST_DIR / "icons" / "Sunrise.webp",
        (105, s_y + 20, 185, s_y + 100),
        badge_fill=(254, 243, 220),
        padding=10,
    )
    draw.text((205, s_y + 26), "Sunrise", fill=COLOR_MUTED, font=_font_sans(22))
    draw.text((205, s_y + 60), p.sunrise_str, fill=COLOR_DARK, font=_font_sans(34, bold=True))

    # Divider
    draw.line([540, s_y + 20, 540, s_y + 105], fill=(225, 210, 190), width=2)

    # Sunset
    _paste_icon_badge(
        canvas,
        ILLUST_DIR / "icons" / "Sunset.webp",
        (570, s_y + 20, 650, s_y + 100),
        badge_fill=(254, 243, 220),
        padding=10,
    )
    draw.text((670, s_y + 26), "Sunset", fill=COLOR_MUTED, font=_font_sans(22))
    draw.text((670, s_y + 60), p.sunset_str, fill=COLOR_DARK, font=_font_sans(34, bold=True))

    # Small diamond ornament below
    cx, cy = 540, s_y + 160
    draw.polygon([(cx, cy - 8), (cx + 8, cy), (cx, cy + 8), (cx - 8, cy)], fill=COLOR_GOLD)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 2. PLAN YOUR DAY (Muhurta, Rahu Kaal and Choghadiya)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_2_plan_day(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_canvas("plan_day_template.png")
    _draw_brand_header(canvas, draw, y=70)

    # Title
    draw.text((75, 280), "Plan Your", fill=COLOR_CRIMSON, font=_font_serif(80, bold=True))
    draw.text((75, 370), "Day Wisely", fill=COLOR_CRIMSON, font=_font_serif(80, bold=True))
    draw.text((75, 480), "Auspicious timings for a more harmonious day.", fill=COLOR_MUTED, font=_font_serif(28, bold=False))

    # Card 1: Abhijit Muhurta (Green border, dark green badge with golden lotus)
    c1_y = 650
    draw.rounded_rectangle([75, c1_y, 1005, c1_y + 230], radius=24, fill=(255, 253, 248, 235), outline=(50, 130, 80), width=2)
    _paste_icon_badge(
        canvas,
        ILLUST_DIR / "icons" / "L Otus.webp",
        (110, c1_y + 40, 260, c1_y + 190),
        badge_fill=(27, 94, 56),  # Dark Emerald Green
        padding=18,
    )
    draw.text((290, c1_y + 40), "Abhijit Muhurta", fill=COLOR_GREEN, font=_font_sans(32, bold=True))
    draw.text((290, c1_y + 90), p.abhijit_muhurta, fill=COLOR_DARK, font=_font_sans(42, bold=True))
    draw.text((290, c1_y + 150), "A highly auspicious time for important work.", fill=COLOR_MUTED, font=_font_sans(24))

    # Card 2: Rahu Kaal (Crimson border, deep crimson badge with clean white X)
    c2_y = 930
    draw.rounded_rectangle([75, c2_y, 1005, c2_y + 230], radius=24, fill=(255, 253, 248, 235), outline=(200, 60, 50), width=2)
    # Badge with clean white cross
    b_cx, b_cy = 185, c2_y + 115
    draw.ellipse([110, c2_y + 40, 260, c2_y + 190], fill=(138, 28, 20))
    cr_r = 28
    draw.line([b_cx - cr_r, b_cy - cr_r, b_cx + cr_r, b_cy + cr_r], fill=WHITE, width=7)
    draw.line([b_cx - cr_r, b_cy + cr_r, b_cx + cr_r, b_cy - cr_r], fill=WHITE, width=7)

    draw.text((290, c2_y + 40), "Rahu Kaal", fill=COLOR_RED, font=_font_sans(32, bold=True))
    draw.text((290, c2_y + 90), p.rahu_kaal, fill=COLOR_DARK, font=_font_sans(42, bold=True))
    draw.text((290, c2_y + 150), "Avoid starting new important activities.", fill=COLOR_MUTED, font=_font_sans(24))

    # Card 3: Choghadiya (Amber border, amber badge with clock)
    c3_y = 1210
    draw.rounded_rectangle([75, c3_y, 1005, c3_y + 230], radius=24, fill=(255, 253, 248, 235), outline=(200, 140, 45), width=2)
    # Clock vector icon in amber badge
    draw.ellipse([110, c3_y + 40, 260, c3_y + 190], fill=(180, 115, 30))
    draw.ellipse([140, c3_y + 70, 230, c3_y + 160], outline=WHITE, width=4)
    draw.line([185, c3_y + 115, 185, c3_y + 88], fill=WHITE, width=4)
    draw.line([185, c3_y + 115, 208, c3_y + 115], fill=WHITE, width=4)

    draw.text((290, c3_y + 40), "Choghadiya (Labh)", fill=COLOR_AMBER, font=_font_sans(32, bold=True))
    draw.text((290, c3_y + 90), "7:12 AM – 8:44 AM", fill=COLOR_DARK, font=_font_sans(42, bold=True))
    draw.text((290, c3_y + 150), "Good for business, financial activities.", fill=COLOR_MUTED, font=_font_sans(24))

    # Bottom Closing Note (centered italic serif, warm brown, perfectly matching mockup)
    quote_y = 1580
    draw.rounded_rectangle([120, quote_y, 960, quote_y + 90], radius=22, fill=(255, 253, 248, 215))
    draw.text((540, quote_y + 45), "Right timing brings the right results.", fill=COLOR_CRIMSON, font=_font_serif(36, italic=True), anchor="mm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 3. FESTIVAL (Beautiful festival announcement - Navratri Begins)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_3_festival(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_canvas("plan_day_template.png")
    _draw_brand_header(canvas, draw, y=70)

    # Title
    fest_title = p.festival_name if p.is_festival and p.festival_name else "Navratri Begins"
    draw.text((75, 280), fest_title, fill=COLOR_CRIMSON, font=_font_serif(76, bold=True))
    draw.text((75, 380), "11 OCTOBER 2026", fill=COLOR_DARK, font=_font_sans(32, bold=True))
    draw.text((75, 425), "SHUKLA PAKSHA PRATIPADA", fill=COLOR_MUTED, font=_font_sans(24, bold=False))

    # Left Column: 3 Bullet Features
    b1_y = 560
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "diya.webp", (75, b1_y, 165, b1_y + 90), badge_fill=(254, 243, 220), padding=12)
    draw.text((190, b1_y + 12), "Nine nights of", fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((190, b1_y + 48), "divine devotion", fill=COLOR_MUTED, font=_font_sans(24))

    b2_y = 710
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "L Otus.webp", (75, b2_y, 165, b2_y + 90), badge_fill=(254, 243, 220), padding=12)
    draw.text((190, b2_y + 12), "Worship of", fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((190, b2_y + 48), "Maa Durga", fill=COLOR_MUTED, font=_font_sans(24))

    b3_y = 860
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "family.webp", (75, b3_y, 165, b3_y + 90), badge_fill=(254, 243, 220), padding=12)
    draw.text((190, b3_y + 6), "Fasting, prayers", fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((190, b3_y + 38), "and spiritual", fill=COLOR_MUTED, font=_font_sans(24))
    draw.text((190, b3_y + 70), "discipline", fill=COLOR_MUTED, font=_font_sans(24))

    # Right Column: Maa Durga Riding Lion Illustration
    durga_path = ILLUST_DIR / "festivals" / "durga.webp"
    if durga_path.exists():
        try:
            durga = Image.open(durga_path)
            durga = _clean_transparency(durga)
            # scale to fit height ~750
            scale = 750 / durga.height
            nw, nh = int(durga.width * scale), int(durga.height * scale)
            durga = durga.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.alpha_composite(durga, (520, 520))
        except Exception:
            pass

    # Bottom CTA Button
    _draw_cta_button(canvas, draw, "Explore all Festivals in Siddhanta", y=1920)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 4. KUNDLI (Core features with clean chart motif)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_4_kundli(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_canvas("plan_day_template.png")
    _draw_brand_header(canvas, draw, y=70)

    # Title
    draw.text((75, 280), "Your Kundli", fill=COLOR_CRIMSON, font=_font_serif(84, bold=True))
    draw.text((75, 380), "A deeper understanding of your unique journey.", fill=COLOR_MUTED, font=_font_serif(28, bold=False))

    # Center: North Indian Kundli Chart Motif
    ch_x1, ch_y1 = 150, 480
    ch_sz = 780
    ch_x2, ch_y2 = ch_x1 + ch_sz, ch_y1 + ch_sz

    # Background card for chart
    draw.rounded_rectangle([ch_x1 - 15, ch_y1 - 15, ch_x2 + 15, ch_y2 + 15], radius=24, fill=(255, 253, 248, 240), outline=(210, 175, 120), width=3)
    draw.rectangle([ch_x1, ch_y1, ch_x2, ch_y2], outline=(200, 160, 100), width=2)

    # Diagonals
    draw.line([ch_x1, ch_y1, ch_x2, ch_y2], fill=(200, 160, 100), width=2)
    draw.line([ch_x1, ch_y2, ch_x2, ch_y1], fill=(200, 160, 100), width=2)

    # Inner Diamond
    mid_x = (ch_x1 + ch_x2) // 2
    mid_y = (ch_y1 + ch_y2) // 2
    draw.polygon([(mid_x, ch_y1), (ch_x2, mid_y), (mid_x, ch_y2), (ch_x1, mid_y)], outline=(200, 160, 100), width=2)

    # Central Ascendant circle
    draw.ellipse([mid_x - 55, mid_y - 55, mid_x + 55, mid_y + 55], fill=(254, 243, 220), outline=(210, 175, 120), width=2)
    draw.text((mid_x, mid_y), "Asc", fill=COLOR_CRIMSON, font=_font_serif(34, bold=True), anchor="mm")

    # House Numbers & Planets
    f_p = _font_serif(36, bold=True)
    f_num = _font_sans(22, bold=False)

    # House 1 (top center diamond)
    draw.text((mid_x, mid_y - 120), "1", fill=COLOR_MUTED, font=f_num, anchor="mm")

    # House 2
    draw.text((ch_x1 + 270, ch_y1 + 90), "2", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x1 + 160, ch_y1 + 130), "Ju", fill=(160, 82, 45), font=f_p)

    # House 12
    draw.text((ch_x2 - 290, ch_y1 + 90), "12", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x2 - 180, ch_y1 + 130), "Ma", fill=COLOR_CRIMSON, font=f_p)

    # House 4
    draw.text((ch_x1 + 230, mid_y), "4", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x1 + 90, mid_y), "Sa", fill=(30, 60, 140), font=f_p)

    # House 10
    draw.text((ch_x2 - 250, mid_y), "10", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x2 - 100, mid_y), "Ve", fill=(34, 139, 34), font=f_p)

    # House 7 (bottom diamond)
    draw.text((mid_x, ch_y2 - 130), "7", fill=COLOR_MUTED, font=f_num, anchor="mm")
    draw.text((ch_x1 + 170, ch_y2 - 150), "Me", fill=(34, 139, 34), font=f_p)
    draw.text((ch_x2 - 170, ch_y2 - 150), "Mo", fill=(25, 25, 112), font=f_p)

    # 4 Feature Badges in a Row below Chart
    b_y = 1350
    badge_w = 210
    badge_h = 240
    badges_data = [
        ("D1", "Lagna Chart", "icons/kundli.webp"),
        ("D9", "Navamsha", "icons/Vargas.webp"),
        ("Dashas", "Vimshottari", "icons/Overview.webp"),
        ("Yogas", "Key combinations", "icons/yogas.webp"),
    ]

    for i, (b_title, b_sub, b_icon) in enumerate(badges_data):
        bx = 75 + i * (badge_w + 25)
        draw.rounded_rectangle([bx, b_y, bx + badge_w, b_y + badge_h], radius=20, fill=(255, 253, 248, 235), outline=COLOR_BORDER, width=2)
        _paste_icon_badge(canvas, ILLUST_DIR / b_icon, (bx + 55, b_y + 25, bx + 155, b_y + 125), badge_fill=(254, 243, 220), padding=12)
        draw.text((bx + badge_w // 2, b_y + 150), b_title, fill=COLOR_CRIMSON, font=_font_sans(26, bold=True), anchor="mm")
        draw.text((bx + badge_w // 2, b_y + 190), b_sub, fill=COLOR_MUTED, font=_font_sans(19), anchor="mm")

    # Bottom CTA Button
    _draw_cta_button(canvas, draw, "Create Your Kundli in Siddhanta", y=1920)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 5. CHAKRA (Balance Your Inner Energy - 7 Chakras)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_5_chakra(output_path: str | Path) -> str:
    canvas, draw = _prepare_canvas("plan_day_template.png")
    _draw_brand_header(canvas, draw, y=70)

    # Title
    draw.text((75, 280), "Balance Your", fill=COLOR_CRIMSON, font=_font_serif(80, bold=True))
    draw.text((75, 370), "Inner Energy", fill=COLOR_CRIMSON, font=_font_serif(80, bold=True))
    draw.text((75, 480), "Explore your 7 chakras for a healthier, more harmonious life.", fill=COLOR_MUTED, font=_font_serif(26, bold=False))

    # Top Right Circular Gauge: Overall Chakra Balance (75% Balanced)
    g_cx, g_cy = 820, 680
    g_r = 100
    draw.text((g_cx, g_cy - 145), "Overall", fill=COLOR_DARK, font=_font_sans(24, bold=True), anchor="mm")
    draw.text((g_cx, g_cy - 115), "Chakra Balance", fill=COLOR_DARK, font=_font_sans(24, bold=True), anchor="mm")

    # Gauge ring
    draw.ellipse([g_cx - g_r, g_cy - g_r, g_cx + g_r, g_cy + g_r], outline=(230, 220, 205), width=18)
    draw.arc([g_cx - g_r, g_cy - g_r, g_cx + g_r, g_cy + g_r], start=-90, end=180, fill=(46, 139, 87), width=18)
    draw.arc([g_cx - g_r, g_cy - g_r, g_cx + g_r, g_cy + g_r], start=180, end=240, fill=(218, 140, 30), width=18)
    draw.text((g_cx, g_cy), "75%", fill=COLOR_DARK, font=_font_sans(46, bold=True), anchor="mm")
    draw.text((g_cx, g_cy + 135), "Balanced", fill=COLOR_DARK, font=_font_sans(26, bold=True), anchor="mm")

    # Center: Meditating Yogi with glowing 7 chakras
    yogi_path = IMAGES_DIR / "chakra_meditating.webp"
    if yogi_path.exists():
        try:
            yogi = Image.open(yogi_path)
            yogi = _clean_transparency(yogi)
            scale = 880 / yogi.height
            nw, nh = int(yogi.width * scale), int(yogi.height * scale)
            yogi = yogi.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.alpha_composite(yogi, (60, 680))
        except Exception:
            pass

    # Right Column: 7 Chakras List
    chakras = [
        ("Sahasrara", (153, 50, 204)),
        ("Ajna", (65, 105, 225)),
        ("Vishuddha", (0, 191, 255)),
        ("Anahata", (46, 139, 87)),
        ("Manipura", (230, 175, 20)),
        ("Svadhisthana", (255, 127, 80)),
        ("Muladhara", (220, 20, 60)),
    ]

    list_x = 730
    list_y = 920
    draw.rounded_rectangle([list_x - 30, list_y - 25, 1005, list_y + 440], radius=20, fill=(255, 253, 248, 235), outline=COLOR_BORDER, width=2)

    for i, (name, col) in enumerate(chakras):
        cy = list_y + i * 58
        draw.ellipse([list_x - 10, cy + 4, list_x + 22, cy + 36], fill=col)
        draw.text((list_x + 42, cy + 6), name, fill=COLOR_DARK, font=_font_sans(24, bold=True))

    # Bottom CTA Button
    _draw_cta_button(canvas, draw, "Explore Your Chakras in Siddhanta", y=1920)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 6. JYOTISH INSIGHT (Jupiter Transit / Planetary Movements)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_6_jyotish(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_canvas("transit_template.png")
    _draw_brand_header(canvas, draw, y=70)

    # Pill badge
    draw.rounded_rectangle([75, 270, 350, 325], radius=14, fill=(255, 248, 235), outline=(220, 190, 140), width=2)
    draw.text((212, 297), "JYOTISH INSIGHT", fill=COLOR_GOLD, font=_font_sans(24, bold=True), anchor="mm")

    # Title
    jup_sign = p.gochar.jupiter_sign.split()[0] if p.gochar else "Gemini"
    draw.text((75, 360), "Jupiter Transit", fill=COLOR_CRIMSON, font=_font_serif(76, bold=True))
    draw.text((75, 450), f"in {jup_sign}", fill=COLOR_CRIMSON, font=_font_serif(76, bold=True))
    draw.text((75, 555), "14 MAY 2026 – 1 JUNE 2027", fill=COLOR_DARK, font=_font_sans(30, bold=True))

    # Right side: Zodiac Gemini Symbol in Gold Circle
    draw.ellipse([860, 360, 980, 480], fill=(254, 243, 220), outline=(210, 175, 120), width=3)
    # Classical Roman II for Gemini
    draw.text((920, 420), "II", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True), anchor="mm")

    # Left Column: 3 Bullet Points with Amber Badges
    b1_y = 670
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Overview.webp", (75, b1_y, 165, b1_y + 90), badge_fill=(254, 243, 220), padding=12)
    draw.text((190, b1_y + 8), "Brings expansion in knowledge", fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((190, b1_y + 46), "and communication for seekers", fill=COLOR_MUTED, font=_font_sans(24))

    b2_y = 820
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "family.webp", (75, b2_y, 165, b2_y + 90), badge_fill=(254, 243, 220), padding=12)
    favs = ", ".join(p.gochar.favorable_rashis[:2]) if p.gochar else "Vrishabha, Mithuna"
    draw.text((190, b2_y + 8), f"Favors learning & research: {favs}", fill=COLOR_GREEN, font=_font_sans(28, bold=True))
    draw.text((190, b2_y + 46), "Positive momentum & new perspectives", fill=COLOR_MUTED, font=_font_sans(24))

    b3_y = 970
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "strength.webp", (75, b3_y, 165, b3_y + 90), badge_fill=(254, 243, 220), padding=12)
    draw.text((190, b3_y + 8), "Good time for teaching, writing", fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((190, b3_y + 46), "and intellectual growth", fill=COLOR_MUTED, font=_font_sans(24))

    # Quote Card: Soft cream container with border
    q_y = 1250
    draw.rounded_rectangle([75, q_y, 750, q_y + 170], radius=20, fill=(255, 253, 248, 235), outline=COLOR_BORDER, width=2)
    draw.text((115, q_y + 35), "“When Guru moves, wisdom", fill=COLOR_CRIMSON, font=_font_serif(30, italic=True))
    draw.text((115, q_y + 85), "finds a new direction.”", fill=COLOR_CRIMSON, font=_font_serif(30, italic=True))

    # Small diamond ornament below card
    cx, cy = 412, q_y + 205
    draw.polygon([(cx, cy - 8), (cx + 8, cy), (cx, cy + 8), (cx - 8, cy)], fill=COLOR_GOLD)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)
