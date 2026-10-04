"""DEV TOOL: regenerate SVG ornament sources and rasterise them to committed PNGs.

    pip install -r requirements-dev.txt
    python tools/build_ornaments.py

Not imported by the runtime. Re-run, review the PNGs, then commit both SVG and PNG.
"""
import math, pathlib
import cairosvg

OUT = pathlib.Path(__file__).parent.parent / "promo_studio" / "assets" / "ornaments"
SRC = OUT / "src"; SRC.mkdir(parents=True, exist_ok=True)
GOLD = "#D9B86C"; GOLD_DEEP = "#B88A3B"
N = 1024; C = N / 2


def f(x): return f"{x:.2f}"


def mandala(petals=24):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {N} {N}" width="{N}" height="{N}" fill="none">']
    for r, w, col in ((500, 5, GOLD_DEEP), (470, 2, GOLD), (390, 3, GOLD), (300, 2, GOLD), (160, 3, GOLD_DEEP), (60, 4, GOLD)):
        parts.append(f'<circle cx="{C}" cy="{C}" r="{r}" stroke="{col}" stroke-width="{w}"/>')
    for ring, (length, width, col) in enumerate(((150, 56, GOLD), (110, 38, GOLD_DEEP))):
        n = petals if ring == 0 else petals // 2
        r0 = 305 if ring == 0 else 170
        for i in range(n):
            a = 360.0 * i / n + (0 if ring == 0 else 180.0 / n)
            parts.append(
                f'<path transform="rotate({f(a)} {C} {C}) translate({C} {f(C - r0)})" '
                f'd="M0 0 C {f(width/2)} {f(-length*0.35)} {f(width/2)} {f(-length*0.75)} 0 {f(-length)} '
                f'C {f(-width/2)} {f(-length*0.75)} {f(-width/2)} {f(-length*0.35)} 0 0 Z" '
                f'stroke="{col}" stroke-width="3"/>')
    for i in range(petals):
        a = math.tau * i / petals
        x, y = C + 470 * math.cos(a), C + 470 * math.sin(a)
        parts.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="7" fill="{GOLD}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    (SRC / "mandala_full.svg").write_text(mandala(), encoding="utf-8")
    for svg in sorted(SRC.glob("*.svg")):
        cairosvg.svg2png(url=str(svg), write_to=str(OUT / f"{svg.stem}.png"), output_width=N, output_height=N)
        print("rendered", svg.stem)


if __name__ == "__main__":
    main()
