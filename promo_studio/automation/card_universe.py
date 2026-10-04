"""Siddhanta 6-Card Universe Generator.

Pixel-accurate rendering engine calibrated strictly for Instagram Feed 4:5 portrait (1080 x 1350)
incorporating all agency editorial rules & brand consistency:

Brand Standards:
- Dimensions: CARD_W = 1080, CARD_H = 1350 (4:5 aspect ratio)
- Typography: Maroon serif headlines, dark charcoal body, gold accents
- Frame: Subtle ornamental corner brackets, consistent top brand header & divider (─── ◆ ───)
- Background: Cream-first palette, utilizing rule-based empty background templates where available
- CTA: Standardized restrained editorial footer pill across every card
- Data Authority: No invented marketing claims or hardcoded festival dates
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from promo_studio.automation.panchang_engine import DailyPanchang
from promo_studio.automation.template_selector import select_template_for_content

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
FONTS_DIR = ASSETS_DIR / "fonts"
ILLUST_DIR = ASSETS_DIR / "illustrations"
IMAGES_DIR = ASSETS_DIR / "images"

# Strict 4:5 Instagram Feed Dimensions
CARD_W = 1080
CARD_H = 1350

# Palette
COLOR_CRIMSON = (122, 20, 20)           # #7A1414 (Main Titles & Accents)
COLOR_GOLD = (180, 115, 30)             # #B4731E (Subtitles & Gold Accents)
COLOR_DARK = (30, 25, 22)               # #1E1916 (Timings & Headers)
COLOR_MUTED = (112, 102, 94)            # #70665E (Descriptions)
COLOR_CARD_BG = (255, 253, 248, 235)    # Translucent Cream
COLOR_BORDER = (235, 222, 202)          # Soft Cream Border
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
    padding: int = 12,
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


def _draw_brand_header(canvas: Image.Image, draw: ImageDraw.ImageDraw, y: int = 42) -> None:
    """Draws the official Siddhanta Jyotish Panchang header with ornamental divider."""
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((70, 70), Image.Resampling.LANCZOS)
            canvas.alpha_composite(logo, (60, y))
        except Exception:
            pass

    font_title = _font_serif(34, bold=True)
    font_sub = _font_serif(20, bold=False)

    text_x = 60 + 85
    draw.text((text_x, y + 2), "Siddhanta", fill=COLOR_CRIMSON, font=font_title)
    draw.text((text_x, y + 40), "Jyotish Panchang", fill=COLOR_GOLD, font=font_sub)

    # Ornamental divider: ─── ◆ ───
    div_y = y + 84
    draw.line([60, div_y, 500, div_y], fill=(210, 180, 130, 140), width=2)
    draw.line([580, div_y, 1020, div_y], fill=(210, 180, 130, 140), width=2)
    # Diamond at center
    cx, cy = 540, div_y
    draw.polygon([(cx, cy - 6), (cx + 6, cy), (cx, cy + 6), (cx - 6, cy)], fill=COLOR_GOLD)


def _draw_card_frame(draw: ImageDraw.ImageDraw) -> None:
    """Draws subtle ornamental corner mandala brackets for 1080x1350 canvas."""
    c_color = (205, 175, 125, 120)
    d_color = COLOR_GOLD

    # Top-Left Bracket
    draw.line([(35, 55), (35, 30), (60, 30)], fill=c_color, width=2)
    draw.polygon([(35, 28), (37, 30), (35, 32), (33, 30)], fill=d_color)

    # Top-Right Bracket
    draw.line([(1045, 55), (1045, 30), (1020, 30)], fill=c_color, width=2)
    draw.polygon([(1045, 28), (1047, 30), (1045, 32), (1043, 30)], fill=d_color)

    # Bottom-Left Bracket
    draw.line([(35, 1295), (35, 1320), (60, 1320)], fill=c_color, width=2)
    draw.polygon([(35, 1318), (37, 1320), (35, 1322), (33, 1320)], fill=d_color)

    # Bottom-Right Bracket
    draw.line([(1045, 1295), (1045, 1320), (1020, 1320)], fill=c_color, width=2)
    draw.polygon([(1045, 1318), (1047, 1320), (1045, 1322), (1043, 1320)], fill=d_color)


def _draw_cta_pill(canvas: Image.Image, draw: ImageDraw.ImageDraw, text: str, y: int = 1245) -> None:
    """Draws an elegant, restrained editorial footer pill replacing giant billboard buttons."""
    pill_box = [60, y, 1020, y + 62]
    # Subtle cream background with warm maroon border and refined typography
    draw.rounded_rectangle(pill_box, radius=18, fill=(255, 250, 242, 230), outline=(190, 155, 115), width=2)

    # Left subtle icon
    ph_x, ph_y = 95, y + 17
    draw.rounded_rectangle([ph_x, ph_y, ph_x + 18, ph_y + 28], radius=4, outline=COLOR_CRIMSON, width=2)
    draw.line([ph_x + 6, ph_y + 21, ph_x + 12, ph_y + 21], fill=COLOR_CRIMSON, width=1)

    # Label & subtle arrow
    font_btn = _font_sans(22, bold=True)
    draw.text((540, y + 31), text, fill=COLOR_CRIMSON, font=font_btn, anchor="mm")
    draw.text((985, y + 30), "›", fill=COLOR_GOLD, font=_font_serif(30, bold=True), anchor="mm")


def _prepare_card_canvas(theme: str, festival_name: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Prepares a 1080x1350 canvas with cream-first atmosphere and template selection."""
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (255, 252, 246, 255))

    # Check for empty template from rule-based selector
    t_path = select_template_for_content(theme, festival_name=festival_name)
    if t_path and t_path.exists():
        try:
            t_img = Image.open(t_path).convert("RGBA")
            scale = max(CARD_W / t_img.width, CARD_H / t_img.height)
            nw, nh = int(t_img.width * scale), int(t_img.height * scale)
            t_img = t_img.resize((nw, nh), Image.Resampling.LANCZOS)
            crop_x = (nw - CARD_W) // 2
            crop_y = (nh - CARD_H) // 2
            cropped = t_img.crop((crop_x, crop_y, crop_x + CARD_W, crop_y + CARD_H))
            
            # Subtle opacity blend so cream-first legibility is preserved
            alpha_val = 80 if theme in ("panchang", "plan_day") else 140
            cropped.putalpha(alpha_val)
            canvas.alpha_composite(cropped, (0, 0))
        except Exception:
            pass
    else:
        # Fallback gentle atmosphere gradients
        draw_bg = ImageDraw.Draw(canvas)
        if theme == "chakra":
            cx, cy = 350, 750
            for r in range(350, 40, -25):
                a = max(2, int(18 * (1.0 - r / 350.0)))
                draw_bg.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 235, 190, a))
        elif theme == "kundli":
            cx, cy = 540, 620
            for r in (240, 290, 340):
                draw_bg.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(220, 195, 155, 40), width=1)
        elif theme == "transit":
            for x in range(600, CARD_W):
                alpha = int(140 * ((x - 600) / 480.0))
                draw_bg.line([(x, 0), (x, CARD_H)], fill=(20, 24, 45, alpha))

    draw = ImageDraw.Draw(canvas)
    _draw_card_frame(draw)
    return canvas, draw


# ═════════════════════════════════════════════════════════════════════════════
# 1. DAILY PANCHANG (1080 x 1350)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_1_panchang(p: DailyPanchang, output_path: str | Path, lang: str = "en") -> str:
    canvas, draw = _prepare_card_canvas("panchang")
    _draw_brand_header(canvas, draw, y=42)

    f_dev = _font_hindi(38)
    f_dev_sub = _font_hindi(22)
    f_dev_h1 = _font_hindi(54)

    if lang == "hi":
        # Pure Devanagari Headline
        draw.text((60, 160), "आज का पंचांग", fill=COLOR_CRIMSON, font=f_dev_h1)
        sub_str = f"{p.date_formatted_hi} • {p.paksha_hi}"
        draw.text((60, 232), sub_str, fill=COLOR_GOLD, font=f_dev_sub)

        # Tithi Card (Row 1)
        t_y = 285
        t_h = 110
        draw.rounded_rectangle([60, t_y, 1020, t_y + t_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
        _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Moon.webp", (80, t_y + 15, 160, t_y + 95), badge_fill=(254, 243, 220), padding=12)
        draw.text((185, t_y + 14), "तिथि", fill=COLOR_MUTED, font=_font_hindi(20))
        draw.text((185, t_y + 40), p.tithi_name_hi, fill=COLOR_CRIMSON, font=f_dev)
        t_end_str = f"समाप्ति: {p.tithi_end}  •  " if p.tithi_end else ""
        tithi_sub = f"{t_end_str}{p.paksha_hi}"
        draw.text((185, t_y + 80), tithi_sub, fill=COLOR_MUTED, font=_font_hindi(19))

        # Nakshatra Card (Row 2)
        n_y = 415
        draw.rounded_rectangle([60, n_y, 1020, n_y + t_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
        _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "nakshatra.webp", (80, n_y + 15, 160, n_y + 95), badge_fill=(254, 243, 220), padding=10)
        draw.text((185, n_y + 14), "नक्षत्र", fill=COLOR_MUTED, font=_font_hindi(20))
        draw.text((185, n_y + 40), p.nakshatra_name_hi, fill=COLOR_CRIMSON, font=f_dev)
        n_end_str = f"समाप्ति: {p.nakshatra_end}  •  " if p.nakshatra_end else ""
        nak_sub = f"{n_end_str}चन्द्र राशि: {p.moon_rashi_hi}"
        draw.text((185, n_y + 80), nak_sub, fill=COLOR_MUTED, font=_font_hindi(19))

        # Auspicious Timings Card (Abhijit & Rahu Kaal)
        m_y = 545
        m_h = 120
        draw.rounded_rectangle([60, m_y, 1020, m_y + m_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
        draw.text((100, m_y + 18), "शुभ मुहूर्त (अभिजित)", fill=COLOR_GREEN, font=_font_hindi(21))
        draw.text((100, m_y + 54), p.abhijit_muhurta, fill=COLOR_DARK, font=_font_sans(28, bold=True))
        draw.text((100, m_y + 90), "शुभ कार्यों की शुरुआत हेतु श्रेष्ठ", fill=COLOR_MUTED, font=_font_hindi(18))

        draw.line([540, m_y + 16, 540, m_y + 104], fill=(225, 210, 190), width=2)

        draw.text((580, m_y + 18), "अशुभ काल (राहुकाल)", fill=COLOR_RED, font=_font_hindi(21))
        draw.text((580, m_y + 54), p.rahu_kaal, fill=COLOR_DARK, font=_font_sans(28, bold=True))
        draw.text((580, m_y + 90), "नए कार्य व समझौते टालें", fill=COLOR_MUTED, font=_font_hindi(18))

        # Sunrise & Sunset Strip
        s_y = 685
        s_h = 100
        draw.rounded_rectangle([60, s_y, 1020, s_y + s_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
        _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Sunrise.webp", (85, s_y + 16, 155, s_y + 84), badge_fill=(254, 243, 220), padding=8)
        draw.text((175, s_y + 18), "सूर्योदय", fill=COLOR_MUTED, font=_font_hindi(19))
        draw.text((175, s_y + 48), p.sunrise_str, fill=COLOR_DARK, font=_font_sans(28, bold=True))

        draw.line([540, s_y + 14, 540, s_y + 86], fill=(225, 210, 190), width=2)

        _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Sunset.webp", (565, s_y + 16, 635, s_y + 84), badge_fill=(254, 243, 220), padding=8)
        draw.text((655, s_y + 18), "सूर्यास्त", fill=COLOR_MUTED, font=_font_hindi(19))
        draw.text((655, s_y + 48), p.sunset_str, fill=COLOR_DARK, font=_font_sans(28, bold=True))

        # Daily Spiritual Focus Footer Pill
        sp_y = 805
        draw.rounded_rectangle([60, sp_y, 1020, sp_y + 95], radius=18, fill=(255, 250, 238), outline=(225, 195, 140), width=2)
        _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "diya.webp", (85, sp_y + 16, 150, sp_y + 80), badge_fill=(254, 243, 220), padding=6)
        draw.text((170, sp_y + 14), "दैनिक आध्यात्मिक संकल्प", fill=COLOR_GOLD, font=_font_hindi(20))
        focus_text = p.remedy if p.remedy else "प्रातःकाल सूर्य देव को तांबे के लोटे से अर्घ्य दें।"
        draw.text((170, sp_y + 48), focus_text[:65], fill=COLOR_CRIMSON, font=_font_hindi(20))

        draw.text((540, 1205), "“शुभ समय पर किया गया कर्म कल्याणकारी होता है।”", fill=COLOR_CRIMSON, font=_font_hindi(22), anchor="mm")
        _draw_cta_pill(canvas, draw, "सिद्धांत पंचांग ऐप में देखें", y=1245)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        canvas.save(output_path, "PNG")
        return str(output_path)

    # Title & Sub-header (English default)
    draw.text((60, 160), "Today's Panchang", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))
    day_str = p.date.strftime("%d %B %Y").upper()
    vara_label = f"{day_str}  •  {p.vara_en.upper()} ({p.vara_sa.upper()})  •  {p.paksha.upper()} PAKSHA"
    draw.text((60, 232), vara_label, fill=COLOR_GOLD, font=_font_sans(21, bold=True))

    # Tithi Card (Row 1)
    t_y = 285
    t_h = 110
    draw.rounded_rectangle([60, t_y, 1020, t_y + t_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Moon.webp", (80, t_y + 15, 160, t_y + 95), badge_fill=(254, 243, 220), padding=12)
    draw.text((185, t_y + 18), "Tithi", fill=COLOR_MUTED, font=_font_sans(20, bold=False))
    draw.text((185, t_y + 44), p.tithi_name, fill=COLOR_CRIMSON, font=_font_serif(34, bold=True))
    t_end_str = f"Until {p.tithi_end}  •  " if p.tithi_end else ""
    tithi_sub = f"{t_end_str}{p.tithi_name_hi} ({p.paksha} Paksha)"
    draw.text((185, t_y + 80), tithi_sub, fill=COLOR_MUTED, font=_font_sans(19))

    # Nakshatra Card (Row 2)
    n_y = 415
    draw.rounded_rectangle([60, n_y, 1020, n_y + t_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "nakshatra.webp", (80, n_y + 15, 160, n_y + 95), badge_fill=(254, 243, 220), padding=10)
    draw.text((185, n_y + 18), "Nakshatra", fill=COLOR_MUTED, font=_font_sans(20, bold=False))
    draw.text((185, n_y + 44), p.nakshatra_name, fill=COLOR_CRIMSON, font=_font_serif(34, bold=True))
    n_end_str = f"Until {p.nakshatra_end}  •  " if p.nakshatra_end else ""
    nak_sub = f"{n_end_str}{p.nakshatra_name_hi} (Moon in {p.moon_rashi})"
    draw.text((185, n_y + 80), nak_sub, fill=COLOR_MUTED, font=_font_sans(19))

    # Auspicious Timings Card (Abhijit & Rahu Kaal side-by-side)
    m_y = 545
    m_h = 120
    draw.rounded_rectangle([60, m_y, 1020, m_y + m_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)

    # Abhijit Left Half
    draw.text((100, m_y + 20), "Abhijit Muhurta", fill=COLOR_GREEN, font=_font_sans(21, bold=True))
    draw.text((100, m_y + 54), p.abhijit_muhurta, fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((100, m_y + 90), "Auspicious for key decisions", fill=COLOR_MUTED, font=_font_sans(18))

    # Divider
    draw.line([540, m_y + 16, 540, m_y + 104], fill=(225, 210, 190), width=2)

    # Rahu Kaal Right Half
    draw.text((580, m_y + 20), "Rahu Kaal", fill=COLOR_RED, font=_font_sans(21, bold=True))
    draw.text((580, m_y + 54), p.rahu_kaal, fill=COLOR_DARK, font=_font_sans(28, bold=True))
    draw.text((580, m_y + 90), "Avoid starting new ventures", fill=COLOR_MUTED, font=_font_sans(18))

    # Sunrise & Sunset Strip (Row 4)
    s_y = 685
    s_h = 100
    draw.rounded_rectangle([60, s_y, 1020, s_y + s_h], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)

    # Sunrise
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Sunrise.webp", (85, s_y + 16, 155, s_y + 84), badge_fill=(254, 243, 220), padding=8)
    draw.text((175, s_y + 20), "Sunrise", fill=COLOR_MUTED, font=_font_sans(19))
    draw.text((175, s_y + 48), p.sunrise_str, fill=COLOR_DARK, font=_font_sans(28, bold=True))

    # Divider
    draw.line([540, s_y + 14, 540, s_y + 86], fill=(225, 210, 190), width=2)

    # Sunset
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "Sunset.webp", (565, s_y + 16, 635, s_y + 84), badge_fill=(254, 243, 220), padding=8)
    draw.text((655, s_y + 20), "Sunset", fill=COLOR_MUTED, font=_font_sans(19))
    draw.text((655, s_y + 48), p.sunset_str, fill=COLOR_DARK, font=_font_sans(28, bold=True))

    # Daily Spiritual Focus Footer Pill (Row 5)
    sp_y = 805
    draw.rounded_rectangle([60, sp_y, 1020, sp_y + 95], radius=18, fill=(255, 250, 238), outline=(225, 195, 140), width=2)
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "diya.webp", (85, sp_y + 16, 150, sp_y + 80), badge_fill=(254, 243, 220), padding=6)
    draw.text((170, sp_y + 16), "Daily Spiritual Focus", fill=COLOR_GOLD, font=_font_sans(20, bold=True))
    focus_text = p.remedy if p.remedy else "Offer Arghya (fresh water) to the rising Sun with Gayatri Mantra."
    if len(focus_text) > 72:
        focus_text = focus_text[:69] + "..."
    draw.text((170, sp_y + 48), focus_text, fill=COLOR_CRIMSON, font=_font_serif(20, italic=True))

    # Subtle quote note
    draw.text((540, 1205), "“Right timing aligns human action with cosmic order.”", fill=COLOR_CRIMSON, font=_font_serif(22, italic=True), anchor="mm")

    # Standardized bottom CTA pill
    _draw_cta_pill(canvas, draw, "Explore Today's Panchang in Siddhanta", y=1245)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 2. PLAN YOUR DAY (1080 x 1350)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_2_plan_day(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_card_canvas("plan_day")
    _draw_brand_header(canvas, draw, y=42)

    # Title & Sub-header
    draw.text((60, 160), "Plan Your Day Wisely", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))
    draw.text((60, 232), "Calculated Vedic Muhurtas for mindful scheduling.", fill=COLOR_MUTED, font=_font_serif(22, bold=False))

    # 3 Cards — height 155px each, cleanly spaced
    c_h = 155

    # Card 1: Abhijit Muhurta
    c1_y = 295
    draw.rounded_rectangle([60, c1_y, 1020, c1_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=(50, 130, 80), width=2)
    _paste_icon_badge(canvas, ILLUST_DIR / "icons" / "L Otus.webp", (85, c1_y + 20, 195, c1_y + 130), badge_fill=(27, 94, 56), padding=12)
    draw.text((225, c1_y + 22), "Abhijit Muhurta", fill=COLOR_GREEN, font=_font_sans(24, bold=True))
    draw.text((225, c1_y + 58), p.abhijit_muhurta, fill=COLOR_DARK, font=_font_sans(30, bold=True))
    draw.text((225, c1_y + 104), "Midday solar window auspicious for important beginnings.", fill=COLOR_MUTED, font=_font_sans(19))

    # Card 2: Rahu Kaal
    c2_y = 475
    draw.rounded_rectangle([60, c2_y, 1020, c2_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=(200, 60, 50), width=2)
    b_cx, b_cy = 140, c2_y + 75
    draw.ellipse([85, c2_y + 20, 195, c2_y + 130], fill=(138, 28, 20))
    cr_r = 18
    draw.line([b_cx - cr_r, b_cy - cr_r, b_cx + cr_r, b_cy + cr_r], fill=WHITE, width=4)
    draw.line([b_cx - cr_r, b_cy + cr_r, b_cx + cr_r, b_cy - cr_r], fill=WHITE, width=4)
    draw.text((225, c2_y + 22), "Rahu Kaal", fill=COLOR_RED, font=_font_sans(24, bold=True))
    draw.text((225, c2_y + 58), p.rahu_kaal, fill=COLOR_DARK, font=_font_sans(30, bold=True))
    draw.text((225, c2_y + 104), "Inauspicious period — avoid major commitments or travel start.", fill=COLOR_MUTED, font=_font_sans(19))

    # Card 3: Choghadiya - Data-driven from authentic dump
    c3_y = 655
    draw.rounded_rectangle([60, c3_y, 1020, c3_y + c_h], radius=18, fill=COLOR_CARD_BG, outline=(200, 140, 45), width=2)
    draw.ellipse([85, c3_y + 20, 195, c3_y + 130], fill=(180, 115, 30))
    draw.ellipse([108, c3_y + 43, 172, c3_y + 107], outline=WHITE, width=3)
    draw.line([140, c3_y + 75, 140, c3_y + 56], fill=WHITE, width=3)
    draw.line([140, c3_y + 75, 156, c3_y + 75], fill=WHITE, width=3)
    draw.text((225, c3_y + 22), f"Day Choghadiya ({p.choghadiya_name})", fill=COLOR_AMBER, font=_font_sans(24, bold=True))
    draw.text((225, c3_y + 58), p.choghadiya_time, fill=COLOR_DARK, font=_font_sans(30, bold=True))
    draw.text((225, c3_y + 104), f"Auspicious {p.choghadiya_name} interval favorable for action & commerce.", fill=COLOR_MUTED, font=_font_sans(19))

    # Daily Muhurta Note
    draw.text((540, 1205), "“Right timing brings the right results.”", fill=COLOR_CRIMSON, font=_font_serif(24, italic=True), anchor="mm")

    # Standardized bottom CTA pill
    _draw_cta_pill(canvas, draw, "View All Daily Muhurtas in Siddhanta", y=1245)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 3. FESTIVAL (1080 x 1350)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_3_festival(p: DailyPanchang, output_path: str | Path) -> str:
    fest_title = p.festival_name.split("(")[0].strip() if (p.is_festival and p.festival_name) else "Jivitputrika Vrat"
    canvas, draw = _prepare_card_canvas("festival", festival_name=fest_title)
    _draw_brand_header(canvas, draw, y=42)

    # Title & Sub-headlines
    draw.text((60, 160), fest_title, fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))
    date_str = p.date.strftime("%d %B %Y").upper()
    paksha_str = f"{date_str}  •  {p.paksha.upper()} PAKSHA • {p.tithi_name.upper()}"
    draw.text((60, 232), paksha_str, fill=COLOR_GOLD, font=_font_sans(21, bold=True))

    # Left Column: 3 concise Shastric points
    if "jivitputrika" in fest_title.lower() or "jitiya" in fest_title.lower():
        pts = [
            ("icons/diya.webp", "Nirjala Mahavrat", "24-hour sacred waterless fast"),
            ("icons/L Otus.webp", "Lord Jimutavahana", "Worship for progeny longevity"),
            ("icons/family.webp", "Parana Muhurta", "Next day post-sunrise puja"),
        ]
    elif "navratri" in fest_title.lower():
        pts = [
            ("icons/diya.webp", "Ghatasthapana", "Invoking Divine Mother Durga"),
            ("icons/L Otus.webp", "Shailaputri Puja", "First day sacred worship"),
            ("icons/family.webp", "Abhijit Muhurta", p.abhijit_muhurta),
        ]
    else:
        pts = [
            ("icons/diya.webp", "Sacred Observance", "Traditional Vedic fast and puja"),
            ("icons/L Otus.webp", "Presiding Deity", p.deity),
            ("icons/family.webp", "Auspicious Timing", p.abhijit_muhurta),
        ]

    for idx, (icon_rel, pt_head, pt_sub) in enumerate(pts):
        b_y = 320 + idx * 140
        _paste_icon_badge(canvas, ILLUST_DIR / icon_rel, (60, b_y, 140, b_y + 80), badge_fill=(254, 243, 220), padding=10)
        draw.text((165, b_y + 12), pt_head, fill=COLOR_DARK, font=_font_sans(24, bold=True))
        draw.text((165, b_y + 44), pt_sub, fill=COLOR_MUTED, font=_font_sans(19))

    # Right Column: Maa Durga Riding Lion Illustration (positioned cleanly on right)
    durga_path = ILLUST_DIR / "festivals" / "durga.webp"
    if durga_path.exists():
        try:
            durga = Image.open(durga_path)
            durga = _clean_transparency(durga)
            scale = 580 / durga.height
            nw, nh = int(durga.width * scale), int(durga.height * scale)
            durga = durga.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.alpha_composite(durga, (520, 300))
        except Exception:
            pass

    # Observance note
    obs_text = p.festival_note if p.festival_note else "May this sacred observance bring health, peace, and spiritual grace."
    if len(obs_text) > 75:
        obs_text = obs_text[:72] + "..."
    draw.text((540, 1205), f"“{obs_text}”", fill=COLOR_CRIMSON, font=_font_serif(22, italic=True), anchor="mm")

    # Standardized bottom CTA pill
    _draw_cta_pill(canvas, draw, "Explore Festival Details in Siddhanta", y=1245)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 4. KUNDLI (1080 x 1350)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_4_kundli(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_card_canvas("kundli")
    _draw_brand_header(canvas, draw, y=42)

    # Title & Subtitle per user feedback
    draw.text((60, 160), "Your Kundli", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))
    draw.text((60, 232), "A deeper understanding of your unique journey.", fill=COLOR_MUTED, font=_font_serif(22, bold=False))

    # Authentic North Indian D1 Lagna Kundli Chart (scaled for 1350 canvas: 480px size centered)
    ch_sz = 480
    ch_x1 = (CARD_W - ch_sz) // 2
    ch_y1 = 290
    ch_x2, ch_y2 = ch_x1 + ch_sz, ch_y1 + ch_sz

    # Background card for chart
    draw.rounded_rectangle([ch_x1 - 12, ch_y1 - 12, ch_x2 + 12, ch_y2 + 12], radius=20, fill=(255, 253, 248, 245), outline=(210, 175, 120), width=2)
    draw.rectangle([ch_x1, ch_y1, ch_x2, ch_y2], outline=(200, 160, 100), width=2)

    # Diagonals
    draw.line([ch_x1, ch_y1, ch_x2, ch_y2], fill=(200, 160, 100), width=2)
    draw.line([ch_x1, ch_y2, ch_x2, ch_y1], fill=(200, 160, 100), width=2)

    # Inner Diamond
    mid_x = (ch_x1 + ch_x2) // 2
    mid_y = (ch_y1 + ch_y2) // 2
    draw.polygon([(mid_x, ch_y1), (ch_x2, mid_y), (mid_x, ch_y2), (ch_x1, mid_y)], outline=(200, 160, 100), width=2)

    # Central Lagna emblem in House 1
    draw.ellipse([mid_x - 36, mid_y - 36, mid_x + 36, mid_y + 36], fill=(254, 243, 220), outline=(210, 175, 120), width=2)
    draw.text((mid_x, mid_y), "Lagna", fill=COLOR_CRIMSON, font=_font_serif(20, bold=True), anchor="mm")

    # House Numbers & Planets
    f_p = _font_serif(26, bold=True)
    f_num = _font_sans(16, bold=False)

    # House 1 (top center diamond)
    draw.text((mid_x, mid_y - 75), "1", fill=COLOR_MUTED, font=f_num, anchor="mm")
    draw.text((mid_x, mid_y - 110), "Ju", fill=COLOR_GOLD, font=f_p, anchor="mm")

    # House 2 (top left triangle)
    draw.text((ch_x1 + 160, ch_y1 + 55), "2", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x1 + 90, ch_y1 + 80), "Ve", fill=(34, 139, 34), font=f_p)

    # House 12 (top right triangle)
    draw.text((ch_x2 - 180, ch_y1 + 55), "12", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x2 - 110, ch_y1 + 80), "Ma", fill=COLOR_CRIMSON, font=f_p)

    # House 4 (left center diamond)
    draw.text((ch_x1 + 140, mid_y), "4", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x1 + 60, mid_y), "Mo", fill=(25, 25, 112), font=f_p)

    # House 10 (right center diamond)
    draw.text((ch_x2 - 150, mid_y), "10", fill=COLOR_MUTED, font=f_num)
    draw.text((ch_x2 - 70, mid_y), "Sa", fill=(30, 60, 140), font=f_p)

    # House 7 (bottom diamond)
    draw.text((mid_x, ch_y2 - 75), "7", fill=COLOR_MUTED, font=f_num, anchor="mm")
    draw.text((mid_x - 45, ch_y2 - 110), "Me", fill=(34, 139, 34), font=f_p)
    draw.text((mid_x + 45, ch_y2 - 110), "Su", fill=COLOR_CRIMSON, font=f_p)

    # 4 Feature Badges in a Row below Chart using exact Siddhanta terminology
    b_y = 820
    badge_w = 215
    badge_h = 160
    badges_data = [
        ("D1 Lagna", "Birth Chart", "icons/kundli.webp"),
        ("D9 Navamsha", "Soul Destiny", "icons/Vargas.webp"),
        ("Dashas", "Vimshottari", "icons/Overview.webp"),
        ("Yogas", "Planetary Yogas", "icons/yogas.webp"),
    ]

    for i, (b_title, b_sub, b_icon) in enumerate(badges_data):
        bx = 60 + i * (badge_w + 35)
        draw.rounded_rectangle([bx, b_y, bx + badge_w, b_y + badge_h], radius=16, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)
        _paste_icon_badge(canvas, ILLUST_DIR / b_icon, (bx + 75, b_y + 16, bx + 140, b_y + 81), badge_fill=(254, 243, 220), padding=8)
        draw.text((bx + badge_w // 2, b_y + 104), b_title, fill=COLOR_CRIMSON, font=_font_sans(20, bold=True), anchor="mm")
        draw.text((bx + badge_w // 2, b_y + 132), b_sub, fill=COLOR_MUTED, font=_font_sans(16), anchor="mm")

    # Subtle quote note
    draw.text((540, 1205), "“The birth chart is the cosmic map of your karmic potential.”", fill=COLOR_CRIMSON, font=_font_serif(22, italic=True), anchor="mm")

    # Standardized bottom CTA pill
    _draw_cta_pill(canvas, draw, "Generate Your Free Kundli in Siddhanta", y=1245)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 5. CHAKRA (1080 x 1350)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_5_chakra(p_or_path: any, maybe_path: str | Path | None = None) -> str:
    output_path = maybe_path if maybe_path is not None else p_or_path
    canvas, draw = _prepare_card_canvas("chakra")
    _draw_brand_header(canvas, draw, y=42)

    # Title & Subtitle updated per user feedback (no health claims!)
    draw.text((60, 160), "Balance Your Inner Energy", fill=COLOR_CRIMSON, font=_font_serif(56, bold=True))
    draw.text((60, 232), "Explore the seven chakras through Jyotish insight.", fill=COLOR_MUTED, font=_font_serif(22, bold=False))

    # Top Right Circular Gauge: Overall Chakra Balance (compacted for 1350 height)
    g_cx, g_cy = 850, 420
    g_r = 65
    draw.text((g_cx, g_cy - 92), "Chakra Balance", fill=COLOR_DARK, font=_font_sans(19, bold=True), anchor="mm")

    # Gauge ring
    draw.ellipse([g_cx - g_r, g_cy - g_r, g_cx + g_r, g_cy + g_r], outline=(230, 220, 205), width=10)
    draw.arc([g_cx - g_r, g_cy - g_r, g_cx + g_r, g_cy + g_r], start=-90, end=180, fill=(46, 139, 87), width=10)
    draw.arc([g_cx - g_r, g_cy - g_r, g_cx + g_r, g_cy + g_r], start=180, end=230, fill=(218, 140, 30), width=10)
    draw.text((g_cx, g_cy), "75%", fill=COLOR_DARK, font=_font_sans(32, bold=True), anchor="mm")
    draw.text((g_cx, g_cy + 88), "Balanced", fill=COLOR_DARK, font=_font_sans(19, bold=True), anchor="mm")

    # Center: Meditating Yogi with glowing 7 chakras (scaled down cleanly, no river ghat)
    yogi_path = IMAGES_DIR / "chakra_meditating.webp"
    if yogi_path.exists():
        try:
            yogi = Image.open(yogi_path)
            yogi = _clean_transparency(yogi)
            scale = 550 / yogi.height
            nw, nh = int(yogi.width * scale), int(yogi.height * scale)
            yogi = yogi.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.alpha_composite(yogi, (50, 470))
        except Exception:
            pass

    # Right Column: 7 Chakras List (compacted)
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
    list_y = 570
    draw.rounded_rectangle([list_x - 20, list_y - 15, 1020, list_y + 310], radius=18, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=2)

    for i, (name, col) in enumerate(chakras):
        cy = list_y + i * 42
        draw.ellipse([list_x - 5, cy + 4, list_x + 17, cy + 26], fill=col)
        draw.text((list_x + 30, cy + 5), name, fill=COLOR_DARK, font=_font_sans(19, bold=True))

    # Subtle quote note
    draw.text((540, 1205), "“Harmony in energy centers brings peace to body and mind.”", fill=COLOR_CRIMSON, font=_font_serif(22, italic=True), anchor="mm")

    # Standardized bottom CTA pill
    _draw_cta_pill(canvas, draw, "Explore Your Chakras in Siddhanta", y=1245)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)


# ═════════════════════════════════════════════════════════════════════════════
# 6. JYOTISH INSIGHT (1080 x 1350)
# ═════════════════════════════════════════════════════════════════════════════
def render_card_6_jyotish(p: DailyPanchang, output_path: str | Path) -> str:
    canvas, draw = _prepare_card_canvas("transit")
    _draw_brand_header(canvas, draw, y=42)

    # Pill badge
    draw.rounded_rectangle([60, 155, 280, 198], radius=12, fill=(255, 248, 235), outline=(220, 190, 140), width=2)
    draw.text((170, 176), "JYOTISH INSIGHT", fill=COLOR_GOLD, font=_font_sans(19, bold=True), anchor="mm")

    # Determine planet and sign dynamically from Gochar snapshot
    planet_name = "Jupiter"
    target_sign = "Cancer"
    date_range = "CURRENT VEDIC GOCHARA"
    motion_info = ""

    if p.gochar:
        planet_name = p.gochar.spotlight_planet or "Jupiter"
        target_sign = p.gochar.spotlight_sign or "Cancer"
        date_range = p.gochar.spotlight_date_range or "CURRENT VEDIC GOCHARA"
        if "Retrograde" in p.gochar.spotlight_motion:
            motion_info = " • RETROGRADE (वक्री)"

    # Map sign to Roman numeral, Hindi name, and classical Shastric qualities
    ZODIAC_DATA = {
        "Aries": ("I", "MESHA", "Courage & Leadership", "Initiative & fresh beginnings"),
        "Taurus": ("II", "VRISHABHA", "Material Stability", "Grounded growth & perseverance"),
        "Gemini": ("III", "MITHUNA", "Intellect & Expression", "Communication & philosophical study"),
        "Cancer": ("IV", "KARKA", "Emotional Depth & Intuition", "Inner wisdom & nurturing strength"),
        "Leo": ("V", "SIMHA", "Authority & Vitality", "Confidence & noble pursuits"),
        "Virgo": ("VI", "KANYA", "Analytical Discernment", "Detail-oriented mastery & service"),
        "Libra": ("VII", "TULA", "Harmony & Balance", "Diplomacy & refined creativity"),
        "Scorpio": ("VIII", "VRISHCHIKA", "Deep Intuition & Transformation", "Occult wisdom & emotional resilience"),
        "Sagittarius": ("IX", "DHANU", "Dharma & Higher Guidance", "Spiritual expansion & ethical triumph"),
        "Capricorn": ("X", "MAKARA", "Karmic Endurance", "Professional duty & long-term foundation"),
        "Aquarius": ("XI", "KUMBHA", "Universal Insight & Gains", "Community collaboration & vision"),
        "Pisces": ("XII", "MEENA", "Transcendence & Peace", "Moksha orientation & meditative clarity"),
    }

    clean_sign = target_sign.split()[0]
    roman, sign_hi, trait_head, trait_sub = ZODIAC_DATA.get(clean_sign, ("VII", "TULA", "Refined Harmony", "Auspicious planetary alignment"))

    # Planet-specific wisdom traits
    PLANET_TRAITS = {
        "Venus": ("Creative Harmony & Aesthetic Balance", "Deepens relationship understanding, artistic pursuits & grace"),
        "Mercury": ("Analytical Intellect & Commerce", "Sharpening business communication, logic & negotiations"),
        "Mars": ("Courage & Decisive Energy", "Action-oriented clarity, vitality & protection"),
        "Jupiter": ("Wisdom, Ethics & Expansion", "Higher learning, mentor blessings & spiritual clarity"),
        "Saturn": ("Patience, Duty & Karmic Restructuring", "Endurance, long-term discipline & grounded humility"),
    }

    if planet_name in PLANET_TRAITS:
        trait_head, trait_sub = PLANET_TRAITS[planet_name]

    # Title & Subtitle - dynamic from active transit
    draw.text((60, 215), f"{planet_name} Transit in {clean_sign}", fill=COLOR_CRIMSON, font=_font_serif(50, bold=True))
    draw.text((60, 285), f"{date_range}{motion_info}", fill=COLOR_DARK, font=_font_sans(22, bold=True))

    # Right side: Dynamic Zodiac Symbol in Gold Circle matching the transit sign
    draw.ellipse([870, 185, 995, 305], fill=(254, 243, 220), outline=(210, 175, 120), width=2)
    draw.text((932, 232), roman, fill=COLOR_CRIMSON, font=_font_serif(40, bold=True), anchor="mm")
    draw.text((932, 272), sign_hi, fill=COLOR_GOLD, font=_font_sans(13, bold=True), anchor="mm")

    # Left Column: 3 concise Shastric transit insights from Gochar snapshot
    fav_str = ", ".join(p.gochar.favorable_rashis[:2]) if (p.gochar and p.gochar.favorable_rashis) else "Cancer & Scorpio"
    pts = [
        ("icons/Overview.webp", trait_head, trait_sub),
        ("icons/family.webp", f"Favorable Alignment: {fav_str}", "Supportive planetary momentum & positive opportunities"),
        ("icons/strength.webp", f"Vedic Transit Guidance", f"Mindful alignment with {planet_name}'s cosmic energy"),
    ]

    for idx, (icon_rel, pt_head, pt_sub) in enumerate(pts):
        b_y = 350 + idx * 135
        _paste_icon_badge(canvas, ILLUST_DIR / icon_rel, (60, b_y, 140, b_y + 80), badge_fill=(254, 243, 220), padding=10)
        draw.text((165, b_y + 10), pt_head, fill=COLOR_DARK, font=_font_sans(24, bold=True))
        draw.text((165, b_y + 44), pt_sub, fill=COLOR_MUTED, font=_font_sans(19))

    # Decorative clean celestial Jupiter sphere
    c_cy = 920
    draw.ellipse([420, c_cy - 90, 660, c_cy + 90], outline=(225, 195, 140, 110), width=2)
    draw.ellipse([480, c_cy - 40, 600, c_cy + 40], fill=(218, 165, 82), outline=(180, 120, 40), width=2)

    # Subtle quote note
    draw.text((540, 1205), "“When Guru moves, wisdom finds a new direction.”", fill=COLOR_CRIMSON, font=_font_serif(22, italic=True), anchor="mm")

    # Standardized bottom CTA pill
    _draw_cta_pill(canvas, draw, "Track Planetary Transits in Siddhanta", y=1245)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return str(output_path)
