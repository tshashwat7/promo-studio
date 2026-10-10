# Daily Panchang card: production implementation guide

Canvas: **1080 × 1350 px** (Instagram 4:5). All coordinates below are canvas pixels.
Template art: [assets/templates/active/Serene Ghat Mandala at Dusk.png](../assets/templates/active/Serene Ghat Mandala at Dusk.png).

The card has two layers:

| Layer | Content | Changes daily? |
|---|---|---|
| Static | Template art, logo, brand name, tagline, title "Daily Panchang", footer button | No |
| Dynamic | Date line, place, all fact values, end times, auspicious tags | Yes |

Static text never changes, so it may be pre-composited once by a designer (best kerning) or drawn by code at fixed positions. Dynamic text always goes into **fixed slots**; the structure of the card must not change from day to day.

---

## 1. Grid and protected regions

| Token | Value | Notes |
|---|---|---|
| Content left edge `L` | 190 | Every text element starts here |
| Content right edge `R` | 864 | Temple begins right of this below y≈650 |
| Content width | 674 | |
| Hanging logo | x 84–172 | Circular emblem cropped from the app-tile logo, with a gold ring; sits in the margin |
| Header width limit | x ≤ 740 for y < 330 | Keeps text off the moon |
| Fact zone | y 312–1024 | Distant temples rise from y ≈ 1030 |
| Divider right end | 840 | Keeps rules clear of the temple tree |
| Footer zone | y 1250–1314 | Starts below the diya base (y ≈ 1243) |
| Baseline unit | 4 px | All vertical offsets are multiples of 4 |

Columns inside the fact zone:

| Layout | Columns (x, width) | Gutter |
|---|---|---|
| Full width | (190, 674) | — |
| Two columns | (190, 317), (547, 317) | 40 |
| Three columns | (190, 202), (424, 202), (658, 202) | 32 |

Protected regions (no text, no icon, no wash): moon (x ≥ 740, y < 330), temple (x > 864, y > 600), horizon and water (y > 1024 except footer), diya and lotus (x < 330, y 1040–1243).

**Background wash.** A parchment haze (`#FAEEDA`, 42 % opacity, 36 px Gaussian feather) sits behind the header and fact zone only. It softens cloud texture and the zodiac wheel without forming a visible panel; the moon, temple, sun face, horizon, and diya are unchanged (tested).

## 2. Section structure

Measured with the bundled Lora Bold and Hind (see §4). Implemented in [promo_studio/panchang_card.py](../promo_studio/panchang_card.py).

| # | Section | Layout | y (top–bottom) | Content |
|---|---|---|---|---|
| H1 | Brand | static | 52–140 | Logo medallion 88 px; "Siddhanta" 40 px (no tagline: it repeated "Panchang") |
| H2 | Title | static | baseline 216 | "Daily Panchang", 72 px |
| H3 | Date line | dynamic, 1 line | baseline 270 | `Monday, 5 October 2026 · Ujjain` |
| S1 | Tithi | hero, full width | 116 high | icon · label / value / detail |
| S2 | Nakshatra | hero, full width | 116 high | icon · label / value / detail |
| — | Divider | 2 px | | |
| S3 | Yoga, Karana | 2 columns | 86 high | |
| — | Divider | | | |
| S4 | Sunrise, Sunset, Moonrise | 3 columns | 86 high | |
| — | Divider | | | |
| S5 | Abhijit, Rahu Kaal | 2 columns | 114 high | value + status tag |
| N1 | Time note | dynamic | after S5 | `All times for Ujjain · IST`, 24 px |
| F1 | Button | static | 1250–1314 | "Explore in Siddhanta" (`CTA` constant), left edge at `L` |

Divider gaps are computed once (20 px nominal, 14–36 px allowed) as if every optional section exists, so positions never shift between days.

Why these choices (measured, not guessed):

- **Tithi and Nakshatra are full-width rows.** "Krishna Chaturdashi" is 444 px and "Uttara Bhadrapada" 398 px at 44 px; a 317 px column cannot hold them on one line.
- **Masa moves into the Tithi detail line** (`Ashwin Masa · Until 2:08 AM`). Masa is part of the lunar date, so it reads naturally beside Tithi, and it frees a column.
- **Combined values are split.** No more `Shiva / Vanija` or `6:20 AM / 6:11 PM`; each value gets its own labelled cell.
- **Compact values are 32 px.** "Chatushpada" (200 px) fits a 202 px column and "10:46 AM – 12:15 PM" (300 px) fits 317 px.
- **The time note replaces the footer credit.** It sits with the times it qualifies, over clear sky; the footer holds one action.

Vertical slack: divide equally between divider gaps, at most 36 px each. Never stretch a row's internal spacing. If an optional section is missing (no Abhijit/Rahu), remaining sections keep their positions and the slack stays at the bottom.

## 3. Cell anatomy

Every fact uses the same cell, so the card has exactly two text edges per column: the label edge (after the icon) and the value edge (the cell's left edge).

```
[icon 40]  TITHI                         ← icon + label row; label at x + 52
Krishna Dashami                          ← value, aligned with the icon
Ashwin Masa · Until 2:08 AM              ← detail (hero) or status tag (muhurta)
```
- Icons are 40 × 40, maroon, label baseline at top + 29.
- Hero value (44 px) baseline at top + 82; detail baseline at top + 112.
- Compact value (32 px) baseline at top + 74.
- Status tag baseline at top + 104: **filled dot + "Auspicious"** or **ring + "Inauspicious"**, so status does not depend on colour alone.

## 4. Typography

| Role | Face | Size | Fallback | Colour |
|---|---|---|---|---|
| Brand name | Lora Bold | 40 | — (static) | Maroon |
| Title | Lora Bold | 72 | — (static) | Maroon |
| Date line | Hind Medium | 30 | Place moves to 2nd line at 26 | Ink |
| Label (all) | Hind SemiBold, UPPERCASE, 2 px tracking | 26 | 24 | Label gold |
| Hero value | Lora Bold | 44 | 40 | Maroon |
| Compact value | Lora Bold | 32 | 30 | Maroon |
| Detail | Hind Medium | 24 | 22 | Ink |
| Tag | Hind SemiBold | 22 | — | Status colour |
| Time note | Hind Medium | 24 | 22 | Ink |
| Button | Lora Bold | 28 | — | `#FFF1D8` on maroon |

Rules:

1. **Fonts are bundled** in [assets/fonts](../assets/fonts) with their SIL OFL licences: Lora (variable, rendered at weight 700) and Hind Regular/Medium/SemiBold (Indian Type Foundry; includes Devanagari for future Hindi cards). The Panchang renderer loads only these files and fails if they are missing.
2. **One fallback step only.** If a value still does not fit at the fallback size, raise an error; the pipeline already writes nothing on failure. Never ellipsize and never shrink continuously.
3. **All labels use the same style.** No title-case labels in one row and uppercase in another.
4. Pillow has no tracking option; tracked labels are drawn character by character by `draw_tracked()` in [promo_studio/text_layout.py](../promo_studio/text_layout.py).

## 5. Colour tokens

| Token | Hex | Use |
|---|---|---|
| Maroon | `#702A32` | Title, values |
| Ink | `#2C2928` | Date, detail |
| Label gold | `#8A5418` | Labels, tagline (replaces `#A46423`) |
| Divider | `#C19A66` | 2 px rules (1 px disappears on phones) |
| Auspicious | `#3B5B2A` | Abhijit tag (muted olive, warmer than a traffic-light green) |
| Inauspicious | `#8A2A2A` | Rahu Kaal tag |

Contrast: the original gold `#A46423` on parchment `#F8E6C8` is about 3.9:1, below the 4.5:1 target for small text. `#8A5418` passes against the washed artwork behind each label. `tests/test_panchang_card.py` checks every text item against the **sampled, washed** background under its bounding box.

## 6. Icons

### 6.1 Production requirements

Every fact icon must meet all of these before use:

- [ ] Same family: one stroke weight, corner style, and level of detail.
- [ ] **Transparent background.** No white squares or tinted discs.
- [ ] SVG preferred. Raster only as RGBA PNG/WebP, at least 192 × 192 px (2× the largest display size of 64 px; 3× preferred).
- [ ] Square artboard; glyph within the central 80 % and optically centred.
- [ ] Single colour (label gold or maroon) or a fixed two-tone scheme used by every icon.
- [ ] Meaning matches the fact (see table).
- [ ] Rights to publish confirmed.

### 6.2 Icon set in use

The workspace has illustrations but no production icon set, so an original single-colour line set was drawn for this card: [assets/icons/panchang](../assets/icons/panchang) (`tithi`, `nakshatra`, `yoga`, `karana`, `sunrise`, `sunset`, `moonrise`, `abhijit`, `rahu`). All are 48-unit SVGs with 3-unit round strokes and transparent backgrounds, authored in `#8A5418` and tinted maroon at render time (`ICON_COLOUR`), rasterized at 40 px. Being original work, they carry no third-party rights. A brand designer may replace them with a commissioned set using the same filenames and §6.1.

The older app icons in `assets/icons/ui/` and `assets/icons/planets/` are **not** used: all are RGB without transparency, most are below 192 px, they span several styles, and some have the wrong meaning (`Masa.webp` is an "add event" glyph, `Muhurat Finder.webp` a download arrow).

### 6.3 Code rules

- Icons are mapped by a fixed allowlist (`ICONS` in [promo_studio/panchang_card.py](../promo_studio/panchang_card.py)); paths never come from JSON.
- SVGs are size-limited, must stay inside `assets/`, and are rasterized with `graphics.svg_renderer.rasterize` directly at 40 px; a non-square result is rejected.
- A missing or invalid icon fails the render; nothing is written.

## 7. Data rules

1. Show values exactly as validated; no abbreviations or rewording.
2. **End times after midnight.** Tithi and Nakshatra end times earlier than sunrise belong to the next calendar day (`models.end_date`), shown as `Until 2:08 AM, 6 Oct`; the date is also in the caption input (`tithi_end_date`, `nakshatra_end_date`). Verified on the 5 Oct 2026 data: the night Choghadiya runs to the next sunrise, and Dashami ending at 2:08 AM on 6 Oct is what makes 6 Oct Indira Ekadashi. **Moonrise is not adjusted**: 12:53 AM is the early morning of 5 Oct (a Moon 71° behind the Sun at Ujjain rises near 1 AM and the file's Moonset is 2:42 PM the same day). A Tithi lasting past the following sunrise (vriddhi) cannot be detected from these fields; exporting ISO datetimes upstream would remove that gap.
3. **Auspicious tags come from data.** The adapter validates `is_auspicious` as a boolean for Abhijit and Rahu Kaal; the selector passes it as `abhijit_auspicious` / `rahu_auspicious`. The renderer never hard-codes it.
4. **Date line format:** `{Weekday}, {d} {Month} {yyyy} · {City}` (no leading zero). City is `metadata.location.name` up to the first comma. The engine's own `date_formatted` (`"Monday, 5 Monday 2026"`) is wrong and is not used.
5. **Long city names:** if the date line exceeds 550 px (moon limit) at 30 px, the date stays on line 1 and the city moves to line 2 at 26 px; the fact zone shifts down 32 px and the divider gaps absorb it.
6. Missing optional facts hide their whole section; never show empty labels.
7. **Masa convention.** The engine names months the Purnimanta way ("Ashwin" Krishna precedes Ashwin Amavasya on 10 Oct and Navratri on 11 Oct). The card says `Ashwin Masa (Purnimanta)` so Amanta readers, who call this month Bhadrapada, are not misled. Change `MASA_SYSTEM` if the engine changes.
8. **Cross-checks against the file's own sunrise/sunset** (adapter). A window that contradicts them is omitted from the card and caption input, and the reason is returned in `warnings`:
   - Abhijit must be centred within 5 min of the sunrise–sunset midpoint (true solar noon). The 5 Oct data gives 12:03–12:51 PM, centred on Ujjain's *mean* noon (12:26) instead of solar noon (12:15), so it is 12 min late and is omitted. Expected from the same sunrise/sunset: 11:51 AM–12:39 PM. **Fix upstream** (apply the equation of time).
   - Rahu Kaal must match its weekday's eighth of daylight within 2 min. It does (Monday, 2nd eighth: 7:48–9:17 AM), as do Yamaganda, Gulika, Brahma and Godhuli.
   - `data.json` and `muhu.json` must give the same latitude and longitude, or generation is refused.

## 7a. Hindi card

Same grid, slots, icons, colours, wash and tests; only text and type change (`HINDI` in [promo_studio/panchang_card.py](../promo_studio/panchang_card.py)). Generate with `python generate_daily.py --language hi`; the file is `{date}_panchang_hi_1080x1350.png`. Hindi is refused for other card types.

- **Shaping.** This Pillow build has no libraqm, so Devanagari is shaped with HarfBuzz and drawn from FreeType masks ([promo_studio/shaping.py](../promo_studio/shaping.py)); conjuncts, reph and the pre-base ि matra render correctly. A test fails if any string would show a missing-glyph box.
- **Fonts.** Martel ExtraBold (brand, title) and Martel Bold (values, button) — a Devanagari serif matching Lora; Hind SemiBold/Medium for labels, tags, date and details. All OFL, bundled under `assets/fonts/`.
- **Sizes.** Devanagari reads larger than Latin at the same size, so Hindi uses title 64, hero values 36 (fallback 34), compact values 30 (28), details 22. Hero rows are 124 px tall (English 116) to clear vowel signs above and below the headline. Labels are not letter-spaced (tracking breaks the शिरोरेखा).
- **Optical alignment.** Shaped text is aligned by its ink, so matras like ि do not hang left of the content edge.
- **Values come from `today.hindi`.** Tithi = `paksha` + `tithi_name` (`कृष्ण पक्ष दशमी`); Nakshatra, Yoga, Karana and Masa use their Hindi fields. Times stay exactly as the engine writes them in its Hindi output (`6:20 AM`).
- **Card text (translations, review with a native editor):** सिद्धान्त, दैनिक पंचांग (both from the engine's own Hindi caption), labels तिथि / नक्षत्र / योग / करण / सूर्योदय / सूर्यास्त / चंद्रोदय, muhurta names from `name_hi` (अभिजित मुहूर्त, राहुकाल), tags शुभ / अशुभ (the engine's `quality_hi`), `समाप्ति:` for end times, `{मास} मास (पूर्णिमांत)`, note `सभी समय {city} के अनुसार · IST`, button `सिद्धान्त पर देखें`.
- **Date line.** Weekday and month names come from fixed tables whose spellings match the engine's `hindi.date_formatted` (`5 अक्टूबर 2026, सोमवार`). The engine gives no Hindi place name, so `HINDI_CITIES` maps known cities (Ujjain → उज्जैन); any other city is shown in English rather than guessed.

## 7b. Shared card kit

[promo_studio/card_kit.py](../promo_studio/card_kit.py) holds everything common to the daily cards: colours, bundled fonts, English/Hindi `Language` settings, shaped Devanagari, the icon/label/value cell, the header (which moves the date down if a title descender such as ू in मुहूर्त would touch it), the CTA button, the wash and the logo medallion. Card modules ([panchang_card.py](../promo_studio/panchang_card.py), [muhurta_card.py](../promo_studio/muhurta_card.py)) only define their own layout. Moving Panchang onto the kit left both Panchang golden images byte-identical.

## 7c. Plan Your Day (Muhurta) card

Template [plan_day_template.webp](../assets/templates/active/plan_day_template.webp); selected on Tuesdays and Thursdays; `--language en|hi`.

**Data checks (adapter).** Verified on the 5 Oct 2026 export:
- Day Choghadiya: 8 slots in the weekday's fixed order (Monday: Amrit, Kaal, Shubh, Rog, Udveg, Chal, Labh, Amrit), quality labels matching the names, and times dividing sunrise–sunset into equal eighths (≤ 1 min error). Any failure empties the list, so that day falls back to the Panchang card.
- Yamaganda and Gulika match their weekday eighths, like Rahu Kaal. Abhijit uses the solar-noon check (§7.8).
- **Engine bug:** the *night* Choghadiya repeats the day cycle (Monday night given as Chal, Labh, Amrit…; correct is Chal, Rog, Kaal, Labh, Udveg, Shubh, Amrit, Chal). It is reported as a warning; no card shows night slots.
- The engine names Yamaganda “Yamaghanta” (Hindi यमगण्ड). Window labels come from the data (`name_en`/`name_hi`), so the engine's spelling is shown; ask the data owner to correct it.

**Selection.** The card needs the 8 validated day slots and Rahu Kaal. Abhijit, Yamaganda and Gulika are optional; a missing one leaves its slot empty without moving the others.

**Layout.**
- Header from the kit; title “Plan Your Day” / “आज के मुहूर्त”. Header text may run to x 900 (pillar from x ≈ 990).
- **Timeline:** label “Today's Choghadiya”, then a 20 px bar from x 190 to 864 split proportionally by the slot times, coloured by the source quality (Best `#3B5B2A`, Auspicious `#6F8A3C`, Neutral `#C9A66B`, Inauspicious `#8A2A2A`), with sunrise and sunset times and icons at its ends.
- **Slots:** 8 rows in two time-ordered columns (morning left, afternoon right). Each: colour swatch, slot name (value font), quality in tracked label gold, and the time range. Hindi rows are 72 px (English 64) for vowel signs.
- **Windows:** fixed 2 × 2 cells — Abhijit, Rahu Kaal / Yamaganda, Gulika — with icons (new `yamaganda` hourglass and `gulika` ringed-planet SVGs) and data-driven शुभ/अशुभ tags.
- Time note, then the shared CTA button. Everything must end by y 1060 (distant temples from y ≈ 1090), or generation fails.

**Tests** ([tests/test_muhurta_card.py](../tests/test_muhurta_card.py)) use the frozen 5 Oct export moved to Tuesday 6 Oct with internally consistent windows and Choghadiya, so the card's own logic is tested even though the real 6 Oct data has not arrived. They cover exact values in both languages, the proportional timeline, geometry and a long city name, a hidden invalid window, the fallback on a wrong Choghadiya order, contrast, bundled fonts, glyph coverage, and English and Hindi golden images.

Any validated card can be made for any date with `--card panchang|muhurta|transit` (default `auto` = weekday rotation); a forced card whose data failed validation stops with an error. A missing Muhurta window closes up the grid rather than leaving a hole.

## 7d. Today's Sky (Transit) carousel

Template [transit_template.webp](../assets/templates/active/transit_template.webp); selected on Fridays; `--language en|hi`. Two slides are written as `{date}_transit{_hi}_1_1080x1350.png` and `_2_`; the result's `paths` lists them in posting order (`path` is the cover).

**Data checks (adapter).** All nine grahas must be present and pass, or positions are emptied with a warning and Friday falls back to Panchang:
- `rashi_index` 0–11 with matching `rashi_en`/`rashi_hi`, `degree_in_rashi` 0–30, and `longitude_total` = index × 30 + degree (± 0.02°).
- `motion_en` agrees with `is_retrograde`; the Sun and Moon are never retrograde. Rahu/Ketu are always set to retrograde (the engine says Direct).
- Ketu exactly opposite Rahu (± 0.1°); Mercury within 28.5° and Venus within 47.5° of the Sun.
- Sun and Moon rashi equal the Panchang's `sun_rashi`/`moon_rashi`.
- Tropical Sun for the date (low-precision formula) minus the file's Sun is 23–25.5°, i.e. the positions are sidereal and for this day.
- Each major transit must match today's rashi and motion and contain the date between ingress and egress, or it is dropped with a warning.
- **Moon-sign lists.** `benefited_rashis_*` must be exactly the signs from which the planet stands in its classical favourable houses (Sun 3/6/10/11, Moon 1/3/6/7/10/11, Mars and Saturn 3/6/11, Mercury 2/4/6/8/10/11, Jupiter 2/5/7/9/11, Venus 1/2/3/4/5/8/9/11/12, Rahu and Ketu 3/6/10/11), `challenged_rashis_*` the other signs, and the Hindi lists the same signs in the same order. Otherwise the lists are dropped with a warning and slide 1 shows no grid. The 5 Oct export failed for Mars (Virgo missing) and Ketu (Sagittarius instead of Scorpio); the fixed 6 Oct export passes.

Both exports pass the position checks (6 Oct: Sun +0.99°, Moon +13.9° and in Ashlesha, matching the Panchang).

**Layout.**
- Kit header on both slides; title “Today's Sky” / “आज का गोचर” (“Planet Transits” is too wide for the clear parchment). Text ends by x 610 above y 500 and x 680 below it (the night sky recedes), and by y 1100 (river scene).
- **Slide 1, the story.** Hero: “Current transit” (“Enters today” on the ingress date) with the featured planet's art, the major transit with the latest ingress (“Mars in Cancer” / “मंगल कर्क राशि में”) and its ingress–egress dates. Then “By Moon sign”: a legend and all twelve signs in zodiac order in a 3 × 4 grid. Each sign has a decorative 48 px sun medallion above its name; favourable signs have a filled green dot and semibold green name, the rest a red ring (shape and colour, never colour alone). Then “Swipe for all nine planet positions ›”. The medallions do not imply calculated planetary positions.
- **Zodiac art** is curated by English sign name in `card_kit.ZODIAC_ART`, never from input paths. Ten supplied medallions have opaque cream square corners; the renderer masks them to soft-edged circles. Original sea-goat (`makar.webp`) and water-bearer (`kumbha.webp`) medallions complete the set; their editable SVG originals live in `assets/icons/zodiac-source/` and are generated by `graphics.generate_zodiac_medallions`.
- **Slide 2, the reference.** Hero: “Moon today” with the Moon's sign and today's nakshatra (changes daily, unlike the featured transit), then **Sidereal positions** (“निरयण ग्रह स्थिति”): nine 54 px rows in fixed columns (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu): 34 px planet art, source name, rashi, whole degree (Hind has no ′ glyph), and the source motion text (“Retrograde” / “वक्री”, title case like other tags) only when retrograde.
- **Planet art** is the curated set in `assets/icons/planets/`. Each file sits on an opaque near-white tile, so `card_kit.planet_image` keys the tile out at render time (spheres keep their colours; the Rahu/Ketu glyphs are tinted maroon like the icons). A test fails if any corner stays opaque.
- **Closing paragraph, no button** (both slides). One parchment panel over the river (the water alternates bright reflections and dark ripples, so bare text cannot stay legible): the bold hook “Every Kundli feels this transit differently.” / “हर कुंडली पर इस गोचर का असर अलग होता है।” followed by “Add your birth details in Siddhanta for your personal transit reading.” / “सिद्धान्त में जन्म विवरण डालें और अपना व्यक्तिगत गोचर फल देखें।”, word-wrapped to the panel (`card_kit.wrap`). The panel grows upward from y 1322. The card makes no prediction beyond the validated sign lists; planet dignities and the engine's yoga texts are not shown (the Gajakesari text says “1th house”).

**Tests** ([tests/test_transit_card.py](../tests/test_transit_card.py)) use the fixed-engine 6 Oct export (`tests/fixtures/*-2026-10-06.json`) with `card="transit"`: exact values on both slides in both languages, the Moon-sign grid, wrong and mistranslated sign lists (the 5 Oct export), the ingress-day label, the closing paragraph, six kinds of impossible position, a contradicting major transit, the Friday fallback, geometry with a long city, contrast (including text on the panel), fonts, glyph coverage, numbered slide files, and four golden images.

## 7e. Kundli feature preview

Saturday's Kundli card is an **illustrative promotion**, not a computed chart. The Saturday selector supplies empty facts and `illustrative=True`. It uses the muted temple backdrop and a twelve-section ornament without houses, signs, grahas or predictions. The centre is explicitly marked `SAMPLE` / `नमूना`; the English/Hindi disclaimer says the diagram is not a calculated birth chart. Four feature labels name Lagna, Navamsa, Dasha and Yogas without displaying any user-specific results. All text uses measured bundled fonts, and the shared logo and footer button. Both language variants render from [kundli_card.py](../promo_studio/kundli_card.py); no birth details are required or inferred. The curated card does not receive the older pipeline's extra preview label, which overlapped its lower feature row.

Tests in [test_kundli_card.py](../tests/test_kundli_card.py) cover both language paths, exact static copy, glyph coverage, feature boundaries, fact independence, the pipeline output and reviewed golden images. The Wednesday Chakra promotion ([chakra_card.py](../promo_studio/chakra_card.py)) uses the same kit header and button over the decorative meditating figure, with Sanskrit chakra names in Hindi and an “illustrative guide, not a personal assessment” line; [test_chakra_card.py](../tests/test_chakra_card.py) covers both languages.

## 7f. Festival card

Chosen whenever `today.festivals_today` is non-empty (the first entry); the six-card preview also renders the next major upcoming festival. Implemented in [festival_card.py](../promo_studio/festival_card.py), `--language en|hi`.

- **Scene and panel.** The scene comes from `FESTIVAL_ART` by exact name (else the neutral scene). Each scene has a fixed panel in its clear sky, `SCENE_PANELS` (left, top, right, lowest bottom), measured so the deity is not covered (edge density under every panel is a fraction of the scene's). The panel uses the kit parchment (alpha 235) because Shivratri and Krishna are night scenes.
- **Content, top to bottom:** logo medallion beside “FESTIVAL TODAY” / “आज का पर्व” (or “UPCOMING FESTIVAL” / “आगामी पर्व”); the name in the title face (60/52 px EN, 54/46 px HI, at most two lines; “(Start)” reads “Begins” in English); weekday, date and city; then Tithi and Nakshatra, or the countdown (“Today”, “Tomorrow”, “In 5 days”); the “Explore in Siddhanta” button. The panel grows to fit but never past the scene's lowest bottom, read off each scene so the deity, lamps, garlands and temples stay visible. Vishnu fills his scene, so his panel is the sky band above the serpent hoods (y ≤ 416) with a **one-band layout** used for any panel at least 640 px wide inside: button beside the label, Tithi and Nakshatra side by side. If the copy would pass the limit (only a two-line city beside the Shivratri lamps or Holi's domes), the card moves to the neutral scene's panel rather than covering the artwork. Festivals without a deity scene always use the neutral scene: the small festival icons in `assets/icons/festivals/` are too small for a full-size post.
- **Ritual windows are not shown.** The 6 Oct export gives Indira Ekadashi a “Parana Time 6:20–8:41 AM” on the fast day itself; Parana (breaking the fast) belongs to the next morning, so printing it would mislead. The adapter does not pass ritual windows.

Tests ([test_festival_card.py](../tests/test_festival_card.py)): exact EN/HI values from the 6 Oct export, Parana absent, countdown wording, a panel for every mapped scene, geometry for every mapped name on its own scene (both languages, short and long city, today and upcoming), the neutral-scene fallback, contrast, over-long names refused, the Hindi pipeline file, and four golden images.

## 8. Implementation order

| Phase | Work | Status |
|---|---|---|
| 0 | Bundle fonts; re-measure widths | Done — `assets/fonts/` |
| 1 | Design tokens | Done — constants in `panchang_card.py` |
| 2 | Carry `is_auspicious`; Masa in Tithi detail | Done — `adapter.py`, `selector.py`, `make_cards._mockup_spec` |
| 3 | Fixed-slot section layout | Done — `panchang_card.plan()` |
| 4 | Icon loader, allowlist, icon set | Done — `assets/icons/panchang/` |
| 5 | Header and footer refinements | Done |
| 6 | Tests and golden image | Done — `tests/test_panchang_card.py`, `tests/golden/` |
| 7 | Apply tokens and slot system to Muhurta and Transit | Done (§7c, §7d) |

## 9. Acceptance criteria

### Automated tests

- **Worst-case fixture** renders without error: Tithi `Krishna Chaturdashi`, Nakshatra `Uttara Bhadrapada`, Yoga `Vishkambha`, Karana `Chatushpada`, Masa `Margashirsha`, city `Thiruvananthapuram`, muhurta `10:46 AM – 12:15 PM`.
- **Geometry:** every text and icon bounding box lies inside its slot, inside x 190–864, and outside all protected regions; no two boxes overlap.
- **Minimum sizes:** no label below 24 px, no value below the fallback in §4.
- **Contrast:** each text box ≥ 4.5:1 against the sampled background.
- **No truncation:** each rendered string equals its source fact.
- **Missing data:** no Abhijit/Rahu → S5 hidden, other sections unchanged.
- **Golden image:** [tests/golden/panchang-2026-10-05.png](../tests/golden/panchang-2026-10-05.png) is the approved render of the real fixture; new renders must match within a mean channel difference of 1.0. After an intentional design change, review the new render and replace the golden file.

### Manual review before each template change

- [ ] View at 375 px wide (phone) — all labels readable.
- [ ] Check the profile-grid crop (centre 1012 × 1350) — no content lost.
- [ ] Icons look like one family at both 64 and 32 px.
- [ ] Moon, temple, sun, and diya remain unobstructed.
- [ ] Archive renders show their actual date and never imply "today".
