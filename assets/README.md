# Asset library

This is a **copy** of the 214 files in `../mockup/`; originals remain in place. Image and SVG bytes are unchanged. Curated rendering in `promo_studio/mock_art.py` now loads templates, festival scenes and the logo from here; the other copies remain available for future use.

- `templates/active/`: the four template images currently named in `TEMPLATES` (one temple template is shared by Kundli and Chakra).
- `templates/reference/`: additional poster/template source images not directly selected by the renderer.
- `content/festivals/`: festival scenes, including the neutral fallback, a Krishna scene used for Janmashtami, and Hanuman and Holi scenes mapped to Hanuman Jayanti and Holi. A scene's presence here does not mean it is approved or mapped to a festival.
- `content/chakras/`: chakra illustration assets.
- `content/backgrounds/`: remaining background/scene images.
- `branding/`: logo.
- `icons/festivals/`, `icons/planets/`, `icons/ui/`, `icons/ui/home/`: copied from the respective `mockup/icons/` collections. These are not the full-size festival scenes used by the renderer.
- `svg/`: SVG artwork.
- `svg/reels-universe.svg`: original, editable 1080 × 1920 vector universe background for all daily Reel preview scenes; its opaque inset reserves space for source-specific text. Decorative celestial orbs and stars do not represent calculated planetary positions. The preview renderer rasterizes this artwork through the existing SVG engine; it is not a video or a publishing asset.
- `fonts/`: Lora, Hind and Martel (Devanagari serif for the Hindi card) from the official Google Fonts repository, each with its SIL OFL licence; loaded by the Panchang card.
- `icons/panchang/`: original single-colour SVG fact icons drawn for the Panchang card (not copied from `mockup/`).
- `icons/festivals/makar.webp` and `icons/festivals/kumbha.webp`: original Capricorn sea-goat and Aquarius water-bearer sun medallions; editable vector originals live in `icons/zodiac-source/` and can be regenerated with `python -m graphics.generate_zodiac_medallions`. The other ten sign medallions are supplied assets. `Makar Sankranti.webp` is a separate festival illustration and is not a zodiac sign.
- `archives/`: the original icon ZIP, retained as provided; its contents were not expanded.

Festival scenes in the curated renderer are selected by Siddhanta festival `id` in `FESTIVAL_ART`, so English/Hindi name variations share one mapping; unknown IDs use the neutral fallback. Review any new mapping against the actual artwork content before use. The JSON `image.local_asset_path` used by the procedural fallback refers to a separate, approved asset location and is not populated by these copies.
