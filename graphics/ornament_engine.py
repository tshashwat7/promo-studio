"""Resolution-independent SVG motifs created entirely from original geometry."""

import math
from functools import lru_cache

try:
    import svgwrite
except ImportError:
    svgwrite = None
from PIL import Image

from graphics.svg_renderer import rasterize

GOLD = "#DEA75F"
PALE = "#FFE1A9"
RED = "#AC553A"


def _new(size: int = 600):
    if svgwrite is None:
        raise ImportError("svgwrite is required for ornament_engine")
    return svgwrite.Drawing(size=(size, size), viewBox=f"0 0 {size} {size}")


def _polar(cx: float, cy: float, r: float, a: float) -> tuple[float, float]:
    return cx + r*math.cos(a), cy + r*math.sin(a)


def _mandala(size: int = 600) -> str:
    svg = _new(size)
    cx = cy = size/2
    for radius in (70, 131, 190, 247, 276):
        svg.add(svg.circle(center=(cx, cy), r=radius, fill="none", stroke=GOLD,
                           stroke_width=1.8 if radius < 250 else 1))
    for layer, count, r, extent in ((0, 12, 105, 43), (1, 16, 164, 40), (2, 24, 217, 31)):
        for i in range(count):
            angle = (i+layer*.5)*math.tau/count
            x, y = _polar(cx, cy, r, angle)
            svg.add(svg.ellipse(center=(x, y), r=(extent*.55, extent),
                                transform=f"rotate({math.degrees(angle)+90} {x} {y})",
                                fill=RED if layer == 1 else "none",
                                fill_opacity=.22 if layer == 1 else 1,
                                stroke=GOLD, stroke_width=1.7))
    for i in range(48):
        angle = i*math.tau/48
        a, b = _polar(cx, cy, 259, angle), _polar(cx, cy, 276, angle)
        svg.add(svg.line(a, b, stroke=GOLD, stroke_width=2))
    svg.add(svg.circle(center=(cx, cy), r=47, fill=RED, fill_opacity=.35,
                       stroke=PALE, stroke_width=2))
    return svg.tostring()


def _moon(size: int = 600) -> str:
    svg = _new(size)
    center = size/2
    defs = svg.defs
    gradient = svg.radialGradient(id="moon", center=("38%", "38%"), r="68%")
    gradient.add_stop_color(0, "#FFF7DD")
    gradient.add_stop_color(.55, "#D9DACD")
    gradient.add_stop_color(1, "#798894")
    defs.add(gradient)
    svg.add(svg.circle(center=(center, center), r=228, fill="url(#moon)",
                       stroke="#FFF1CF", stroke_width=3))
    for x, y, r in ((187, 175, 23), (333, 213, 40), (244, 300, 48), (382, 385, 29),
                     (160, 383, 19), (330, 130, 15), (411, 290, 18), (278, 436, 32)):
        svg.add(svg.circle(center=(x, y), r=r, fill="#8D9A9A", fill_opacity=.14,
                           stroke="#A1AAA7", stroke_opacity=.5, stroke_width=2))
    for r in (247, 264, 278):
        svg.add(svg.circle(center=(center, center), r=r, fill="none",
                           stroke=PALE, stroke_opacity=.4, stroke_width=1))
    return svg.tostring()


def _temple(size: int = 600) -> str:
    svg = _new(size)
    dark = "#301F26"
    svg.add(svg.polygon(points=[(58, 504), (542, 504), (502, 457), (455, 457),
                                 (423, 390), (365, 390), (332, 262), (300, 126),
                                 (268, 262), (235, 390), (178, 390), (146, 457), (99, 457)],
                        fill=dark, stroke=GOLD, stroke_width=3))
    for x in (138, 190, 240, 360, 410, 462):
        svg.add(svg.line((x, 472), (x, 398), stroke=GOLD, stroke_width=3))
    for y, w in ((412, 170), (374, 135), (337, 115), (290, 79), (251, 57)):
        svg.add(svg.line((300-w, y), (300+w, y), stroke=GOLD, stroke_width=3))
    svg.add(svg.line((300, 126), (300, 61), stroke=GOLD, stroke_width=5))
    svg.add(svg.polygon(points=[(304, 60), (367, 82), (304, 101)], fill=RED))
    svg.add(svg.path(d="M251 504 V444 A49 49 0 0 1 349 444 V504 Z", fill="#0E1C2A",
                     stroke=GOLD, stroke_width=3))
    for y in (505, 521, 538, 556):
        svg.add(svg.line((34, y), (566, y), stroke=GOLD, stroke_width=3))
    return svg.tostring()


def _lotus(size: int = 600) -> str:
    svg = _new(size)
    for row, n, r in ((0, 11, 145), (1, 9, 99), (2, 7, 47)):
        for i in range(n):
            a = i*360/n + (row*15)
            x, y = _polar(300, 326, r, math.radians(a))
            svg.add(svg.ellipse(center=(x, y), r=(30 if row else 37, 112 if row == 0 else 92),
                                transform=f"rotate({a+90} {x} {y})", fill="#B4413A",
                                fill_opacity=.22 if row == 0 else .5,
                                stroke=GOLD, stroke_width=3))
    svg.add(svg.circle(center=(300, 326), r=62, fill="#7C1F2B", stroke=GOLD, stroke_width=5))
    for r in (229, 256, 281):
        svg.add(svg.circle(center=(300, 326), r=r, stroke=GOLD, stroke_width=2,
                           fill="none", stroke_opacity=.65))
    return svg.tostring()


def _kundli(size: int = 600) -> str:
    svg = _new(size)
    gold = "#C08E53"
    svg.add(svg.rect(insert=(61, 61), size=(478, 478), rx=8, fill="#FFF1D7",
                     fill_opacity=.32, stroke=gold, stroke_width=4))
    svg.add(svg.polyline(points=[(61, 61), (539, 539), (61, 539), (539, 61), (61, 61)],
                         fill="none", stroke=gold, stroke_width=3))
    svg.add(svg.polygon(points=[(300, 61), (539, 300), (300, 539), (61, 300)],
                         fill="none", stroke=gold, stroke_width=3))
    for x, y in ((61, 61), (539, 61), (61, 539), (539, 539)):
        svg.add(svg.circle(center=(x, y), r=11, fill="#A45036", stroke=GOLD, stroke_width=2))
    svg.add(svg.circle(center=(300, 300), r=46, fill="#F4D8AF", stroke=gold, stroke_width=3))
    for i in range(12):
        a = i*math.tau/12
        x, y = _polar(300, 300, 282, a)
        svg.add(svg.circle(center=(x, y), r=4, fill=gold))
    return svg.tostring()


def _zodiac(size: int = 600) -> str:
    svg = _new(size)
    for r in (208, 233, 257, 281):
        svg.add(svg.circle(center=(300, 300), r=r, fill="none", stroke=GOLD,
                           stroke_width=2, stroke_opacity=.85))
    for i in range(12):
        a = i*math.tau/12
        svg.add(svg.line(_polar(300, 300, 232, a), _polar(300, 300, 278, a),
                         stroke=GOLD, stroke_width=2))
        x, y = _polar(300, 300, 248, a+math.pi/12)
        svg.add(svg.circle(center=(x, y), r=3, fill=PALE))
    for i in range(32):
        a = i*math.tau/32
        svg.add(svg.circle(center=_polar(300, 300, 285, a), r=2.3, fill=GOLD))
    return svg.tostring()


def _diya(size: int = 600) -> str:
    svg = _new(size)
    svg.add(svg.path(d="M300 63 C218 171 267 257 300 276 C346 247 371 162 300 63 Z",
                     fill="#F7D998", stroke="#F1AC51", stroke_width=5))
    svg.add(svg.path(d="M300 142 C275 195 293 235 300 245 C323 218 329 183 300 142 Z",
                     fill="#F2A54B"))
    svg.add(svg.path(d="M70 330 Q300 475 530 330 Q492 522 300 538 Q110 522 70 330 Z",
                     fill="#812D2A", stroke=GOLD, stroke_width=8))
    svg.add(svg.path(d="M70 330 Q300 441 530 330", fill="none", stroke=PALE, stroke_width=6))
    for i in range(9):
        x = 144 + i*39
        y = 436 + 48*math.sin((x-144)/386*math.pi)
        svg.add(svg.circle(center=(x, y), r=5, fill=PALE))
    return svg.tostring()


def _planet(size: int = 600) -> str:
    svg = _new(size)
    grad = svg.radialGradient(id="jupiter", center=("31%", "22%"), r="73%")
    for offset, color in ((0, "#F9DFC0"), (.4, "#D5A479"), (.8, "#A76C56"), (1, "#5F494D")):
        grad.add_stop_color(offset, color)
    svg.defs.add(grad)
    svg.add(svg.circle(center=(300, 300), r=252, fill="url(#jupiter)", stroke=PALE, stroke_width=2))
    clip = svg.clipPath(id="disc")
    clip.add(svg.circle(center=(300, 300), r=249))
    svg.defs.add(clip)
    group = svg.g(clip_path="url(#disc)")
    for y, height, color in ((115, 16, "#B48777"), (159, 26, "#E5B895"),
                              (219, 36, "#A87867"), (277, 19, "#F5CF9C"),
                              (326, 41, "#B37962"), (402, 27, "#E2B991"),
                              (465, 20, "#9E715F")):
        group.add(svg.path(d=f"M40 {y} C200 {y-40} 389 {y+height} 563 {y-8}",
                           fill="none", stroke=color, stroke_width=height,
                           stroke_opacity=.75))
    group.add(svg.ellipse(center=(394, 361), r=(50, 21), fill="#AF6861", opacity=.8))
    svg.add(group)
    return svg.tostring()


MOTIFS = {"mandala": _mandala, "moon": _moon, "temple": _temple,
          "lotus": _lotus, "kundli": _kundli, "zodiac": _zodiac,
          "diya": _diya, "planet": _planet}


@lru_cache(maxsize=32)
def ornament(name: str, size: int) -> Image.Image:
    if name not in MOTIFS:
        raise ValueError(f"Unknown SVG motif: {name}")
    return rasterize(MOTIFS[name](), width=size)
