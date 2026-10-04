# v3.2 — procedural backgrounds + pre-rendered SVG ornaments

- New: `graphics/background.py` (BackgroundEngine), `graphics/ornaments.py`, `tools/build_ornaments.py`,
  `assets/ornaments/` (SVG source + committed PNG), `requirements-dev.txt`, `GRAPHICS_STACK.md`.
- Panchang -> `sunrise`, Muhurta -> `solar`, Festival -> `festival_glow`; Transit/Kundli/Chakra stay flat cream.
- Festival fallback hero uses the vector mandala instead of Pillow line-art.
- Footer right-hand text now uses `MUTED_DEEP` (#5E554D): the old muted tone fell to 3.5:1 on the warm
  backgrounds. This changes the footer on **all six** posts, so all six golden hashes were regenerated.
- NumPy pinned (2.4.4). CairoSVG is dev-only.
- Tests 70 -> 94: determinism, per-theme golden hashes, contrast floors, theme mapping, ornament safety
  (no path traversal), SVG/PNG sync, CairoSVG-not-imported, NumPy pin.

Known limits: hash stability verified on x86-64 only (SIMD paths disabled to simulate other CPUs); not tried
on ARM. The footer divider line is faint on the warm backgrounds. Items still open: festival long names (P1 #5),
Festival whitespace (P2 #8), Hindi string review (P2 #9).
