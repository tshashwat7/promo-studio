from ..draw import *
from ..festival_assets import resolve as festival_asset
from ..spec import PostSpec
from ..models import post_warnings
from . import register

def build(day):
    if not day.festivals_today:
        return None
    names = [x.name_en for x in day.festivals_today]
    f = {"date": day.date.isoformat(), "festival": names[0],
         "tithi": f"{day.paksha.title()} {day.tithi}", "nakshatra": day.nakshatra}
    if day.location: f["location"] = day.location
    if day.location_display: f["location_display"] = day.location_display
    if len(names) > 1: f["also_today"] = " • ".join(names[1:])
    return PostSpec("festival", f["date"], f, warnings=post_warnings(day))

@register("festival", build)
def render(s):
    f = s.facts; im, d = canvas("festival_glow"); header(d, "Festival Today", im, "आज का पर्व")
    hero_path = festival_asset(f["festival"])
    festival_hero(im, d, (M, 245, W - M, 760), f["festival"], hero_path)
    y = 790
    if f.get("location_display"):
        d.text((W / 2, y), f"Times for {f['location_display']}", font=sans(TYPE["label"], True), fill=MAROON, anchor="ma"); y += 48
    metric_card(d, (M, y, 510, y + 160), "Tithi", f["tithi"])
    metric_card(d, (570, y, W - M, y + 160), "Nakshatra", f["nakshatra"])
    if "also_today" in f:
        centered_wrapped(d, y + 185, "Also today: " + f["also_today"], TYPE["body"], INK, max_lines=2, face="sans", min_size=TYPE["minimum"])
    footer(d, "See the festival calendar in Siddhanta"); return im
