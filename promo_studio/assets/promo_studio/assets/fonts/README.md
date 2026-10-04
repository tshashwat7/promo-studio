# Siddhanta Promo Studio fonts

The package includes the Devanagari roles required for reliable Hindi shaping:

- `NotoSansDevanagari-Regular.ttf`
- `NotoSansDevanagari-Bold.ttf`
- `NotoSerifDevanagari-Regular.ttf`
- `NotoSerifDevanagari-Bold.ttf`

The bundled Noto Sans/Noto Serif family is the deterministic Latin fallback used by the release renderer.
If the final Siddhanta brand font is selected later, replace/bundle that licensed family and update the golden hashes.

**CI requirement:** Pillow must report `features.check("raqm") == True` so
HarfBuzz/FriBiDi/libraqm shaping is available. Without it, Devanagari can render
incorrectly even though the font itself is present.
