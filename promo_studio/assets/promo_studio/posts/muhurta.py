from ..draw import *
from ..spec import PostSpec
from ..models import post_warnings
from . import register

def _minutes(value: str) -> int:
    from datetime import datetime
    parsed = datetime.strptime(value.strip().upper(), "%I:%M %p")
    return parsed.hour * 60 + parsed.minute


def _overlaps(start: str, end: str, other_start: str, other_end: str) -> bool:
    a, b = _minutes(start), _minutes(end)
    c, d = _minutes(other_start), _minutes(other_end)
    if b <= a: b += 1440
    if d <= c: d += 1440
    return max(a, c) < min(b, d)


# Presentation-only policy (documentation, NOT a caption fact). Never claim that an
# auspicious Choghadiya window overrides Rahu Kaal: featured slots that overlap Rahu
# are omitted from the card. This sentence must never be passed to the caption writer.
CHOGHADIYA_POLICY = (
    "Auspicious Choghadiya windows overlapping Rahu Kaal are omitted from the featured list; "
    "this is a presentation filter, not a Jyotish judgement."
)


def build(day):
    if not (day.abhijit or day.rahu_kaal or day.choghadiya):
        return None
    f = {"weekday": day.weekday, "date": day.date.isoformat(),
         "tithi": f"{day.paksha.title()} {day.tithi}", "nakshatra": day.nakshatra}
    if day.location: f["location"] = day.location
    if day.location_display: f["location_display"] = day.location_display
    if day.abhijit: f["abhijit"] = f"{day.abhijit.start} – {day.abhijit.end}"
    if day.rahu_kaal: f["rahu"] = f"{day.rahu_kaal.start} – {day.rahu_kaal.end}"

    if day.choghadiya and isinstance(day.choghadiya.get("day"), list):
        candidates = [dict(x) for x in day.choghadiya["day"]
                      if isinstance(x, dict) and x.get("is_auspicious")]
        excluded = []
        if day.rahu_kaal:
            kept = []
            for slot in candidates:
                if slot.get("start") and slot.get("end") and _overlaps(
                    str(slot["start"]), str(slot["end"]), day.rahu_kaal.start, day.rahu_kaal.end
                ):
                    excluded.append({"name_en": slot.get("name_en", ""), "start": slot.get("start", ""), "end": slot.get("end", "")})
                else:
                    kept.append(slot)
            candidates = kept
        f["choghadiya_day"] = candidates[:4]
        if excluded:
            f["choghadiya_excluded_overlapping_rahu"] = excluded

    if not ("abhijit" in f or "rahu" in f or f.get("choghadiya_day")):
        return None          # nothing Muhurta-specific left to show: selector falls back to Panchang
    return PostSpec("muhurta", f["date"], f, warnings=post_warnings(day))

@register("muhurta", build)
def render(s):
    f = s.facts; im, d = canvas("solar"); header(d, "Plan Your Day Wisely", im, "आज का शुभ समय")
    d.text((W / 2, 252), f"{f['weekday']} • {f['date']}", font=sans(TYPE["body"], True), fill=MUTED, anchor="ma")
    if f.get("location_display"):
        d.text((W / 2, 292), f"Times for {f['location_display']}", font=sans(TYPE["label"], True), fill=MAROON, anchor="ma")
    # The Choghadiya card is drawn only when at least one slot survives the Rahu filter.
    # If every auspicious slot overlapped Rahu Kaal there is nothing honest to feature,
    # so the card is omitted and the remaining cards use the freed space.
    slots = list(f.get("choghadiya_day", ()))
    has_chog = bool(slots)
    card_h, pitch = (155, 174) if has_chog else (190, 220)
    y = 325
    if "abhijit" in f:
        metric_card(d, (M, y, W - M, y + card_h), "Auspicious Window · Abhijit", f["abhijit"], accent=GOLD); y += pitch
    if "rahu" in f:
        metric_card(d, (M, y, W - M, y + card_h), "Caution Window · Rahu Kaal", f["rahu"], accent=MAROON); y += pitch
    if has_chog:
        choghadiya_list(d, (M, y, W - M, min(y + 390, 1125)), slots)
        y += 410
    metric_card(d, (M, y, 510, y + (145 if has_chog else card_h)), "Tithi", f["tithi"])
    metric_card(d, (570, y, W - M, y + (145 if has_chog else card_h)), "Nakshatra", f["nakshatra"])
    footer(d, "Use the calculated windows in Siddhanta"); return im
