# P0.1 binding + graphics update

## Fixed before graphics

- Reject stale `muhurta_data` when its `date` differs from `today.date`.
- Bind `metadata.location.name` into facts and render location context on time posts.
- Normalize Rahu/Ketu to Retrograde at the adapter boundary; upstream Direct values are never displayed.
- Fail clearly when a Siddhanta-shaped payload is missing `today.english`.
- Real-schema tests now use committed fixtures under `tests/fixtures/`.

## Graphics foundation

- Added `promo_studio/graphics/components.py`.
- Header, Footer, MetricCard, TimelineBar, ChoghadiyaTimeline, FestivalHero.
- Panchang uses the daylight timeline with Abhijit and Rahu bands.
- Muhurta uses the eight-slot daytime Choghadiya timeline.
- Festival uses an allowlisted local artwork resolver and safe geometric fallback.
- Transit selection is data-driven rather than Jupiter-first and no longer presents a generic Transit Period card.
- Added bundled Noto Sans/Serif Devanagari fonts.
- Added CI test for Pillow `raqm` support.
- Removed fake Om/placeholder logo rendering; a real mark is loaded only when supplied at `assets/brand/siddhanta_mark.png`.

## Verification

`37 passed` with the supplied Siddhanta fixtures.

No upstream Panchang calculations were modified in this package.
