# Graphics stack: what was adopted from the proposal, and how

| Proposal | Decision | Why |
|---|---|---|
| Pillow as core renderer | **Kept** | Already the renderer; text always goes through Pillow + raqm so Devanagari shaping is uniform. |
| NumPy procedural backgrounds | **Adopted** (`graphics/background.py`) | Themes: `cream` (flat, = v3), `sunrise` (Panchang), `solar` (Muhurta), `festival_glow` (Festival). Exact arithmetic only (no sin/cos/exp, no RNG) so hashes are stable; verified with SIMD paths disabled. |
| SVG ornaments via CairoSVG | **Adapted** | SVG sources in `assets/ornaments/src/`, rasterised **offline** by `tools/build_ornaments.py` into committed PNGs. Runtime never touches Cairo. First ornament: `mandala_full` (festival fallback hero). |
| svgwrite | Skipped | The tool writes SVG strings directly; fewer dependencies. |
| aggdraw | Skipped | Pillow supersampling is enough; unverified wheel support for Pillow 12.3. |
| Matplotlib | Skipped for now | Font/AA drift between versions would break golden hashes. Draw the few charts in Pillow if needed. |
| OpenCV | Skipped | No current need. |
| Curated deity artwork | Already supported | `festival_assets.py` allowlist + size/pixel limits. Add only images you have rights to. |

## Adding a background theme
Add a `Theme(...)` to `THEMES`, map a post to it in `posts/<kind>.py` (`canvas("theme")`), keep
it light, then add its hash to `GOLDEN_BACKGROUND_HASHES`. Tests enforce text contrast on the darkest pixel.

## Adding an ornament
Add the generator/SVG in `tools/build_ornaments.py`, run it, review the PNG, commit SVG + PNG.
Names must match `[a-z0-9_]+`.
