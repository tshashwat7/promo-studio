# P0.1 Siddhanta Workflow Binding + Graphics Update

Promo Studio remains downstream of Siddhanta. The Panchang workflow is not modified.

## P0.1 binding fixes

1. `muhurta_data.date` must exactly match `today.date`; stale windows raise `DataError` and no image is written.
2. `metadata.location.name` is bound into `PostSpec.facts` and time-based posts render `Times for <location>`.
3. Rahu/Ketu motion is normalized to `Retrograde` / `वक्री` in the adapter. The upstream Direct flag is never exposed to captions or graphics.
4. Siddhanta-shaped payloads missing `today.english` fail with a specific `not a Siddhanta payload` error.

Real JSON fixtures live under `tests/fixtures/`, so tests no longer depend on `/mnt/data`.

## Graphics foundation

The renderer now has reusable components under `promo_studio/graphics/components.py`:

- Header / Footer
- MetricCard
- TimelineBar (sunrise → sunset with Abhijit/Rahu bands)
- ChoghadiyaTimeline (8 daytime slots)
- FestivalHero

The old `draw.py` remains a compatibility re-export.

Devanagari fonts are bundled in `assets/fonts/`, and CI verifies Pillow `raqm` support.
A real Siddhanta brand mark can be dropped into `assets/brand/siddhanta_mark.png`.
Festival artwork is resolved only through the explicit allowlist in `festival_assets.py`.

## Post design direction

- Panchang: metric grid + daylight timeline.
- Muhurta: Abhijit/Rahu cards + eight-slot Choghadiya timeline.
- Festival: local allowlisted FestivalHero + compact facts.
- Transit: dynamic featured transit selection; no misleading generic Transit Period card.

No AI image generation is used.
