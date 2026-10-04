from ..draw import *
from ..spec import PostSpec
from ..models import post_warnings
from . import register

def build(day):
    f = {"weekday": day.weekday, "date": day.date.isoformat(),
         "tithi": f"{day.paksha.title()} {day.tithi}", "nakshatra": day.nakshatra}
    if day.location: f["location"] = day.location
    if day.location_display: f["location_display"] = day.location_display
    for k, v in (("yoga", day.yoga), ("karana", day.karana), ("masa", day.masa),
                 ("sunrise", day.sunrise), ("sunset", day.sunset)):
        if v: f[k] = v
    if day.abhijit: f["abhijit"] = f"{day.abhijit.start} – {day.abhijit.end}"
    if day.rahu_kaal: f["rahu"] = f"{day.rahu_kaal.start} – {day.rahu_kaal.end}"
    return PostSpec("panchang", f["date"], f, warnings=post_warnings(day))

@register("panchang", build)
def render(s):
    f = s.facts; im, d = canvas("sunrise"); header(d, "Today's Panchang", im, "दैनिक पंचांग")
    d.text((W / 2, 252), f"{f['weekday']} • {f['date']}", font=sans(TYPE["body"], True), fill=MUTED, anchor="ma")
    if f.get("location_display"):
        d.text((W / 2, 292), f"Times for {f['location_display']}", font=sans(TYPE["label"], True), fill=MAROON, anchor="ma")
    grid = [("Tithi", "tithi"), ("Nakshatra", "nakshatra"), ("Yoga", "yoga"), ("Karana", "karana"),
            ("Sunrise", "sunrise"), ("Sunset", "sunset")]
    items = [(t, f[k]) for t, k in grid if k in f]
    y = 330
    for i in range(0, len(items), 2):
        row = items[i:i + 2]
        xs = [(M, 510), (570, W - M)] if len(row) == 2 else [(M, W - M)]
        for (t, v), (x1, x2) in zip(row, xs): metric_card(d, (x1, y, x2, y + 150), t, v)
        y += 176
    if "masa" in f:
        d.text((W / 2, y + 4), f"Masa • {f['masa']} · Purnimanta", font=sans(TYPE["label"], True), fill=MAROON, anchor="ma")
        y += 50
    if "sunrise" in f and "sunset" in f and ("abhijit" in f or "rahu" in f):
        bands = []
        if "abhijit" in f:
            a, b = [x.strip() for x in f["abhijit"].split("–", 1)]
            bands.append(("Abhijit", a, b, GOLD))
        if "rahu" in f:
            a, b = [x.strip() for x in f["rahu"].split("–", 1)]
            bands.append(("Rahu Kaal", a, b, MAROON))
        top = y + 8
        h = timeline_height(f["sunrise"], f["sunset"], bands)
        timeline_bar(d, (M, top, W - M, top + h), f["sunrise"], f["sunset"], bands)
    footer(d); return im
