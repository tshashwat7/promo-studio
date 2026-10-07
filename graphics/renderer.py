"""Pillow compositing canvas shared by six independently themed cards."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from graphics.background_engine import BackgroundEngine
from graphics.effects import flourish, shadow_panel
from graphics.ornament_engine import ornament

try:
    from make_post import HindiText, find_font
except ImportError:
    # Graceful fallback if make_post is not on sys.path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from make_post import HindiText, find_font

W, H = 1080, 1350
PAPER = "#FFF1D8"
WINE = "#82272A"
GOLD = "#C58A42"
INK = "#382B29"
MUTED = "#826F63"
NAVY = "#102638"


class Canvas:
    def __init__(self, hindi_font: Path, theme: str = "plan"):
        self.image = BackgroundEngine.create(theme, W, H)
        self.draw = ImageDraw.Draw(self.image)
        self.hindi = HindiText(hindi_font)
        self.regular = find_font([r"C:\Windows\Fonts\georgia.ttf",
                                  "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"])
        self.bold = find_font([r"C:\Windows\Fonts\georgiab.ttf",
                               "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"])
        self.sans = find_font([r"C:\Windows\Fonts\segoeui.ttf",
                               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
        self.dark = theme in {"panchang", "chakra", "transit"}
        border = "#9D855F" if self.dark else "#CBAC7C"
        self.draw.rounded_rectangle((20, 20, W-20, H-20), radius=8, outline=border, width=2)
        self.draw.rounded_rectangle((31, 31, W-31, H-31), radius=6, outline=border, width=1)
        self.motif("mandala", 795, -77, 370, opacity=.14 if self.dark else .19)
        self.brand()

    def text(self, value: str, x: int, y: int, size: int = 30,
             color: str | None = None, bold: bool = False, sans: bool = False,
             max_width: int | None = None) -> None:
        path = self.sans if sans else self.bold if bold else self.regular
        font = ImageFont.truetype(str(path), size)
        if max_width:
            while size > 18 and self.draw.textbbox((0, 0), value, font=font)[2] > max_width:
                size -= 2
                font = ImageFont.truetype(str(path), size)
        self.draw.text((x, y), value, font=font, fill=color or (PAPER if self.dark else INK))

    def centered(self, value: str, y: int, size: int = 30,
                 color: str | None = None, bold: bool = False) -> None:
        font_path = self.bold if bold else self.regular
        font = ImageFont.truetype(str(font_path), size)
        while size > 18 and self.draw.textbbox((0, 0), value, font=font)[2] > 895:
            size -= 2
            font = ImageFont.truetype(str(font_path), size)
        width = self.draw.textbbox((0, 0), value, font=font)[2]
        self.draw.text(((W-width)//2, y), value, font=font,
                       fill=color or (PAPER if self.dark else INK))

    def hi(self, value: str, x: int, baseline: int, size: int = 32,
           color: str | None = None) -> None:
        self.hindi.draw(self.image, x, baseline, value, size,
                        color or (PAPER if self.dark else INK))

    def motif(self, name: str, x: int, y: int, size: int, opacity: float = 1) -> None:
        art = ornament(name, size).copy()
        if opacity < 1:
            art.putalpha(art.getchannel("A").point(lambda a: int(a * opacity)))
        self.image.alpha_composite(art, dest=(x, y))

    def panel(self, box: tuple[int, int, int, int], fill: str = "#FFF1D8",
              outline: str | None = None, radius: int = 28) -> None:
        shadow_panel(self.image, box, radius=radius, fill=fill, outline=outline)

    def brand(self) -> None:
        d = self.draw
        d.ellipse((64, 59, 158, 153), fill=NAVY, outline=GOLD, width=3)
        self.motif("mandala", 71, 67, 78, opacity=.95)
        self.text("Siddhanta", 180, 61, 57, PAPER if self.dark else WINE, True)
        self.text("Jyotish Panchang", 184, 119, 26,
                  "#DBAE74" if self.dark else "#B67642", sans=True)
        d.line((66, 176, 1014, 176), fill=GOLD, width=2)
        d.ellipse((536, 171, 544, 179), fill=GOLD)

    def footer(self, text: str, *, cta: bool = False) -> None:
        if cta:
            self.panel((86, 1220, 994, 1295), fill=WINE, radius=17)
            self.centered(text, 1239, 30, PAPER, True)
        else:
            self.draw.line((83, 1220, 997, 1220), fill=GOLD, width=2)
            self.centered(text, 1250, 25, "#FFE2AE" if self.dark else MUTED)

    def flourish(self, x: int, y: int, scale: float = 1) -> None:
        flourish(self.image, x, y, scale, "#CB995D")
