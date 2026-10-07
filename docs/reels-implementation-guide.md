# Siddhanta Reels: implementation and publishing plan

This is a **staged implementation plan**, not a configured publishing schedule. The project still produces 1080 × 1350 PNG cards and a factual caption hand-off. A separate validated Reel planner and review-only 1080 × 1920 daily storyboard PNG previews now exist (five scenes, cover and contact sheet in both languages). Run the separate command with `--dry-run` to print the plan or `--preview` to write review images. It does not yet make video, fetch fresh exports, run on a timer, or upload to Instagram. Preserve the current card workflow while adding Reels as a separate output channel.

## 1. Editorial plan

### Purpose and Formats
- Aspect ratio: 9:16 vertical video format (1080 × 1920 px).
- Language support: Bilingual English and Hindi (`en` and `hi`).
- Target duration: Exactly 23 seconds storyboarded into 5 timed scenes:
  1. Cover / Hook (3s)
  2. Panchang essentials: Tithi & Nakshatra (5s)
  3. Solar rhythms: Sunrise & Sunset (5s)
  4. Timings: Rahu Kaal & Auspicious window (5s)
  5. Close / Call to action (5s)

### Scene Structure and Constraints
- Background artwork: Vector background `assets/svg/reels-universe.svg`.
- Safe margins: Safe margins ensure elements remain visible above social UI overlays (bottom action bars, captions, profile icons).
- Typography & contrast: Text meets minimum WCAG AA contrast ratio (4.5:1) over the background panels.
- Glyph rendering: HarfBuzz and FreeType Devanagari text shaping prevents broken conjuncts and vowel marks in Hindi.
