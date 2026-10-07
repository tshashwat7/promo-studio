"""Draw original Capricorn and Aquarius sun medallions as SVG and small WebP assets.

Run from the repository root: python -m graphics.generate_zodiac_medallions
The SVGs are the editable originals; the WebPs match the scale of the supplied
zodiac illustrations. Neither illustration is derived from a festival scene.
"""

from math import cos, pi, sin
from pathlib import Path

from PIL import Image

from graphics.svg_renderer import rasterize


ROOT = Path(__file__).resolve().parent.parent / "assets" / "icons"
INK = "#492106"


CAPRICORN = f"""
  <!-- Sea-goat: horned goat forequarters, hooves, and a coiled fish tail. -->
  <path fill="{INK}" d="M30 56 Q28 47 36 44 Q43 42 49 47 L59 54
      Q67 54 70 48 Q75 44 79 48 Q74 49 73 54 Q73 62 65 65
      Q59 66 57 61 L49 59 Q43 66 36 65 L31 62 Z"/>
  <path fill="{INK}" d="M32 52 Q24 49 22 43 Q23 39 28 38
      Q33 37 37 42 L40 46 L36 53 Z"/>
  <path fill="{INK}" d="M26 41 Q21 36 22 30 Q25 35 29 37
      Q26 29 30 25 Q30 34 35 40 Z"/>
  <path fill="{INK}" d="M31 61 L33 74 L30 75 L27 64 Z
      M41 62 L45 74 L42 75 L36 65 Z"/>
  <path fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"
      d="M65 61 Q77 70 75 77 Q73 83 65 80 Q60 78 62 73
         Q65 69 70 73 M68 78 Q78 75 82 70"/>
  <path fill="{INK}" d="M77 70 Q82 65 84 64 Q83 71 80 73 L84 76
      Q79 78 75 75 Z"/>
  <circle cx="27" cy="44" r="1.3" fill="#F6DA98"/>
"""


AQUARIUS = f"""
  <!-- Water-bearer holding a tilted amphora, with flowing water below. -->
  <circle cx="38" cy="35" r="6" fill="{INK}"/>
  <path fill="{INK}" d="M34 43 Q40 40 44 43 L51 53 L47 58 L43 53
      L45 66 L38 66 L35 54 L31 63 L26 60 L31 47 Z"/>
  <path fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"
      d="M38 64 L33 76 L28 78 M44 65 L50 76 L56 77
         M35 46 L51 40 L57 42 M32 47 L26 53 L29 59"/>
  <path fill="{INK}" d="M53 38 Q60 34 66 39 L71 48 Q69 54 61 55
      L55 50 Z"/>
  <path fill="none" stroke="{INK}" stroke-width="2" d="M54 41 Q48 44 52 48 L56 47
      M66 40 Q72 38 75 43 Q76 47 71 48"/>
  <path fill="none" stroke="{INK}" stroke-width="2.8" stroke-linecap="round"
      d="M70 52 Q81 59 70 63 Q61 66 72 70
         M65 56 Q70 61 61 66 Q56 70 66 75"/>
  <path fill="none" stroke="#AC6A16" stroke-width="1.3" stroke-linecap="round"
      d="M74 56 Q82 63 77 69 M59 56 Q59 61 56 64"/>
"""


def medallion(figure: str) -> str:
    rays = []
    for i in range(80):
        angle = 2 * pi * i / 80
        inner = 39 if i % 5 == 0 else 40
        outer = 49 if i % 5 == 0 else 45 if i % 2 == 0 else 43
        x1, y1 = 50 + inner * cos(angle), 50 + inner * sin(angle)
        x2, y2 = 50 + outer * cos(angle), 50 + outer * sin(angle)
        rays.append(f'<path d="M{x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f}" '
                    f'stroke="#BA751A" stroke-width="{0.9 if i % 5 == 0 else 0.55}"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"
        viewBox="0 0 100 100">
      <defs>
        <radialGradient id="gold"><stop stop-color="#FFE4A0"/>
          <stop offset="0.78" stop-color="#F7CE75"/>
          <stop offset="1" stop-color="#E5A638"/></radialGradient>
      </defs>
      {''.join(rays)}
      <circle cx="50" cy="50" r="39.5" fill="#F9E9C1" stroke="#C48627"
          stroke-width="1.4"/>
      <circle cx="50" cy="50" r="36.5" fill="url(#gold)" stroke="#F9D88E"
          stroke-width="1.2"/>
      <circle cx="50" cy="50" r="33.7" fill="none" stroke="#A65D12"
          stroke-width="0.9"/>
      <circle cx="50" cy="50" r="31.5" fill="none" stroke="#FFD778"
          stroke-width="0.7"/>
      {figure}
    </svg>'''


def main() -> None:
    source_dir = ROOT / "zodiac-source"
    source_dir.mkdir(parents=True, exist_ok=True)
    for name, figure in (("makar", CAPRICORN), ("kumbha", AQUARIUS)):
        svg = medallion(figure)
        (source_dir / f"{name}.svg").write_text(svg + "\n", encoding="utf-8")
        large = rasterize(svg, 400)
        image = large.resize((100, 100), Image.Resampling.LANCZOS)
        image.save(ROOT / "festivals" / f"{name}.webp", quality=95, method=6)


if __name__ == "__main__":
    main()
