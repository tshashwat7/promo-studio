from datetime import date, datetime
from ..draw import *
from ..spec import PostSpec
from ..models import post_warnings
from . import register


def _iso(value):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _featured_major(major, today):
    candidates = []
    for key, item in major.items():
        if not isinstance(item, dict) or not item.get("current_rashi_en"):
            continue
        ingress = _iso(item.get("ingress_date")); egress = _iso(item.get("egress_date"))
        if ingress == today or egress == today:
            return key, item
        latest_ingress = ingress if ingress and ingress <= today else None
        candidates.append((latest_ingress or date.min, key, item))
    if not candidates:
        return None
    # Most recently entered current sign first; stable key breaks ties. This removes
    # the old hard-coded Jupiter-first behaviour while remaining deterministic.
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][1], candidates[0][2]


def build(day):
    if not day.raw_transit or not isinstance(day.raw_transit.get("major_transits"), dict):
        return None
    chosen = _featured_major(day.raw_transit["major_transits"], day.date)
    if not chosen:
        return None
    key, item = chosen
    planet = str(item.get("planet_en") or key.title())
    facts = {
        "date": day.date.isoformat(),
        "planet": planet,
        "rashi": str(item["current_rashi_en"]),
    }
    if day.location:
        facts["location"] = day.location
    if day.location_display:
        facts["location_display"] = day.location_display
    # Node motion is already normalized by the Siddhanta adapter. Do not expose the
    # upstream Direct value. For other planets, preserve the authoritative motion.
    if key in ("rahu", "ketu"):
        facts["motion"] = "Retrograde"
    elif item.get("motion_en"):
        facts["motion"] = str(item["motion_en"])
    if item.get("ingress_date"):
        facts["most_recent_ingress"] = str(item["ingress_date"])
    # Egress is intentionally omitted because retrograde re-entry can make a single
    # period card misleading.
    return PostSpec("transit", facts["date"], facts, warnings=post_warnings(day, include_node_motion=True))


@register("transit", build)
def render(s):
    f = s.facts
    im, d = canvas(); header(d, "Jyotish Insight", im, "ग्रह गोचर")
    d.text((W / 2, 252), f["date"], font=sans(TYPE["body"], True), fill=MUTED, anchor="ma")
    if f.get("location_display"):
        d.text((W / 2, 292), f"Sky reference: {f['location_display']}", font=sans(TYPE["label"], True), fill=MAROON, anchor="ma")
    centered_wrapped(d, 335, f"{f['planet']} Transit", 58, MAROON, max_lines=2)
    metric_card(d, (M, 535, W - M, 705), "Current Rashi", f["rashi"])
    if "motion" in f:
        metric_card(d, (M, 735, W - M, 880), "Motion", f["motion"])
    if f.get("most_recent_ingress"):
        try:
            ingress_label = datetime.strptime(f["most_recent_ingress"], "%Y-%m-%d").strftime("%d %b %Y").lstrip("0")
        except ValueError:
            ingress_label = f["most_recent_ingress"]
        metric_card(d, (M, 910, W - M, 1055), "Most Recent Ingress", ingress_label)
    footer(d, "Explore Jyotish in Siddhanta")
    return im
