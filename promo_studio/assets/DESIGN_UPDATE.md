# P0.1 Graphics Design Pass

## P0 safety
- Festival artwork is rejected safely when corrupt, oversized, or too large to decode.
- Asset limits are checked before full pixel decode: 40M pixels and 15 MB.
- Timeline labels are positioned above the daylight bar to avoid sunset/end-cap collisions.
- No production artwork uses text below 20 px.

## Design tokens
- Title: 64 px
- Hero/value: 44 px
- Body: 28 px
- Label: 22 px
- Minimum: 20 px

## Components
- Editorial header/footer
- Metric cards with larger values
- Sunrise/sunset timeline with non-overlapping labels
- Vertical Choghadiya list showing the best 3–4 daytime windows
- Festival hero with a gradient lower scrim
- Explicit image passing into FestivalHero; no Pillow private `_image` access

## Fonts
Production uses bundled Noto Sans and Noto Serif for Latin plus Noto Sans/Serif Devanagari. Noto font licensing text is bundled under `promo_studio/assets/fonts/licenses/`.

The graphics layer now exercises Devanagari in the Panchang, Muhurta, Festival and Transit headers. CI continues to require Pillow `raqm` support.

## Location
The raw metadata location remains available in facts, while `location_display` is used for human-facing artwork. If upstream supplies `metadata.location.display_name`, it wins; otherwise the city portion is used.
