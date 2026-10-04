# Reproducible rendering stack

Release golden images are pinned to (asserted by the test suite):

- Pillow 12.3.0 · FreeType 2.14.3 · libraqm 0.10.5
- NumPy 2.4.4 (procedural backgrounds)

**Runtime needs only Pillow + NumPy.** CairoSVG / libcairo is a *development-only* tool
(`requirements-dev.txt`) used by `tools/build_ornaments.py` to rasterise SVG ornaments into
committed PNGs. A test asserts it is never imported by the pipeline.

If you intentionally change any pinned component, regenerate and review the golden hashes.
