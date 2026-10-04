# v3.1 — P0 fixes and P1 items 3–4

## P0
1. **Caption hand-off no longer crashes on JSON.** `caption.py` and `pipeline.py` now build
   facts with `spec.to_dict()["facts"]` (fully thawed: plain dict/list/str). `CaptionInput`
   additionally freezes its own copy, and `to_dict()` returns a fresh JSON-safe copy each call,
   so the hand-off object cannot be mutated through a returned dict.
2. **Two-lane timeline.**
   - Each lane has its own label row directly above its bar: dark text plus a colour swatch.
   - The card sizes itself from the number of lanes (`timeline_height()`); `timeline_bar()`
     returns its bottom edge and grows rather than overflows. Sunrise/sunset stay inside the card.
   - Two windows share a lane only if neither their bars *nor their labels* collide.
   - **Latent v3 bug fixed on the way:** band labels on a maroon band were drawn white on the
     white card, so "Rahu Kaal" was invisible even in the normal one-lane Panchang post.
     The Panchang golden hash changes for that reason.

## P1
3. `choghadiya_policy` is no longer a caption fact. The sentence lives in code as
   `posts/muhurta.py::CHOGHADIYA_POLICY`. Only `choghadiya_excluded_overlapping_rahu` is passed
   when slots were dropped.
4. When every auspicious slot overlaps Rahu Kaal, the Choghadiya card is not drawn and the
   remaining cards use the freed space. `choghadiya_list()` returns `False` and draws nothing
   for an empty list. If nothing Muhurta-specific is left at all (no Abhijit, no Rahu, no slot),
   the selector falls back to Panchang.

## Tests (49 → 70)
- JSON round-trip of `caption_input` and `caption_facts` for **every** post type.
- Overlap exclusion, boundary-touching slots, policy never reaching the caption writer.
- All-excluded Muhurta, empty Choghadiya list, Muhurta -> Panchang fallback.
- Lane planning, card growth, sunrise/sunset inside the card, label ink present for every band,
  two-lane Panchang fits above the footer.
- Golden hashes: Panchang updated; two new edge-layout hashes (Panchang overlap, Muhurta all-excluded).
- Existing pins (Pillow 12.3.0 / FreeType 2.14.3 / libraqm 0.10.5) unchanged.

## Not done in this pass
P1 #5 (long festival names), P2 #8 (Festival whitespace), P2 #9 (Hindi strings — needs a native speaker).
Muhurta all-excluded layout still leaves blank space below the cards.
