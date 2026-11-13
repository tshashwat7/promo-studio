#!/usr/bin/env python3
"""
Siddhanta Reel Generator

Requirements:
    pip install pillow numpy

System requirements:
    ffmpeg
    ffprobe

Examples:
    python generate_reel.py data.json --lang en
    python generate_reel.py data.json --lang both --fonts assets/fonts
    python generate_reel.py data.json --lang en --preview

Default output:
    1080 x 1920
    30 FPS
    MP4 / H.264 / AAC

Hindi output uses Pillow libraqm when available, or falls back to
promo_studio.shaping (uharfbuzz + freetype-py) when libraqm is absent.
"""

import argparse
import glob
import json
import math
import os
import subprocess
import tempfile
import wave

from functools import lru_cache
from pathlib import Path

import numpy as np

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
    features,
)

try:
    from promo_studio.shaping import ShapedFont
except ImportError:
    ShapedFont = None


# ---------------------------------------------------------
# Design
# ---------------------------------------------------------

INK = (62, 30, 18)
MUTED = (104, 66, 38)
GOLD = (180, 130, 40)
LINE = (210, 163, 70)
MAROON = (140, 34, 40)
GREEN = (40, 128, 80)
RED = (176, 44, 44)
CREAM = (255, 246, 226)

BACKGROUND_NAMES = {
    "intro": [
        "intro_sunrise_template.webp",
        "intro_template.webp",
        "intro_template.jpg",
    ],
    "panchang": [
        "Panchang Temple Riverside Template.webp",
        "Panchang-Temple-Riverside-Template.jpg",
    ],
    "transit": [
        "transit_template.webp",
        "transit_template.jpg",
    ],
    "muhurat": [
        "plan_day_template.webp",
        "plan_day_template.jpg",
    ],
    "guidance": [
        "Generic festival_old.webp",
        "Generic festival.webp",
        "generic_festival.webp",
    ],
}

PLANET_ALIASES = {
    "jupiter": ["jupiter", "guru", "brihaspati"],
    "saturn": ["saturn", "shani"],
    "rahu": ["rahu"],
    "ketu": ["ketu"],
    "mercury": ["mercury", "budh"],
    "venus": ["venus", "shukra"],
    "mars": ["mars", "mangal"],
}

DISHA_SHOOL_DATA = {
    0: {  # Monday
        "disha_en": "East", "disha_hi": "पूर्व दिशा",
        "upay_en": "Look into a mirror before stepping out", "upay_hi": "दर्पण देखकर घर से निकलें",
        "color_en": "Pearl White & Silver", "color_hi": "सफेद एवं चांदी जैसा",
        "detail_en": "Symbol of calm and spiritual clarity", "detail_hi": "शांति और मानसिक स्पष्टता का प्रतीक",
        "deity_en": "Lord Shiva & Chandra Deva", "deity_hi": "भगवान शिव एवं चंद्र देव",
        "mantra_en": "Chant: Om Namah Shivaya", "mantra_hi": "मंत्र: ॐ नमः शिवाय",
    },
    1: {  # Tuesday
        "disha_en": "North", "disha_hi": "उत्तर दिशा",
        "upay_en": "Eat a little Jaggery (Gud) before travel", "upay_hi": "यात्रा से पूर्व थोड़ा गुड़ खाकर निकलें",
        "color_en": "Crimson Red & Saffron", "color_hi": "लाल एवं सिंदूरी",
        "detail_en": "Symbol of vitality, courage and strength", "detail_hi": "ऊर्जा, साहस और पराक्रम का प्रतीक",
        "deity_en": "Shri Hanuman Ji", "deity_hi": "श्री हनुमान जी",
        "mantra_en": "Chant: Om Hanumate Namah", "mantra_hi": "मंत्र: ॐ हनुमते नमः",
    },
    2: {  # Wednesday
        "disha_en": "North", "disha_hi": "उत्तर दिशा",
        "upay_en": "Consume Coriander seeds (Dhania) or Til", "upay_hi": "धनिया या तिल खाकर निकलें",
        "color_en": "Emerald Green", "color_hi": "हरा एवं पन्ना रंग",
        "detail_en": "Enhances intellect, trade and communication", "detail_hi": "बुद्धि, व्यापार और संचार में शुभ",
        "deity_en": "Lord Ganesha & Budh Deva", "deity_hi": "भगवान गणेश एवं बुध देव",
        "mantra_en": "Chant: Om Gam Ganapataye Namah", "mantra_hi": "मंत्र: ॐ गं गणपतये नमः",
    },
    3: {  # Thursday
        "disha_en": "South", "disha_hi": "दक्षिण दिशा",
        "upay_en": "Eat Yellow Mustard or Curd", "upay_hi": "पीली सरसों या दही खाकर निकलें",
        "color_en": "Bright Yellow & Gold", "color_hi": "पीला एवं स्वर्णिम",
        "detail_en": "Brings wisdom, prosperity and divine grace", "detail_hi": "ज्ञान, समृद्धि और गुरु कृपा का प्रतीक",
        "deity_en": "Lord Vishnu & Brihaspati", "deity_hi": "श्री हरि विष्णु एवं बृहस्पति देव",
        "mantra_en": "Chant: Om Namo Bhagavate Vasudevaya", "mantra_hi": "मंत्र: ॐ नमो भगवते वासुदेवाय",
    },
    4: {  # Friday
        "disha_en": "West", "disha_hi": "पश्चिम दिशा",
        "upay_en": "Eat sweet Curd (Dahi) or Barley", "upay_hi": "मीठा दही या जौ खाकर निकलें",
        "color_en": "Lustrous White & Soft Pink", "color_hi": "चमकीला सफेद एवं गुलाबी",
        "detail_en": "Symbol of beauty, harmony and abundance", "detail_hi": "सौंदर्य, सामंजस्य और ऐश्वर्य का प्रतीक",
        "deity_en": "Maa Lakshmi & Shukra Deva", "deity_hi": "माँ लक्ष्मी एवं शुक्र देव",
        "mantra_en": "Chant: Om Shreem Mahalakshmyai Namah", "mantra_hi": "मंत्र: ॐ श्रीं महालक्ष्म्यै नमः",
    },
    5: {  # Saturday
        "disha_en": "East", "disha_hi": "पूर्व दिशा",
        "upay_en": "Eat Ginger (Adrak) or Urad dal", "upay_hi": "अदरक या उड़द खाकर निकलें",
        "color_en": "Navy Blue & Deep Charcoal", "color_hi": "नीला एवं गहरा स्लेटी",
        "detail_en": "Cultivates patience, discipline and focus", "detail_hi": "धैर्य, अनुशासन और कर्म शुद्धि",
        "deity_en": "Lord Shani Deva", "deity_hi": "भगवान शनि देव",
        "mantra_en": "Chant: Om Sham Shanaishcharaya Namah", "mantra_hi": "मंत्र: ॐ शं शनैश्चराय नमः",
    },
    6: {  # Sunday
        "disha_en": "West", "disha_hi": "पश्चिम दिशा",
        "upay_en": "Eat Betel leaf (Paan) or Ghee", "upay_hi": "पान या घी खाकर निकलें",
        "color_en": "Saffron, Orange & Copper", "color_hi": "नारंगी एवं तांबई",
        "detail_en": "Aura of confidence, leadership and health", "detail_hi": "आत्मबल, तेज और आरोग्य का प्रतीक",
        "deity_en": "Lord Surya Narayana", "deity_hi": "भगवान सूर्य नारायण",
        "mantra_en": "Chant: Om Suryaya Namah", "mantra_hi": "मंत्र: ॐ सूर्याय नमः",
    },
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


# ---------------------------------------------------------
# Renderer
# ---------------------------------------------------------

class ReelRenderer:
    def __init__(self, args, data, language, muhurta=None):
        self.args = args
        self.data = data
        self.language = language
        self.muhurta = muhurta or {}

        self.width = args.width
        self.height = round(args.width * 16 / 9 / 2) * 2
        self.scale = self.width / 1080
        self.use_shaped = (
            self.language == "hi"
            and not features.check("raqm")
            and ShapedFont is not None
        )

        self.font_paths = {}
        self.backgrounds = {}
        self.icons = {}

        self.load_fonts()
        self.load_backgrounds()
        self.load_logo()

        self.border = self.make_border()
        self.scenes = self.build_scenes()

        self.starts = []
        elapsed = 0.0

        for scene in self.scenes:
            self.starts.append(elapsed)
            elapsed += scene["duration"]

        self.duration = elapsed

    def px(self, value):
        return max(1, round(value * self.scale))

    def label(self, english, hindi):
        return hindi if self.language == "hi" else english

    # -----------------------------------------------------
    # Fonts
    # -----------------------------------------------------

    def load_fonts(self):
        roots = [
            self.args.fonts,
            "assets/fonts",
            "fonts",
            "/usr/share/fonts",
            "/Library/Fonts",
            "C:/Windows/Fonts",
        ]

        # Optional fallback available when matplotlib is installed.
        try:
            import matplotlib

            roots.append(
                os.path.join(
                    matplotlib.get_data_path(),
                    "fonts",
                    "ttf",
                )
            )
        except ImportError:
            pass

        if self.language == "hi":
            if not features.check("raqm") and ShapedFont is None:
                raise RuntimeError(
                    "Hindi requires Pillow with libraqm support or "
                    "uharfbuzz + freetype-py (promo_studio.shaping)."
                )

            patterns = {
                "bold": [
                    "NotoSerifDevanagari-Bold.ttf",
                    "NotoSerifDevanagari*.ttf",
                    "Martel-ExtraBold.ttf",
                    "Martel-Bold.ttf",
                    "NotoSansDevanagari-Bold.ttf",
                    "NotoSansDevanagari*.ttf",
                ],
                "sans": [
                    "NotoSansDevanagari-Bold.ttf",
                    "NotoSansDevanagari*.ttf",
                    "Hind-SemiBold.ttf",
                    "Hind-Medium.ttf",
                ],
            }
        else:
            patterns = {
                "bold": [
                    "LibreBaskerville-Bold.ttf",
                    "LibreBaskerville*.ttf",
                    "DejaVuSerif-Bold.ttf",
                ],
                "sans": [
                    "DMSans-Bold.ttf",
                    "DMSans*.ttf",
                    "DejaVuSans-Bold.ttf",
                ],
            }

        for role, candidates in patterns.items():
            matches = []

            for pattern in candidates:
                for root in roots:
                    if not root or not os.path.exists(root):
                        continue
                    matches.extend(
                        sorted(
                            glob.glob(
                                os.path.join(root, "**", pattern),
                                recursive=True,
                            )
                        )
                    )

                if matches:
                    break

            if not matches:
                raise FileNotFoundError(
                    f"Missing {self.language} font for '{role}'. "
                    "Place the required fonts in --fonts DIR."
                )

            self.font_paths[role] = matches[0]

    @lru_cache(maxsize=256)
    def font(self, role, size):
        if self.use_shaped:
            return ShapedFont(Path(self.font_paths[role]), max(1, size))

        font = ImageFont.truetype(
            self.font_paths[role],
            max(1, size),
        )

        # Set a bold weight if a variable font is supplied.
        try:
            axes = font.get_variation_axes()
            values = []

            for axis in axes:
                name = axis.get("name", b"")

                if isinstance(name, bytes):
                    name = name.decode()

                if "weight" in str(name).lower():
                    values.append(
                        min(
                            axis["maximum"],
                            max(axis["minimum"], 700),
                        )
                    )
                else:
                    values.append(axis["default"])

            font.set_variation_by_axes(values)
        except (OSError, AttributeError):
            pass

        return font

    def _draw_shaped_text(
        self,
        layer,
        value,
        x,
        y,
        font,
        color,
        alpha,
        anchor,
    ):
        text_width = font.getlength(value)
        x0, y0, x1, y1 = font.bbox(0, 0, value)
        text_height = max(1, y1 - y0)

        if anchor == "mt":
            draw_x = round(x - text_width / 2)
            baseline = round(y - y0)
        elif anchor == "mm":
            draw_x = round(x - text_width / 2)
            baseline = round(y - (y0 + y1) / 2)
        elif anchor == "lm":
            draw_x = round(x - x0)
            baseline = round(y - (y0 + y1) / 2)
        else:  # "lt"
            draw_x = round(x - x0)
            baseline = round(y - y0)

        fill_alpha = round(255 * alpha)
        for glyph_id, gx, gy in font._glyphs(value):
            mask, left, top = font._mask(glyph_id)
            if mask is None:
                continue
            if fill_alpha < 255:
                mask = mask.point(lambda v: round(v * fill_alpha / 255))
            glyph_img = Image.new("RGBA", mask.size, (*color, 255))
            glyph_img.putalpha(mask)
            layer.alpha_composite(
                glyph_img,
                (round(draw_x + gx + left), round(baseline - gy - top)),
            )

    def text(
        self,
        layer,
        value,
        x,
        y,
        size=40,
        role="sans",
        color=INK,
        alpha=1.0,
        anchor="lt",
        max_width=None,
    ):
        if not value:
            return

        value = str(value)
        size = self.px(size)
        limit = max_width or self.width * 0.82
        minimum = self.px(22)

        while (
            size > minimum
            and self.font(role, size).getlength(value) > limit
        ):
            size -= 1

        if self.font(role, size).getlength(value) > limit:
            raise ValueError(
                f"Text cannot fit at readable size: {value!r}"
            )

        alpha = max(0.0, min(1.0, alpha))
        font = self.font(role, size)

        if self.use_shaped:
            if not font.covers(value):
                for fallback_name in (
                    "Hind-SemiBold.ttf",
                    "Martel-Bold.ttf",
                    "DMSans-Bold.ttf",
                    "LibreBaskerville-Bold.ttf",
                ):
                    matches = sorted(
                        glob.glob(
                            os.path.join("assets/fonts", "**", fallback_name),
                            recursive=True,
                        )
                    )
                    if matches:
                        candidate = ShapedFont(Path(matches[0]), size)
                        if candidate.covers(value):
                            font = candidate
                            break
            self._draw_shaped_text(
                layer,
                value,
                x,
                y,
                font,
                color,
                alpha,
                anchor,
            )
            return

        ImageDraw.Draw(layer).text(
            (x, y),
            value,
            font=font,
            fill=(*color, round(255 * alpha)),
            anchor=anchor,
        )

    def wrap_lines(
        self,
        value,
        size=40,
        role="sans",
        max_width=400,
    ):
        """Wrap text into lines that fit within max_width."""
        if not value:
            return []

        words = str(value).split()
        if not words:
            return []

        px_size = self.px(size)
        font = self.font(role, px_size)
        lines = []
        current = words[0]

        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.getlength(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines

    # -----------------------------------------------------
    # Assets
    # -----------------------------------------------------

    def load_backgrounds(self):
        root = Path(self.args.assets)

        for kind, filenames in BACKGROUND_NAMES.items():
            matches = []
            for filename in filenames:
                matches = sorted(root.rglob(filename))
                if matches:
                    break

            if not matches:
                if kind in ("intro", "guidance"):
                    # Fall back to panchang background if specific artwork not supplied
                    continue
                raise FileNotFoundError(
                    f"Background missing: {filenames[0]}"
                )

            image = Image.open(matches[0]).convert("RGB")

            if kind == "intro":
                # The intro template is a 9:16 vertical cosmic sunrise artwork.
                # Uniform scale and center crop directly without splitting/blurring.
                scale = max(self.width / image.width, self.height / image.height)
                nw, nh = round(image.width * scale), round(image.height * scale)
                image_scaled = image.resize((nw, nh), Image.Resampling.LANCZOS)
                crop_x = (nw - self.width) // 2
                crop_y = (nh - self.height) // 2
                self.backgrounds[kind] = image_scaled.crop(
                    (crop_x, crop_y, crop_x + self.width, crop_y + self.height)
                ).convert("RGBA")
                continue

            # Preserve the real artwork at the top.
            scale_mult = 1.45 if kind == "guidance" else 1.20
            scaled_width = round(self.width * scale_mult)
            scaled_height = round(
                image.height * scaled_width / image.width
            )

            image = image.resize(
                (scaled_width, scaled_height),
                Image.Resampling.LANCZOS,
            )

            if kind == "guidance":
                anchor = 0.99
            elif kind == "transit":
                anchor = 0.75
            else:
                anchor = 0.70
            left = round(
                (scaled_width - self.width) * anchor
            )

            image = image.crop(
                (
                    left,
                    0,
                    left + self.width,
                    image.height,
                )
            )

            # These source images are 4:5.
            # Extend only the bottom, never the top.
            if image.height < self.height:
                missing = self.height - image.height

                strip = image.crop(
                    (
                        0,
                        max(0, image.height - missing),
                        self.width,
                        image.height,
                    )
                )

                strip = strip.transpose(
                    Image.Transpose.FLIP_TOP_BOTTOM
                )

                strip = strip.resize(
                    (self.width, missing)
                ).filter(
                    ImageFilter.GaussianBlur(4 * self.scale)
                )

                canvas = Image.new(
                    "RGB",
                    (self.width, self.height),
                )

                canvas.paste(image, (0, 0))
                canvas.paste(strip, (0, image.height))
                image = canvas

            self.backgrounds[kind] = image.crop(
                (0, 0, self.width, self.height)
            ).convert("RGBA")

    def load_logo(self):
        root = Path(self.args.assets)

        candidates = [
            root / "assets/branding/logo.webp",
            root / "branding/logo.webp",
            root / "logo.jpg",
            root / "logo.webp",
            root / "logo.png",
        ]

        if self.args.logo:
            path = Path(self.args.logo)
        else:
            path = next(
                (p for p in candidates if p.exists()),
                None,
            )

        if path is None or not path.exists():
            raise FileNotFoundError(
                "Logo missing. Supply --logo PATH."
            )

        image = Image.open(path).convert("RGBA")

        side = min(image.size)
        left = (image.width - side) // 2
        top = (image.height - side) // 2

        image = image.crop(
            (left, top, left + side, top + side)
        ).resize((500, 500), Image.Resampling.LANCZOS)

        mask = Image.new("L", (500, 500), 0)

        ImageDraw.Draw(mask).ellipse(
            (4, 4, 496, 496),
            fill=255,
        )

        # Preserve original transparency.
        original = np.asarray(image.getchannel("A"))
        circle = np.asarray(mask)

        image.putalpha(
            Image.fromarray(
                np.minimum(original, circle).astype("uint8")
            )
        )

        self.logo = image

    # -----------------------------------------------------
    # Border and logo
    # -----------------------------------------------------

    def make_border(self):
        multiplier = 2
        width = self.width * multiplier
        height = self.height * multiplier

        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)

        def q(value):
            return self.px(value) * multiplier

        for margin, thickness in [(28, 4), (42, 2)]:
            draw.rounded_rectangle(
                (
                    q(margin),
                    q(margin),
                    width - q(margin),
                    height - q(margin),
                ),
                radius=q(32),
                outline=(*LINE, 235),
                width=q(thickness),
            )

        # Top-right ornament is replaced by the watermark.
        corners = [
            (q(50), q(50), 1, 1),
            (q(50), height - q(50), 1, -1),
            (width - q(50), height - q(50), -1, -1),
        ]

        for x, y, sx, sy in corners:
            for offset in [-0.65, 0, 0.65]:
                angle = math.atan2(sy, sx) + offset
                points = []

                for sign, samples in [
                    (1, np.linspace(0, 1, 16)),
                    (-1, np.linspace(1, 0, 16)),
                ]:
                    for t in samples:
                        radius = q(58) * t
                        lateral = (
                            sign * q(9) * math.sin(math.pi * t)
                        )

                        points.append(
                            (
                                x
                                + radius * math.cos(angle)
                                - lateral * math.sin(angle),
                                y
                                + radius * math.sin(angle)
                                + lateral * math.cos(angle),
                            )
                        )

                draw.line(
                    points + [points[0]],
                    fill=(*LINE, 255),
                    width=q(2),
                )

        return image.resize(
            (self.width, self.height),
            Image.Resampling.LANCZOS,
        )

    def draw_logo(
        self,
        image,
        center_x,
        center_y,
        size,
        opacity,
    ):
        size = max(2, round(size))

        logo = self.logo.resize(
            (size, size),
            Image.Resampling.LANCZOS,
        )

        logo.putalpha(
            logo.getchannel("A").point(
                lambda value: round(value * opacity)
            )
        )

        image.alpha_composite(
            logo,
            (
                round(center_x - size / 2),
                round(center_y - size / 2),
            ),
        )

    # -----------------------------------------------------
    # JSON -> scenes
    # -----------------------------------------------------

    def get_intro_hook(self, today, fest_en, fest_hi):
        user_choice = getattr(self.args, "intro_hook", "auto")

        day_en = today.get("day_of_week_en", "Today")
        day_hi = today.get("day_of_week_hi", "आज")

        is_fest = bool(today.get("is_festival_today") and (fest_en or fest_hi))

        if (user_choice == "festival" or (user_choice == "auto" and is_fest)) and (fest_en or fest_hi):
            return {
                "en": f"{fest_en}\nSpecial Panchang" if fest_en else "Festival Special\nDaily Panchang",
                "hi": f"{fest_hi}\nविशेष पंचांग" if fest_hi else "त्योहार विशेष\nदैनिक पंचांग",
                "is_festival_hook": True,
            }

        catalog = {
            "curiosity": {
                "en": "How Will Your\nDay Be Today?",
                "hi": "आज का दिन\nकैसा रहेगा?",
            },
            "weekday": {
                "en": f"{day_en} Special\nDaily Panchang",
                "hi": f"{day_hi} विशेष\nदैनिक पंचांग",
            },
            "muhurat": {
                "en": "Today's Muhurat\n& Planet Transits",
                "hi": "आज के शुभ मुहूर्त\nऔर ग्रह गोचर",
            },
            "personal": {
                "en": "How Will Today\nGo for You?",
                "hi": "कैसा बीतेगा\nआज का दिन?",
            },
            "vedic": {
                "en": "Explore Today's\nVedic Panchang",
                "hi": "जानें आज का\nवैदिक पंचांग",
            },
        }

        if user_choice in catalog:
            hook_item = catalog[user_choice]
            return {
                "en": hook_item["en"],
                "hi": hook_item["hi"],
                "is_festival_hook": False,
            }

        # Automatic deterministic daily rotation based on calendar date
        try:
            import datetime as _dt
            d = _dt.date.fromisoformat(today["date"])
            idx = d.toordinal()
        except Exception:
            idx = 0

        hook_keys = ["curiosity", "weekday", "muhurat", "personal", "vedic"]
        selected_key = hook_keys[idx % len(hook_keys)]
        hook_item = catalog[selected_key]
        return {
            "en": hook_item["en"],
            "hi": hook_item["hi"],
            "is_festival_hook": False,
        }

    def build_scenes(self):
        today = self.data["today"]

        language_key = (
            "hindi" if self.language == "hi" else "english"
        )

        facts = today[language_key]
        local = self.label
        scenes = []

        festivals = today.get("festivals_today") or []

        festival = (
            festivals[0]
            if today.get("is_festival_today") and festivals
            else {}
        )

        fest_en = festival.get("name_en", "")
        fest_hi = festival.get("name_hi", "")
        festival_name = fest_hi if self.language == "hi" else fest_en

        ritual = ""
        parana = festival.get("parana_time")
        if isinstance(parana, dict) and parana.get("start") and parana.get("end"):
            lbl = local("Parana Time", "पारण समय")
            ritual = f"{lbl} {parana['start']} – {parana['end']}"
        elif (
            festival.get("ritual_window_start")
            and festival.get("ritual_window_end")
        ):
            lbl = festival.get("ritual_label") or local("Puja Muhurat", "पूजा मुहूर्त")
            is_next = festival.get("ritual_window_is_next_day", False)
            next_prefix = local("Next Day ", "कल ") if is_next else ""
            ritual = (
                f"{next_prefix}{lbl} "
                + festival["ritual_window_start"]
                + " – "
                + festival["ritual_window_end"]
            )

        hook_info = self.get_intro_hook(today, fest_en, fest_hi)
        title_text = hook_info["hi" if self.language == "hi" else "en"]

        scenes.append(
            {
                "kind": "intro",
                "duration": 6.8,
                "title": title_text,
                "subtitle": (
                    local("Daily Panchang", "दैनिक पंचांग")
                    + " | "
                    + today["date"]
                ),
                "festival": festival_name,
                "ritual": ritual,
                "is_festival_hook": hook_info["is_festival_hook"],
            }
        )

        def end_text(key):
            entries = today.get(
                "timeline", {}
            ).get(key, [])

            if entries:
                entry = entries[0]
                end_local = entry.get("end_local")

                if not end_local:
                    return ""

                suffix = ""

                if end_local[:10] != today["date"]:
                    suffix = (
                        " ("
                        + end_local[8:10]
                        + "/"
                        + end_local[5:7]
                        + ")"
                    )

                return (
                    local("Ends ", "समाप्ति ")
                    + entry.get("end", "")
                    + suffix
                )

            fallback_end = facts.get(f"{key}_end")
            if fallback_end:
                return local("Ends ", "समाप्ति ") + str(fallback_end)

            return ""

        rows = []

        for key, english, hindi in [
            ("tithi", "TITHI", "तिथि"),
            ("nakshatra", "NAKSHATRA", "नक्षत्र"),
            ("yoga", "YOGA", "योग"),
            ("karana", "KARANA", "करण"),
        ]:
            value = facts.get(
                "tithi_name" if key == "tithi" else key
            )

            if value:
                rows.append(
                    (
                        local(english, hindi),
                        value,
                        end_text(key),
                        GOLD,
                        key == "tithi",
                    )
                )

        if facts.get("sunrise") and facts.get("sunset"):
            rows.append(
                (
                    local(
                        "SUNRISE • SUNSET",
                        "सूर्योदय • सूर्यास्त",
                    ),
                    facts["sunrise"] + " – " + facts["sunset"],
                    "",
                    GOLD,
                    False,
                )
            )

        moon = (
            facts.get("chandra_rashi")
            or facts.get("moon_rashi", "")
        )

        sun = (
            facts.get("surya_rashi")
            or facts.get("sun_rashi", "")
        )

        if moon and sun:
            rows.append(
                (
                    local(
                        "MOON • SUN SIGN",
                        "चंद्र • सूर्य राशि",
                    ),
                    moon + " • " + sun,
                    "",
                    GOLD,
                    False,
                )
            )

        location = self.data.get(
            "metadata", {}
        ).get("location", {})

        place = " • ".join(
            item
            for item in [
                location.get("name", "").split(",")[0],
                location.get("timezone", ""),
            ]
            if item
        )

        # Build authentic Vedic Masa, Paksha & Samvat subtitle if available
        masa = facts.get("masa")
        paksha = facts.get("paksha")
        samvat = facts.get("vikram_samvat")
        vedic_line1_parts = []
        if masa:
            vedic_line1_parts.append(masa)
        if paksha:
            paksha_label = paksha if self.language == "hi" else f"{paksha.capitalize()} Paksha"
            vedic_line1_parts.append(paksha_label)

        line1 = " • ".join(vedic_line1_parts) if vedic_line1_parts else facts.get("date_formatted", today["date"])
        line2 = f"वि. संवत् {samvat}" if self.language == "hi" else f"Vikram Samvat {samvat}" if samvat else ""

        panchang_subtitle = f"{line1}\n{line2}" if line2 else line1

        if rows:
            scenes.append(
                {
                    "kind": "panchang",
                    "duration": 8.5,
                    "title": local(
                        "Daily Panchang",
                        "दैनिक पंचांग",
                    ),
                    "subtitle": panchang_subtitle,
                    "rows": rows,
                    "place": place,
                }
            )

        positions = self.data.get(
            "transits", {}
        ).get("positions", {})

        rows = []

        keys = [
            key
            for key in ["jupiter", "saturn", "rahu", "ketu"]
            if key in positions
        ]

        keys += [
            key
            for key in ["mercury", "venus", "mars"]
            if positions.get(key, {}).get("is_retrograde")
        ][:2]

        for key in keys:
            planet = positions[key]
            hindi = self.language == "hi"

            rows.append(
                (
                    planet[
                        "name_hi" if hindi else "name_en"
                    ].split(" (")[0],
                    planet[
                        "rashi_hi" if hindi else "rashi_en"
                    ],
                    planet[
                        "motion_hi" if hindi else "motion_en"
                    ],
                    (
                        MAROON
                        if planet.get("is_retrograde")
                        else GOLD
                    ),
                    key,
                )
            )

        if rows:
            scenes.append(
                {
                    "kind": "transit",
                    "duration": 6.5,
                    "title": local(
                        "Graha Gochar",
                        "ग्रह गोचर",
                    ),
                    "subtitle": local(
                        "Planetary positions today",
                        "आज ग्रह कहाँ हैं",
                    ),
                    "rows": rows,
                }
            )

        periods = {
            period["id"]: period
            for period in today.get(
                "timeline", {}
            ).get("periods", [])
        }
        muhurtas = self.muhurta.get("muhurtas", {})

        rows = []

        def add_period(key, color, fallback_key=None):
            period = periods.get(key) or (
                muhurtas.get(fallback_key, {}) if fallback_key else {}
            )

            if not (
                period.get("start")
                and period.get("end")
            ):
                return

            rows.append(
                (
                    period[
                        (
                            "name_hi"
                            if self.language == "hi"
                            else "name_en"
                        )
                    ],
                    period["start"] + " – " + period["end"],
                    (
                        local("Avoid", "अशुभ — बचें")
                        if color == RED
                        else local("Auspicious", "शुभ")
                    ),
                    color,
                    False,
                )
            )

        add_period("brahma", GOLD, fallback_key="brahma_muhurta")
        add_period("abhijit", GREEN, fallback_key="abhijit_muhurta")

        best = next(
            (
                slot
                for slot in today.get(
                    "choghadiya", {}
                ).get("day", [])
                if slot.get("quality_en") == "Best"
            ),
            None,
        )

        if best and best.get("start") and best.get("end"):
            rows.append(
                (
                    best[
                        (
                            "name_hi"
                            if self.language == "hi"
                            else "name_en"
                        )
                    ]
                    + " "
                    + local("Choghadiya", "चौघड़िया"),
                    best["start"] + " – " + best["end"],
                    local("Auspicious", "शुभ"),
                    GREEN,
                    False,
                )
            )

        add_period("rahu", RED, fallback_key="rahu_kaal")

        if rows:
            scenes.append(
                {
                    "kind": "muhurat",
                    "duration": 9.5,
                    "title": local(
                        "Plan Your Day",
                        "आज का शुभ मुहूर्त",
                    ),
                    "subtitle": local(
                        "Auspicious & avoid timings",
                        "शुभ और अशुभ काल",
                    ),
                    "rows": rows,
                    "place": place,
                }
            )

        # -------------------------------------------------
        # Daily Guidance (Disha Shool, Lucky Color, Deity)
        # -------------------------------------------------
        import datetime as dt_mod
        try:
            target_dt = dt_mod.date.fromisoformat(today["date"])
            weekday_idx = target_dt.weekday()
        except Exception:
            weekday_idx = 1  # Default Tuesday

        info = DISHA_SHOOL_DATA.get(weekday_idx, DISHA_SHOOL_DATA[1])
        is_hi = self.language == "hi"

        guidance_cards = [
            (
                local("DISHA SHOOL", "दिशा शूल"),
                info["disha_hi" if is_hi else "disha_en"],
                local(f"Remedy: {info['upay_en']}", f"उपाय: {info['upay_hi']}"),
                RED,
            ),
            (
                local("LUCKY COLOR", "आज का शुभ रंग"),
                info["color_hi" if is_hi else "color_en"],
                info["detail_hi" if is_hi else "detail_en"],
                GOLD,
            ),
            (
                local("DEITY OF THE DAY", "आज के देवता"),
                info["deity_hi" if is_hi else "deity_en"],
                info["mantra_hi" if is_hi else "mantra_en"],
                GREEN,
            ),
        ]

        scenes.append(
            {
                "kind": "guidance",
                "duration": 7.5,
                "title": local(
                    "Daily Guidance",
                    "आज का मार्गदर्शन",
                ),
                "subtitle": local(
                    "Disha Shool, lucky color & deity",
                    "दिशा शूल, शुभ रंग एवं आज के देवता",
                ),
                "cards": guidance_cards,
            }
        )

        scenes.append(
            {
                "kind": "outro",
                "duration": 5.5,
                "title": "SIDDHANTA",
                "subtitle": local(
                    "Explore your Panchang",
                    "अपना पंचांग देखें",
                ),
            }
        )

        return scenes

    # -----------------------------------------------------
    # Planet artwork
    # -----------------------------------------------------

    def planet_icon(self, key):
        if key in self.icons:
            return self.icons[key]

        root = Path(self.args.assets)

        directories = [
            root / "assets/icons/planets",
            root / "icons/planets",
        ]

        candidates = []

        for directory in directories:
            if not directory.exists():
                continue

            for path in sorted(directory.iterdir()):
                if (
                    path.suffix.lower() in IMAGE_EXTENSIONS
                    and any(
                        alias in path.stem.lower()
                        for alias in PLANET_ALIASES[key]
                    )
                ):
                    candidates.append(path)

        if candidates:
            image = Image.open(
                candidates[0]
            ).convert("RGBA")

            # Circular crop with fine gold ring to eliminate square card backgrounds
            side = 120
            from PIL import ImageOps
            image_fit = ImageOps.fit(image, (side, side), Image.Resampling.LANCZOS)
            mask = Image.new("L", (side, side), 0)
            d_mask = ImageDraw.Draw(mask)
            d_mask.ellipse((2, 2, side - 2, side - 2), fill=255)
            image_fit.putalpha(mask)

            icon = Image.new("RGBA", (140, 140))
            icon.alpha_composite(
                image_fit,
                (
                    (140 - side) // 2,
                    (140 - side) // 2,
                ),
            )
            # Gold perimeter ring matching the theme
            d_icon = ImageDraw.Draw(icon)
            cx, cy, r = 70, 70, side // 2 - 1
            d_icon.ellipse(
                (cx - r, cy - r, cx + r, cy + r),
                outline=(*LINE, 255),
                width=3,
            )
        else:
            icon = Image.new("RGBA", (140, 140))
            draw = ImageDraw.Draw(icon)

            draw.ellipse(
                (15, 15, 125, 125),
                fill=(22, 38, 62, 255),
                outline=(*LINE, 255),
                width=3,
            )

            letters = {
                "jupiter": "J",
                "saturn": "S",
                "rahu": "R",
                "ketu": "K",
                "mercury": "M",
                "venus": "V",
                "mars": "Ma",
            }

            self.text(
                icon,
                letters[key],
                70,
                70,
                size=44,
                role="sans",
                color=LINE,
                anchor="mm",
            )

        self.icons[key] = icon
        return icon

    # -----------------------------------------------------
    # Intro
    # -----------------------------------------------------

    def draw_intro(self, layer, scene, time):
        draw = ImageDraw.Draw(layer)

        center_x = self.width / 2
        lines = scene["title"].splitlines()

        pitch = self.px(120)
        has_intro_bg = "intro" in self.backgrounds

        if has_intro_bg:
            # Render centered brand emblem above hook title in cosmic sky
            logo_progress = ease(time / 0.5)
            if logo_progress > 0:
                logo_y = self.px(270)
                logo_size = self.px(130)
                # Outer gold decorative ring
                draw.ellipse(
                    (
                        center_x - logo_size / 2 - self.px(6),
                        logo_y - logo_size / 2 - self.px(6),
                        center_x + logo_size / 2 + self.px(6),
                        logo_y + logo_size / 2 + self.px(6),
                    ),
                    outline=(*LINE, round(230 * logo_progress)),
                    width=self.px(3),
                )
                self.draw_logo(
                    layer,
                    center_x,
                    logo_y,
                    logo_size,
                    opacity=0.95 * logo_progress,
                )

            top = self.px(390)
            title_color = (255, 245, 222)       # Luminous radiant cream
            sub_color = (240, 196, 105)         # Warm celestial gold
            fest_color = (255, 140, 90)         # Bright amber / saffron
            ritual_color = (255, 225, 160)      # Soft warm gold
        else:
            question_height = len(lines) * pitch
            extra = self.px(
                200 if scene["festival"] else 75
            )
            if scene["ritual"]:
                extra += self.px(60)
            top = (
                self.height - question_height - extra
            ) / 2
            title_color = INK
            sub_color = GOLD
            fest_color = MAROON
            ritual_color = GOLD

        for index, line in enumerate(lines):
            self.text(
                layer,
                line,
                center_x,
                top + index * pitch,
                size=88,
                role="bold",
                color=title_color,
                alpha=ease(
                    (time - 0.15 - index * 0.18) / 0.5
                ),
                anchor="mt",
                max_width=self.width * 0.78,
            )

        divider_y = (
            top + len(lines) * pitch + self.px(24)
        )

        radius = (
            self.width
            * 0.18
            * ease((time - 0.7) / 0.6)
        )

        draw.line(
            (
                center_x - radius,
                divider_y,
                center_x + radius,
                divider_y,
            ),
            fill=(*LINE, 255),
            width=self.px(3),
        )

        self.text(
            layer,
            scene["subtitle"],
            center_x,
            divider_y + self.px(42),
            size=38,
            color=sub_color,
            alpha=ease((time - 1.0) / 0.5),
            anchor="mt",
            max_width=self.width * 0.78,
        )

        title_first_line = scene["title"].splitlines()[0] if scene.get("title") else ""
        has_separate_festival = bool(
            scene.get("festival")
            and not scene.get("is_festival_hook")
            and scene["festival"].lower() not in title_first_line.lower()
        )

        if has_separate_festival:
            self.text(
                layer,
                scene["festival"],
                center_x,
                divider_y + self.px(116),
                size=50,
                role="bold",
                color=fest_color,
                alpha=ease((time - 1.5) / 0.5),
                anchor="mt",
                max_width=self.width * 0.78,
            )

        if scene.get("ritual"):
            ritual_y = divider_y + self.px(186 if has_separate_festival else 116)
            self.text(
                layer,
                scene["ritual"],
                center_x,
                ritual_y,
                size=34 if not has_separate_festival else 32,
                color=ritual_color,
                alpha=ease((time - 1.9) / 0.5),
                anchor="mt",
                max_width=self.width * 0.78,
            )

    # -----------------------------------------------------
    # Main sections
    # -----------------------------------------------------

    def draw_section(self, layer, scene, time):
        draw = ImageDraw.Draw(layer)
        kind = scene["kind"]
        left = self.width * 0.085
        top = self.px(112)

        self.text(
            layer,
            scene["title"],
            left,
            top,
            size=84,
            role="bold",
            alpha=ease(time / 0.45),
            max_width=self.width * 0.60,
        )

        subtitle_lines = str(scene["subtitle"]).splitlines()
        sub_pitch = self.px(54)
        sub_top = top + self.px(134)
        for s_idx, s_line in enumerate(subtitle_lines):
            self.text(
                layer,
                s_line,
                left,
                sub_top + s_idx * sub_pitch,
                size=34 if len(subtitle_lines) > 1 else 38,
                role="bold",
                color=MAROON,
                alpha=ease((time - 0.15 - s_idx * 0.08) / 0.5),
                max_width=self.width * 0.65,
            )

        sub_bottom = sub_top + (len(subtitle_lines) - 1) * sub_pitch + self.px(36)
        divider_y = sub_bottom + self.px(28)

        draw.line(
            (
                left,
                divider_y,
                left
                + self.width * 0.32 * ease(time / 0.7),
                divider_y,
            ),
            fill=(*LINE, 255),
            width=self.px(3),
        )

        rows = scene["rows"]
        first_y = divider_y + self.px(44)

        if kind == "panchang":
            right = self.width * 0.89
            col1_w = self.width * 0.27
            col_gap = self.px(24)
            col2_x = left + col1_w + col_gap
            col2_w = right - col2_x

            min_row_h = self.px(116)
            top_pad = self.px(24)
            bottom_pad = self.px(24)
            label_line_h = self.px(40)
            val_line_h = self.px(54)

            cursor_y = first_y
            for index, row in enumerate(rows):
                label, value, detail, color, flag = row
                val_text = f"{value}, {detail}" if detail else value
                label_lines = self.wrap_lines(
                    label, size=30, role="sans", max_width=col1_w
                )
                val_size = 42 if flag else 40
                val_lines = self.wrap_lines(
                    val_text, size=val_size, role="bold", max_width=col2_w
                )
                content_h = max(
                    len(label_lines) * label_line_h,
                    len(val_lines) * val_line_h,
                )
                row_h = max(min_row_h, top_pad + content_h + bottom_pad)

                progress = ease((time - 0.45 - index * 0.18) / 0.45)
                if progress > 0:
                    y = cursor_y + (1 - progress) * self.px(18)
                    draw.line(
                        (
                            left,
                            y,
                            left + (right - left) * progress,
                            y,
                        ),
                        fill=(*LINE, round(220 * progress)),
                        width=self.px(2),
                    )
                    for li, l_line in enumerate(label_lines):
                        self.text(
                            layer,
                            l_line,
                            left,
                            y + top_pad + li * label_line_h,
                            size=30,
                            color=color,
                            alpha=progress,
                            max_width=col1_w,
                        )
                    for vi, v_line in enumerate(val_lines):
                        self.text(
                            layer,
                            v_line,
                            col2_x,
                            y + top_pad + vi * val_line_h,
                            size=val_size,
                            role="bold",
                            alpha=progress,
                            max_width=col2_w,
                        )

                cursor_y += row_h

            if scene.get("place"):
                badge_y = cursor_y + self.px(24)
                place_text = str(scene["place"])
                badge_font = self.font("sans", self.px(26))
                text_w = badge_font.getlength(place_text)
                icon_gap = self.px(30)
                badge_w = text_w + icon_gap + self.px(36)
                badge_h = self.px(48)
                badge_r = badge_h / 2

                # Translucent cream pill with crisp gold outline
                draw.rounded_rectangle(
                    (
                        left,
                        badge_y,
                        left + badge_w,
                        badge_y + badge_h,
                    ),
                    radius=badge_r,
                    fill=(255, 246, 226, 225),
                    outline=(*LINE, 245),
                    width=self.px(2),
                )

                # Crisp vector map pin
                pin_cx = left + self.px(22)
                pin_cy = badge_y + badge_h / 2 - self.px(2)
                pr = self.px(6.5)
                draw.ellipse(
                    (pin_cx - pr, pin_cy - pr - self.px(2), pin_cx + pr, pin_cy + pr - self.px(2)),
                    fill=(*MAROON, 255),
                )
                draw.polygon(
                    [
                        (pin_cx - self.px(5.5), pin_cy),
                        (pin_cx + self.px(5.5), pin_cy),
                        (pin_cx, pin_cy + self.px(10)),
                    ],
                    fill=(*MAROON, 255),
                )
                draw.ellipse(
                    (pin_cx - self.px(2.5), pin_cy - self.px(4), pin_cx + self.px(2.5), pin_cy + self.px(1)),
                    fill=(255, 255, 255, 255),
                )

                self.text(
                    layer,
                    place_text,
                    left + icon_gap + self.px(18),
                    badge_y + self.px(8),
                    size=26,
                    color=INK,
                    role="sans",
                    max_width=text_w + self.px(10),
                )
            return

        if kind == "transit":
            right = self.width * 0.58

            pitch = min(
                self.height * 0.105,
                (self.height * 0.74 - first_y) / len(rows),
            )
        else:
            right = self.width * (
                0.72 if kind == "panchang" else 0.88
            )

            pitch = (
                self.height * 0.65 - first_y
            ) / len(rows)

        for index, row in enumerate(rows):
            label, value, detail, color, flag = row

            progress = ease(
                (time - 0.45 - index * 0.18) / 0.45
            )

            if progress <= 0:
                continue

            y = (
                first_y
                + index * pitch
                + (1 - progress) * self.px(18)
            )

            draw.line(
                (
                    left,
                    y,
                    left + (right - left) * progress,
                    y,
                ),
                fill=(*LINE, round(220 * progress)),
                width=self.px(2),
            )

            if kind == "transit":
                size = round(
                    min(self.width * 0.12, pitch * 0.8)
                )

                icon = self.planet_icon(flag).resize(
                    (size, size),
                    Image.Resampling.LANCZOS,
                )

                icon.putalpha(
                    icon.getchannel("A").point(
                        lambda v: round(v * progress)
                    )
                )

                icon_x = (
                    left
                    + (1 - progress) * self.width * 0.65
                )

                layer.alpha_composite(
                    icon,
                    (
                        round(icon_x),
                        round(y + (pitch - size) / 2),
                    ),
                )

                text_x = left + size + self.px(25)

                self.text(
                    layer,
                    label,
                    text_x,
                    y + pitch * 0.15,
                    size=30,
                    color=color,
                    alpha=progress,
                    max_width=(right - text_x) * 0.64,
                )

                self.text(
                    layer,
                    value,
                    text_x,
                    y + pitch * 0.40,
                    size=60,
                    role="bold",
                    alpha=progress,
                    max_width=right - text_x,
                )

                self.text(
                    layer,
                    detail,
                    text_x,
                    y + pitch * 0.78,
                    size=28,
                    color=color,
                    alpha=progress,
                    max_width=right - text_x,
                )
            else:
                text_x = left

                if kind == "muhurat":
                    draw.line(
                        (
                            left,
                            y + pitch * 0.20,
                            left,
                            y + pitch * 0.80,
                        ),
                        fill=(*color, 255),
                        width=self.px(7),
                    )

                    text_x += self.px(25)

                self.text(
                    layer,
                    label,
                    text_x,
                    y + pitch * 0.12,
                    size=34 if flag else 30,
                    color=color,
                    alpha=progress,
                    max_width=right - text_x,
                )

                self.text(
                    layer,
                    value,
                    text_x,
                    y + pitch * 0.36,
                    size=(
                        54
                        if (flag and self.language == "hi")
                        else (66 if flag else 48)
                    ),
                    role="bold",
                    alpha=progress,
                    max_width=right - text_x,
                )

                if detail:
                    self.text(
                        layer,
                        detail,
                        text_x,
                        y + pitch * 0.76,
                        size=32,
                        color=(
                            MUTED if color == GOLD else color
                        ),
                        alpha=progress,
                        max_width=right - text_x,
                    )

        if scene.get("place"):
            badge_y = self.height * 0.70
            place_text = str(scene["place"])
            badge_font = self.font("sans", self.px(26))
            text_w = badge_font.getlength(place_text)
            icon_gap = self.px(30)
            badge_w = text_w + icon_gap + self.px(36)
            badge_h = self.px(48)
            badge_r = badge_h / 2

            draw.rounded_rectangle(
                (
                    left,
                    badge_y,
                    left + badge_w,
                    badge_y + badge_h,
                ),
                radius=badge_r,
                fill=(255, 246, 226, 225),
                outline=(*LINE, 245),
                width=self.px(2),
            )

            pin_cx = left + self.px(22)
            pin_cy = badge_y + badge_h / 2 - self.px(2)
            pr = self.px(6.5)
            draw.ellipse(
                (pin_cx - pr, pin_cy - pr - self.px(2), pin_cx + pr, pin_cy + pr - self.px(2)),
                fill=(*MAROON, 255),
            )
            draw.polygon(
                [
                    (pin_cx - self.px(5.5), pin_cy),
                    (pin_cx + self.px(5.5), pin_cy),
                    (pin_cx, pin_cy + self.px(10)),
                ],
                fill=(*MAROON, 255),
            )
            draw.ellipse(
                (pin_cx - self.px(2.5), pin_cy - self.px(4), pin_cx + self.px(2.5), pin_cy + self.px(1)),
                fill=(255, 255, 255, 255),
            )

            self.text(
                layer,
                place_text,
                left + icon_gap + self.px(18),
                badge_y + self.px(8),
                size=26,
                color=INK,
                role="sans",
                max_width=text_w + self.px(10),
            )

    # -----------------------------------------------------
    # Daily Guidance (Disha Shool, Lucky Color, Deity)
    # -----------------------------------------------------

    def draw_guidance(self, layer, scene, time):
        draw = ImageDraw.Draw(layer)
        left = self.width * 0.085
        right = self.width * 0.915
        top = self.px(112)

        self.text(
            layer,
            scene["title"],
            left,
            top,
            size=84,
            role="bold",
            alpha=ease(time / 0.45),
            max_width=self.width * 0.65,
        )

        sub_top = top + self.px(134)
        self.text(
            layer,
            scene["subtitle"],
            left,
            sub_top,
            size=38,
            role="bold",
            color=MAROON,
            alpha=ease((time - 0.15) / 0.5),
            max_width=self.width * 0.70,
        )

        divider_y = sub_top + self.px(38) + self.px(28)
        draw.line(
            (
                left,
                divider_y,
                left + self.width * 0.32 * ease(time / 0.7),
                divider_y,
            ),
            fill=(*LINE, 255),
            width=self.px(3),
        )

        cards = scene["cards"]
        first_y = divider_y + self.px(44)
        card_w = right - left
        card_h = self.px(180)
        gap = self.px(30)

        for index, (label, val, detail, color) in enumerate(cards):
            progress = ease((time - 0.40 - index * 0.18) / 0.45)
            if progress <= 0:
                continue

            cy = first_y + index * (card_h + gap) + (1 - progress) * self.px(18)
            alpha_int = round(255 * progress)

            # Card background
            draw.rounded_rectangle(
                (left, cy, right, cy + card_h),
                radius=self.px(24),
                fill=(255, 246, 226, round(235 * progress)),
                outline=(*LINE, round(240 * progress)),
                width=self.px(2),
            )

            # Vertical accent indicator on left edge
            draw.rounded_rectangle(
                (left, cy, left + self.px(10), cy + card_h),
                radius=self.px(5),
                fill=(*color, alpha_int),
            )

            # Category label (e.g. DISHA SHOOL / दिशा शूल)
            self.text(
                layer,
                label,
                left + self.px(34),
                cy + self.px(24),
                size=26,
                color=color,
                role="sans",
                alpha=progress,
                max_width=card_w - self.px(50),
            )

            # Main value (e.g. North / उत्तर दिशा)
            self.text(
                layer,
                val,
                left + self.px(34),
                cy + self.px(64),
                size=44,
                role="bold",
                color=INK,
                alpha=progress,
                max_width=card_w - self.px(50),
            )

            # Remedy or detail (e.g. Remedy: Eat Jaggery before travel)
            self.text(
                layer,
                detail,
                left + self.px(34),
                cy + self.px(124),
                size=28,
                role="sans",
                color=MUTED,
                alpha=progress,
                max_width=card_w - self.px(50),
            )

    # -----------------------------------------------------
    # Outro
    # -----------------------------------------------------

    def draw_outro(self, image, layer, scene):
        draw = ImageDraw.Draw(layer)
        center_x = self.width / 2

        self.draw_logo(
            image,
            center_x,
            self.height * 0.33,
            self.width * 0.23,
            1.0,
        )

        self.text(
            layer,
            scene["title"],
            center_x,
            self.height * 0.450,
            size=84,
            role="bold",
            anchor="mm",
        )

        self.text(
            layer,
            scene["subtitle"],
            center_x,
            self.height * 0.516,
            size=48,
            role="bold",
            color=MAROON,
            anchor="mm",
        )

        self.text(
            layer,
            self.label(
                "Panchang • Muhurat • Kundli",
                "पंचांग • मुहूर्त • कुंडली",
            ),
            center_x,
            self.height * 0.572,
            size=34,
            color=GOLD,
            anchor="mm",
        )

        button_width = self.width * 0.74
        button_height = self.height * 0.072
        button_y = self.height * 0.64

        draw.rounded_rectangle(
            (
                center_x - button_width / 2,
                button_y - button_height / 2,
                center_x + button_width / 2,
                button_y + button_height / 2,
            ),
            radius=button_height / 2,
            fill=(*MAROON, 255),
            outline=(*LINE, 255),
            width=self.px(3),
        )

        self.text(
            layer,
            self.label(
                "Download Siddhanta",
                "सिद्धांत डाउनलोड करें",
            ),
            center_x,
            button_y,
            size=44,
            color=CREAM,
            anchor="mm",
            max_width=button_width * 0.90,
        )

        self.text(
            layer,
            self.args.handle,
            center_x,
            self.height * 0.705,
            size=34,
            color=GOLD,
            anchor="mm",
        )

        # Engagement / Save CTA Pill below handle
        save_text = self.label(
            "Save this Reel to plan your day",
            "आज के शुभ मुहूर्त के लिए सेव करें",
        )
        save_size = 30
        save_font = self.font("bold", self.px(save_size))
        text_w = save_font.getlength(save_text)

        icon_w = self.px(16)
        icon_h = self.px(22)
        icon_gap = self.px(12)
        content_w = icon_w + icon_gap + text_w
        pad_x = self.px(28)

        pill_w = content_w + 2 * pad_x
        pill_h = self.px(54)
        pill_y = self.height * 0.755

        px0 = center_x - pill_w / 2
        py0 = pill_y - pill_h / 2
        px1 = center_x + pill_w / 2
        py1 = pill_y + pill_h / 2

        # Luminous ivory capsule with refined gold outline
        draw.rounded_rectangle(
            (px0, py0, px1, py1),
            radius=pill_h / 2,
            fill=(255, 248, 232, 245),
            outline=(*LINE, 255),
            width=self.px(2),
        )

        # Bookmark ribbon icon on left
        cx0 = center_x - content_w / 2
        ix = cx0
        iy = pill_y - icon_h / 2
        draw.polygon(
            [
                (ix, iy),
                (ix + icon_w, iy),
                (ix + icon_w, iy + icon_h),
                (ix + icon_w / 2, iy + icon_h - self.px(6)),
                (ix, iy + icon_h),
            ],
            fill=(*MAROON, 255),
        )

        self.text(
            layer,
            save_text,
            cx0 + icon_w + icon_gap,
            pill_y,
            size=save_size,
            role="bold",
            color=MAROON,
            anchor="lm",
            max_width=text_w + self.px(10),
        )

    # -----------------------------------------------------
    # Frames and transitions
    # -----------------------------------------------------

    def frame(self, scene_index, local_time):
        scene = self.scenes[scene_index]
        kind = scene["kind"]

        background_kind = (
            kind
            if kind in self.backgrounds
            else "panchang"
        )

        background = self.backgrounds[background_kind]

        enlarged_width = round(self.width * 1.02)
        enlarged_height = round(self.height * 1.02)

        image = background.resize(
            (enlarged_width, enlarged_height),
            Image.Resampling.BILINEAR,
        )

        progress = min(
            1.0,
            local_time / scene["duration"],
        )

        left = round(
            (enlarged_width - self.width) * progress
        )

        top = (enlarged_height - self.height) // 2

        image = image.crop(
            (
                left,
                top,
                left + self.width,
                top + self.height,
            )
        )

        image.alpha_composite(self.border)

        layer = Image.new(
            "RGBA",
            (self.width, self.height),
        )

        if kind != "outro":
            self.draw_logo(
                image,
                self.width - self.px(82),
                self.px(82),
                self.px(96),
                self.args.watermark_opacity,
            )

        if kind == "intro":
            self.draw_intro(layer, scene, local_time)
        elif kind == "outro":
            self.draw_outro(image, layer, scene)
        elif kind == "guidance":
            self.draw_guidance(layer, scene, local_time)
        else:
            self.draw_section(layer, scene, local_time)

        image.alpha_composite(layer)
        return image.convert("RGB")

    def render(self, frame_index):
        global_time = frame_index / self.args.fps

        scene_index = max(
            index
            for index, start in enumerate(self.starts)
            if start <= global_time
        )

        local_time = (
            global_time - self.starts[scene_index]
        )

        current = self.frame(
            scene_index,
            local_time,
        )

        fade = (
            0.8
            if self.scenes[scene_index]["kind"] == "outro"
            else 0.35
        )

        if scene_index > 0 and local_time < fade:
            previous = self.frame(
                scene_index - 1,
                self.scenes[
                    scene_index - 1
                ]["duration"] + local_time,
            )

            current = Image.blend(
                previous,
                current,
                ease(local_time / fade),
            )

        return current


# ---------------------------------------------------------
# Dynamic Voiceover Synthesis (Neural TTS)
# ---------------------------------------------------------

def synthesize_voiceover_clips(renderer, data, voice="swara", temp_dir=None):
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("edge-tts not installed; skipping voiceover synthesis")
        return []

    voice_map = {
        "swara": "hi-IN-SwaraNeural",
        "madhur": "hi-IN-MadhurNeural",
    }
    voice_name = voice_map.get(voice, "hi-IN-SwaraNeural")

    today = data.get("today", {})
    hindi = today.get("hindi", {})
    fest = today.get("primary_festival_hi") or ""
    tithi = hindi.get("tithi_name", "")
    nak = hindi.get("nakshatra", "")
    yoga = hindi.get("yoga", "")
    masa = hindi.get("masa", "")
    paksha = hindi.get("paksha", "")
    samvat = hindi.get("vikram_samvat", "विक्रम संवत 2083")

    abhijit_str = hindi.get("shubh_muhurta", {}).get("abhijit", "11:51 AM")
    abh_start = abhijit_str.split("–")[0].split("-")[0].replace("AM", "").replace("PM", "").strip()

    rahu_str = hindi.get("ashubh_muhurta", {}).get("rahu_kaal", "3:12 PM")
    rahu_start = rahu_str.split("–")[0].split("-")[0].replace("AM", "").replace("PM", "").strip()

    try:
        import datetime as dt_mod
        target_dt = dt_mod.date.fromisoformat(today["date"])
        weekday_idx = target_dt.weekday()
    except Exception:
        weekday_idx = 1
    disha_info = DISHA_SHOOL_DATA.get(weekday_idx, DISHA_SHOOL_DATA[1])
    disha = disha_info["disha_hi"].replace("दिशा", "").strip()
    deity = disha_info["deity_hi"]
    color = disha_info["color_hi"].split("एवं")[0].strip()

    pos = data.get("transits", {}).get("positions", {})
    jup_rashi = pos.get("jupiter", {}).get("rashi_hi", "कर्क")
    sat_rashi = pos.get("saturn", {}).get("rashi_hi", "मीन")

    clips = []
    for sc in renderer.scenes:
        kind = sc.get("kind")
        if kind == "intro":
            txt = f"आज {fest} का पावन पर्व है। देखिए आज का विशेष पंचांग।" if fest else "आज का दैनिक वैदिक पंचांग और विशेष मार्गदर्शन।"
        elif kind == "panchang":
            txt = f"{samvat}, {masa} {paksha}: {tithi} तिथि, {nak} नक्षत्र और {yoga} योग।"
        elif kind == "transit":
            txt = f"आज का ग्रह गोचर: गुरु {jup_rashi} राशि में, और शनि {sat_rashi} में वक्री हैं।"
        elif kind == "muhurat":
            txt = f"आज का शुभ और अशुभ काल: शुभ अभिजित मुहूर्त {abh_start}, और राहुकाल दोपहर {rahu_start} से रहेगा।"
        elif kind == "guidance":
            txt = f"दैनिक मार्गदर्शन: दिशा शूल {disha}, शुभ रंग {color}, और आराध्य {deity}।"
        elif kind == "outro":
            txt = "अपने संपूर्ण पंचांग के लिए आज ही डाउनलोड करें सिद्धांत ऐप।"
        else:
            txt = ""
        rate = "+14%" if kind == "muhurat" else "+10%"
        clips.append((txt, rate))

    out_paths = []
    async def _run():
        for i, (txt, rate) in enumerate(clips):
            if not txt:
                continue
            mp3_path = Path(temp_dir) / f"vo_{i}.mp3"
            comm = edge_tts.Communicate(text=txt, voice=voice_name, rate=rate)
            await comm.save(str(mp3_path))
            out_paths.append((i, mp3_path))

    asyncio.run(_run())
    return out_paths


# ---------------------------------------------------------
# Synthesized audio (Tanpura drone + Resonant Om chant + Temple bells)
# ---------------------------------------------------------

def create_audio(path, duration, scene_starts):
    sample_rate = 44100

    time = np.arange(
        round(duration * sample_rate)
    ) / sample_rate

    mix = np.zeros_like(time)

    # 1. Warm meditative master fade envelope
    master_envelope = (
        np.minimum(1, time / 2.0)
        * np.minimum(1, (duration - time) / 1.5)
    )

    # 2. Tanpura root drone (C# / 136.1 Hz Vedic Om frequency & harmonics)
    for frequency, level in [
        (68.05, 0.015),    # Sub-octave warm body
        (136.1, 0.030),    # Earth Om frequency (cosmic fundamental)
        (204.15, 0.018),   # Pa (fifth)
        (272.2, 0.012),    # Octave
        (408.3, 0.007),    # Higher harmonic
    ]:
        # Subtle gentle chorusing / breathing detune for sacred acoustic feel
        chorus = 1.0 + 0.002 * np.sin(2 * np.pi * 0.15 * time)
        mix += (
            level
            * np.sin(2 * np.pi * frequency * chorus * time)
            * master_envelope
        )

    # 3. Resonant continuous Om chant breath cycles (~7.5s cycle: inhale -> A-U-M resonance)
    cycle_period = 7.5
    cycle_phase = (time % cycle_period) / cycle_period

    # Smooth bell-curve vocal breath envelope per cycle
    vocal_envelope = np.sin(np.pi * np.clip(cycle_phase, 0.0, 1.0)) ** 2

    # Vowel formant simulation (A-U-M transition across the cycle):
    # Early cycle: "Ah" formant (~750 Hz); mid: "Oh" (~500 Hz); late: nasal "Mm" (~280 Hz)
    formant_freq = 750.0 - 470.0 * cycle_phase

    # Rich harmonic spectrum of fundamental 136.1 Hz passed through vocal formant
    f0 = 136.1
    om_vocal = np.zeros_like(time)
    for harmonic in range(1, 9):
        h_freq = f0 * harmonic
        # Gaussian resonance filter around the moving formant frequency
        resonance = np.exp(-((h_freq - formant_freq) / 140.0) ** 2)
        om_vocal += (0.018 * resonance) * np.sin(2 * np.pi * h_freq * time)

    mix += om_vocal * vocal_envelope * master_envelope

    # 4. Clear Tibetan / temple transition chimes on scene boundaries
    bell_times = [1.1] + [
        start + 0.1
        for start in scene_starts[1:]
    ]

    for start in bell_times:
        relative = time - start
        valid = relative >= 0
        positive = np.maximum(relative, 0)

        # 587 Hz (D5) fundamental + shimmering upper harmonics + gentle ring decay
        mix += (
            valid
            * 0.032
            * (
                np.sin(2 * np.pi * 587 * positive)
                + 0.40 * np.sin(2 * np.pi * 1174 * positive)
                + 0.18 * np.sin(2 * np.pi * 1761 * positive)
            )
            * np.exp(-positive * 3.5)
        )

    mix *= np.minimum(
        1,
        (duration - time) / 0.5,
    )

    pcm = (
        np.clip(mix, -1, 1) * 32767
    ).astype("<i2")

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


# ---------------------------------------------------------
# Export verification
# ---------------------------------------------------------

def verify_export(path, width, height, fps, duration):
    result = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            (
                "stream=codec_type,width,height,r_frame_rate:"
                "format=duration"
            ),
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )

    metadata = json.loads(result)

    video = next(
        stream
        for stream in metadata["streams"]
        if stream["codec_type"] == "video"
    )

    numerator, denominator = (
        video["r_frame_rate"].split("/")
    )

    actual_fps = (
        float(numerator) / float(denominator)
    )

    actual_duration = float(
        metadata["format"]["duration"]
    )

    if (
        video["width"] != width
        or video["height"] != height
        or abs(actual_fps - fps) > 0.01
        or abs(actual_duration - duration) > 0.15
    ):
        raise RuntimeError(
            "Export verification failed:\n"
            + json.dumps(metadata, indent=2)
        )

    has_audio = any(
        stream["codec_type"] == "audio"
        for stream in metadata["streams"]
    )

    print(
        f"Verified: {width}x{height}, "
        f"{actual_fps:.2f} FPS, "
        f"{actual_duration:.2f} seconds, "
        f"audio={'yes' if has_audio else 'no'}"
    )


# ---------------------------------------------------------
# Command line
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("data")
    parser.add_argument("--muhurta")

    parser.add_argument(
        "--lang",
        choices=["en", "hi", "both"],
        default="both",
    )

    parser.add_argument(
        "--intro-hook",
        choices=["auto", "festival", "curiosity", "weekday", "muhurat", "personal", "vedic"],
        default="auto",
        help="Intro headline hook style: auto (cycles daily, festival prioritized), or explicit hook style",
    )

    parser.add_argument("--assets", default=".")
    parser.add_argument("--fonts", default="assets/fonts")
    parser.add_argument("--logo")
    parser.add_argument("--audio", help="Optional background audio file (e.g. Om chant MP3/WAV)")
    parser.add_argument(
        "--voiceover",
        choices=["none", "swara", "madhur"],
        default="swara",
        help="Neural voiceover style: swara (Hindi female, default), madhur (Hindi male), or none",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1080,
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--out",
        default="reel.mp4",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
    )

    parser.add_argument(
        "--silent",
        action="store_true",
    )

    parser.add_argument(
        "--handle",
        default="@siddhanta.app",
    )

    parser.add_argument(
        "--watermark-opacity",
        type=float,
        default=0.30,
    )

    args = parser.parse_args()

    if args.width < 270 or args.width % 2:
        parser.error(
            "--width must be an even integer >= 270"
        )

    if args.fps <= 0:
        parser.error("--fps must be positive")

    if not 0 <= args.watermark_opacity <= 1:
        parser.error(
            "--watermark-opacity must be between 0 and 1"
        )

    data_path = Path(args.data)
    data = json.loads(
        data_path.read_text(encoding="utf-8")
    )

    muhurta = {}
    muhurta_path = (
        Path(args.muhurta)
        if args.muhurta
        else data_path.with_name("muhu.json")
    )
    if muhurta_path.exists():
        muhurta = json.loads(
            muhurta_path.read_text(encoding="utf-8")
        )

    languages = (
        ["hi", "en"]
        if args.lang == "both"
        else [args.lang]
    )

    for language in languages:
        renderer = ReelRenderer(
            args,
            data,
            language,
            muhurta=muhurta,
        )

        output = Path(args.out)

        if args.lang == "both":
            output = output.with_name(
                output.stem
                + "_"
                + language
                + output.suffix
            )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if args.preview:
            for index, scene in enumerate(
                renderer.scenes
            ):
                frame = renderer.frame(
                    index,
                    scene["duration"] * 0.8,
                )

                preview = output.parent / (
                    f"preview_{language}_"
                    f"{index + 1}_{scene['kind']}.png"
                )

                frame.save(preview)
                print("Saved", preview)

            continue

        frame_count = round(
            renderer.duration * args.fps
        )

        # TemporaryDirectory cleans intermediate frames
        # even if FFmpeg fails.
        with tempfile.TemporaryDirectory() as temporary:
            print(
                f"Rendering {language}: "
                f"{frame_count} frames, "
                f"{renderer.duration:.2f} seconds"
            )

            for index in range(frame_count):
                renderer.render(index).save(
                    f"{temporary}/{index:05d}.jpg",
                    quality=94,
                )

                if index % args.fps == 0:
                    print(
                        f"\rFrames: {index}/{frame_count}",
                        end="",
                        flush=True,
                    )

            print()

            command = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(args.fps),
                "-i",
                f"{temporary}/%05d.jpg",
            ]

            if not args.silent:
                if args.audio and Path(args.audio).exists():
                    command += [
                        "-stream_loop",
                        "-1",
                        "-i",
                        str(args.audio),
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-af",
                        f"afade=t=in:st=0:d=1.5,afade=t=out:st={renderer.duration - 1.5}:d=1.5",
                    ]
                else:
                    audio_path = (
                        Path(temporary) / "sound.wav"
                    )

                    create_audio(
                        audio_path,
                        renderer.duration,
                        renderer.starts,
                    )

                    vo_clips = []
                    if getattr(args, "voiceover", "none") != "none":
                        try:
                            vo_clips = synthesize_voiceover_clips(renderer, data, voice=args.voiceover, temp_dir=temporary)
                        except Exception as e:
                            print(f"Voiceover synthesis note ({e}); proceeding with drone audio only")

                    if vo_clips:
                        # 0:v is video frames. 1:a is sound.wav (drone + bells)
                        command += ["-i", str(audio_path)]
                        for _, clip_path in vo_clips:
                            command += ["-i", str(clip_path)]

                        filter_parts = ["[1:a]volume=0.15[bg]"]
                        delayed_labels = []
                        for clip_idx, (scene_idx, _) in enumerate(vo_clips):
                            in_arg_idx = 2 + clip_idx
                            delay_ms = int(renderer.starts[scene_idx] * 1000)
                            lbl = f"vo{clip_idx}"
                            filter_parts.append(f"[{in_arg_idx}:a]adelay={delay_ms}|{delay_ms},volume=1.0[{lbl}]")
                            delayed_labels.append(f"[{lbl}]")

                        mix_inputs = "".join(delayed_labels)
                        filter_parts.append(f"{mix_inputs}amix=inputs={len(vo_clips)}:normalize=0[vo_all]")
                        filter_parts.append("[bg][vo_all]amix=inputs=2:duration=first:normalize=0[aout]")

                        command += [
                            "-filter_complex", ";".join(filter_parts),
                            "-map", "0:v",
                            "-map", "[aout]",
                            "-c:a", "aac",
                            "-b:a", "192k",
                        ]
                    else:
                        command += [
                            "-i",
                            str(audio_path),
                            "-c:a",
                            "aac",
                            "-b:a",
                            "160k",
                        ]

            command += [
                "-t",
                str(frame_count / args.fps),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "18",
                "-movflags",
                "+faststart",
                str(output),
            ]

            subprocess.run(
                command,
                check=True,
            )

        verify_export(
            output,
            renderer.width,
            renderer.height,
            args.fps,
            frame_count / args.fps,
        )

        print("Saved", output)


if __name__ == "__main__":
    main()
