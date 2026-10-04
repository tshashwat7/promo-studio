"""Static, person-agnostic feature showcases. Always labelled illustrative."""
import math
from ..draw import *
from ..spec import PostSpec
from ..models import post_warnings
from . import register

def _spec(kind): return lambda day: PostSpec(kind, day.date.isoformat(), {}, illustrative=True, warnings=post_warnings(day))

@register("kundli", _spec("kundli"))
def kundli(s):
    im, d = canvas(); header(d, "Your Kundli"); cx, cy, r = W // 2, 620, 250
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=MAROON, width=4)
    for i in range(12):
        a = math.radians(i * 30); d.line((cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r), fill=CREAM_DARK, width=3)
    d.ellipse((cx - 80, cy - 80, cx + 80, cy + 80), fill=CREAM_DARK, outline=GOLD, width=3)
    d.text((W / 2, 930), "D1 • D9 • Dashas • Yogas", font=sans(30, True), fill=MAROON, anchor="ma")
    d.text((W / 2, 985), "Illustrative feature preview", font=sans(22), fill=MUTED, anchor="ma")
    footer(d, "Explore Kundli in Siddhanta"); return im

@register("chakra", _spec("chakra"))
def chakra(s):
    im, d = canvas(); header(d, "Balance Your Inner Energy")
    names = ["Sahasrara", "Ajna", "Vishuddha", "Anahata", "Manipura", "Svadhisthana", "Muladhara"]
    radii = [46, 42, 38, 34, 30, 26, 22]               # uniform-ish radii: no overlap, labels beside circles
    top, step, cx = 280, 120, W // 2 - 120
    for i, (n, r) in enumerate(zip(names, radii)):
        y = top + i * step
        d.ellipse((cx - r, y - r, cx + r, y + r), outline=GOLD, width=4)
        d.text((cx + 90, y), n, font=sans(28, True), fill=MAROON if i % 2 == 0 else MUTED, anchor="lm")
    d.text((W / 2, 1090), "Illustrative feature preview", font=sans(22), fill=MUTED, anchor="ma")
    footer(d, "Explore the seven chakras in Siddhanta"); return im
