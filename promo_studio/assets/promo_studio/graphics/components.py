"""Reusable Pillow components for Siddhanta promotional posts."""
from __future__ import annotations
import logging, math, warnings
from pathlib import Path
from typing import Optional, Sequence
from PIL import Image, ImageDraw
from ..theme import *
from .background import BackgroundEngine
from .ornaments import paste_ornament

log = logging.getLogger(__name__)
MAX_ASSET_PIXELS = 40_000_000
MAX_ASSET_BYTES = 15 * 1024 * 1024


def canvas(theme: str = "cream"):
    """Blank post canvas. ``theme`` selects a procedural background (see background.py)."""
    im = BackgroundEngine.create(theme, W, H)
    return im, ImageDraw.Draw(im)


def fit_size(text, max_w, size, min_size, make_font):
    while size > min_size and make_font(size).getlength(str(text)) > max_w:
        size -= 1
    return max(min_size, size)


def _ellipsize(text, font, max_w):
    text = str(text)
    if font.getlength(text) <= max_w:
        return text
    ellipsis = "…"
    if font.getlength(ellipsis) > max_w:
        return ""
    out = []
    for ch in text:
        candidate = "".join(out) + ch + ellipsis
        if font.getlength(candidate) > max_w:
            break
        out.append(ch)
    return "".join(out).rstrip() + ellipsis


def wrap(text, font, max_w, max_lines):
    lines, cur = [], ""
    for word in str(text).split():
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = word
    if cur or not lines: lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _ellipsize(lines[-1], font, max_w)
    return lines


def text_fit(d, xy, s, max_w, size, min_size=TYPE["minimum"], fill=INK, bold=False, anchor=None, face="sans"):
    mk = (lambda z: serif(z)) if face == "serif" else (lambda z: sans(z, bold))
    final_size = fit_size(str(s), max_w, size, min_size, mk)
    actual = mk(final_size)
    text = _ellipsize(str(s), actual, max_w)
    d.text(xy, text, font=actual, fill=fill, anchor=anchor)


def centered_wrapped(d, y, s, size=TYPE["title"], fill=MAROON, max_lines=2, face="serif", min_size=TYPE["minimum"]):
    mk = (lambda z: serif(z)) if face == "serif" else (lambda z: sans(z, True))
    size = fit_size(str(s), (W - 2 * M), size, min_size, mk)
    f = mk(size); lines = wrap(str(s), f, W - 2 * M, max_lines)
    for i, ln in enumerate(lines):
        d.text((W / 2, y + i * int(size * 1.15)), ln, font=f, fill=fill, anchor="ma")
    return y + len(lines) * int(size * 1.15)


def _brand_mark_path() -> Optional[Path]:
    p = Path(__file__).parent.parent / "assets" / "brand" / "siddhanta_mark.png"
    return p if p.is_file() else None


def header(d, title, im=None, hindi_title=None):
    mark = _brand_mark_path(); x = M
    if mark and im is not None:
        logo = Image.open(mark).convert("RGBA")
        logo.thumbnail((40, 40), Image.Resampling.LANCZOS)
        im.paste(logo, (x, 54), logo); x += 54
    d.text((x, 58), "SIDDHANTA", font=sans(26, True), fill=MAROON)
    title_end = centered_wrapped(d, 118, title, TYPE["title"], MAROON, max_lines=2, min_size=TYPE["body"])
    if hindi_title:
        d.text((W / 2, title_end + 18), hindi_title, font=devanagari(TYPE["hindi_subtitle"], True), fill=MAROON, anchor="ma")


def footer(d, cta="Explore Siddhanta"):
    d.line((M, H - 112, W - M, H - 112), fill=CREAM_DARK, width=2)
    text_fit(d, (M, H - 78), cta, 640, TYPE["footer"], TYPE["minimum"], MAROON, True)
    d.text((W - M, H - 78), "Offline Panchang", font=sans(TYPE["footer"]), fill=MUTED_DEEP, anchor="ra")


def card(d, box, title, value, subtitle=None, accent=MAROON):
    x1, y1, x2, y2 = box; inner = x2 - x1 - 50
    d.rounded_rectangle(box, 22, fill=WHITE, outline=CREAM_DARK, width=2)
    d.text((x1 + 25, y1 + 20), title.upper(), font=sans(TYPE["label"], True), fill=MUTED)
    text_fit(d, (x1 + 25, y1 + 62), value, inner, TYPE["hero"], TYPE["minimum"], accent, True)
    if subtitle: text_fit(d, (x1 + 25, y2 - 34), subtitle, inner, TYPE["body"], TYPE["minimum"], MUTED)


def metric_card(d, box, label, value, detail=None, accent=MAROON):
    x1, y1, x2, y2 = box
    d.rounded_rectangle(box, 24, fill=WHITE, outline=CREAM_DARK, width=2)
    d.text((x1 + 26, y1 + 20), label.upper(), font=sans(TYPE["label"], True), fill=MUTED)
    text_fit(d, (x1 + 26, y1 + 60), value, x2 - x1 - 52, TYPE["hero"], TYPE["minimum"], accent, True)
    if detail: text_fit(d, (x1 + 26, y2 - 34), detail, x2 - x1 - 52, TYPE["body"], TYPE["minimum"], MUTED)


def mandala(d, cx, cy, r=150, spokes=12, color=GOLD_LIGHT):
    for rr in (r, r * .78, r * .56, r * .34): d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=color, width=2)
    for i in range(spokes):
        a = math.tau * i / spokes; d.line((cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r), fill=color, width=2)


def _minutes(value: str) -> int:
    import datetime as _dt
    parsed = _dt.datetime.strptime(value.strip().upper(), "%I:%M %p")
    return parsed.hour * 60 + parsed.minute


# Timeline geometry. Everything the card needs vertically is derived from the number of
# lanes, so the card can never be shorter than its content (v3 drew the sunrise/sunset
# row outside the card when two lanes were needed).
_TL_TITLE_H = 64      # card title row
_TL_LABEL_H = 30      # label row sitting directly above each lane's bar
_TL_BAR_GAP = 2       # gap between a lane's label row and its bar
_TL_BAR_H = 24
_TL_LANE_GAP = 18     # empty space between one lane's bar and the next lane's label
_TL_TIMES_H = 52      # sunrise / sunset row (gap + 28 px text)
_TL_BOTTOM_PAD = 14
_TL_MIN_H = 188
_TL_SWATCH = 14


def _timeline_height_for(lane_count: int) -> int:
    n = max(1, lane_count)
    lane_block = n * (_TL_LABEL_H + _TL_BAR_GAP + _TL_BAR_H) + (n - 1) * _TL_LANE_GAP
    return max(_TL_MIN_H, _TL_TITLE_H + lane_block + _TL_TIMES_H + _TL_BOTTOM_PAD)


def _plan_timeline(sunrise, sunset, bands, bar_x1, bar_x2):
    """Place bands on the daylight axis and group them into lanes.

    Two bands share a lane only if neither their bars nor their labels collide.
    Returns a list of lanes; each lane is a list of dicts with pixel geometry.
    """
    start_m, end_m = _minutes(sunrise), _minutes(sunset)
    if end_m <= start_m: end_m += 24 * 60
    usable = bar_x2 - bar_x1
    label_font = sans(TYPE["label"], True)

    prepared = []
    for label, s, e, fill in bands:
        sm, em = _minutes(s), _minutes(e)
        if sm < start_m: sm += 24 * 60
        if em < start_m: em += 24 * 60
        if em <= sm or sm > end_m or em < start_m:
            continue
        left = bar_x1 + usable * max(0, min(1, (sm - start_m) / (end_m - start_m)))
        right = bar_x1 + usable * max(0, min(1, (em - start_m) / (end_m - start_m)))
        if right <= left: continue
        label_w = _TL_SWATCH + 8 + label_font.getlength(str(label))
        lx = min(max((left + right) / 2 - label_w / 2, bar_x1), bar_x2 - label_w)
        prepared.append({"label": label, "start": sm, "end": em, "left": left, "right": right,
                         "fill": fill, "label_x": lx, "label_x2": lx + label_w})

    def collides(a, b):
        bars = a["left"] < b["right"] - 0.5 and a["right"] > b["left"] + 0.5
        labels = a["label_x"] < b["label_x2"] + 14 and a["label_x2"] + 14 > b["label_x"]
        return bars or labels

    lanes: list[list[dict]] = []
    for item in sorted(prepared, key=lambda z: (z["start"], z["end"])):
        for lane in lanes:
            if not any(collides(item, other) for other in lane):
                lane.append(item); break
        else:
            lanes.append([item])
    return lanes


def timeline_height(sunrise, sunset, bands: Sequence[tuple[str, str, str, str]], width: int = W - 2 * M) -> int:
    """Height the timeline card needs for these bands (1 lane, or 2+ when windows overlap)."""
    return _timeline_height_for(len(_plan_timeline(sunrise, sunset, bands, 28, width - 28)))


def timeline_bar(d, box, sunrise, sunset, bands: Sequence[tuple[str, str, str, str]], title="Daylight"):
    """Draw the daylight timeline card and return its bottom y.

    Overlapping windows (e.g. Abhijit inside Rahu Kaal) get separate lanes. Every lane
    has its own label row directly above its bar, drawn in dark text with a colour
    swatch, so each bar is unambiguously named. The card grows to fit its lanes; use
    ``timeline_height`` to reserve the right amount of space before calling.
    """
    x1, y1, x2, y2 = box
    bar_x1, bar_x2 = x1 + 28, x2 - 28
    lanes = _plan_timeline(sunrise, sunset, bands, bar_x1, bar_x2)
    y2 = y1 + max(y2 - y1, _timeline_height_for(len(lanes)))
    d.rounded_rectangle((x1, y1, x2, y2), 22, fill=WHITE, outline=CREAM_DARK, width=2)
    d.text((x1 + 24, y1 + 20), title.upper(), font=sans(TYPE["label"], True), fill=MUTED)

    label_font = sans(TYPE["label"], True)
    lane_pitch = _TL_LABEL_H + _TL_BAR_GAP + _TL_BAR_H + _TL_LANE_GAP
    top = y1 + _TL_TITLE_H
    for i, lane in enumerate(lanes or [[]]):
        row_y = top + i * lane_pitch
        bar_y = row_y + _TL_LABEL_H + _TL_BAR_GAP
        d.rounded_rectangle((bar_x1, bar_y, bar_x2, bar_y + _TL_BAR_H), 12, fill=CREAM_DARK)
        for item in lane:
            d.rounded_rectangle((item["left"], bar_y, item["right"], bar_y + _TL_BAR_H), 12, fill=item["fill"])
            cy = row_y + _TL_LABEL_H / 2
            sw = item["label_x"]
            d.rounded_rectangle((sw, cy - _TL_SWATCH / 2, sw + _TL_SWATCH, cy + _TL_SWATCH / 2), 4, fill=item["fill"])
            d.text((sw + _TL_SWATCH + 8, cy), str(item["label"]), font=label_font, fill=MAROON, anchor="lm")

    n = max(1, len(lanes))
    times_y = top + n * (_TL_LABEL_H + _TL_BAR_GAP + _TL_BAR_H) + (n - 1) * _TL_LANE_GAP + 16
    d.text((bar_x1, times_y), sunrise, font=sans(TYPE["body"], True), fill=MUTED)
    d.text((bar_x2, times_y), sunset, font=sans(TYPE["body"], True), fill=MUTED, anchor="ra")
    return y2


def choghadiya_list(d, box, slots: Sequence[dict], title="Auspicious Choghadiya") -> bool:
    """Draw the Choghadiya card. Returns False (drawing nothing) when there is no slot to list.

    An empty card would read as a statement about the day, so the caller decides what
    to show instead; see ``posts/muhurta.py``.
    """
    good = list(slots)[:4]
    if not good:
        return False
    x1, y1, x2, y2 = box
    d.rounded_rectangle(box, 24, fill=WHITE, outline=CREAM_DARK, width=2)
    d.text((x1 + 24, y1 + 22), title.upper(), font=sans(TYPE["label"], True), fill=MUTED)
    top = y1 + 78
    row_h = (y2 - top - 22) / max(1, len(good))
    for i, slot in enumerate(good):
        ry = top + i * row_h
        d.rounded_rectangle((x1 + 24, ry, x2 - 24, ry + row_h - 12), 18, fill=GOLD_LIGHT, outline=CREAM_DARK, width=1)
        name = str(slot.get("name_en", "")); times = f"{slot.get('start','')} – {slot.get('end','')}"
        text_fit(d, (x1 + 48, ry + (row_h - 12) / 2), name, 300, TYPE["body"], TYPE["minimum"], MAROON, True, "lm")
        text_fit(d, (x2 - 48, ry + (row_h - 12) / 2), times, 350, TYPE["body"], TYPE["minimum"], INK, True, "rm")
    return True


def _safe_open_image(path: Path):
    try:
        size_bytes = path.stat().st_size
        if size_bytes > MAX_ASSET_BYTES:
            raise ValueError(f"asset exceeds {MAX_ASSET_BYTES // (1024*1024)} MB")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as probe:
                width, height = probe.size
                if width * height > MAX_ASSET_PIXELS:
                    raise ValueError(f"asset exceeds {MAX_ASSET_PIXELS:,} pixels")
                # Decode only after both limits have passed.
                return probe.convert("RGB")
    except Exception as exc:
        log.warning("Festival asset rejected (%s): %s", path.name, exc)
        return None


def festival_hero(im, d, box, title, image_path=None, max_title_lines=3):
    x1, y1, x2, y2 = box
    d.rounded_rectangle(box, 28, fill=NAVY, outline=CREAM_DARK, width=2)
    if image_path and Path(image_path).is_file():
        src = _safe_open_image(Path(image_path))
        if src is not None:
            ratio = max((x2-x1)/src.width, (y2-y1)/src.height)
            src = src.resize((max(1, int(src.width*ratio)), max(1, int(src.height*ratio))), Image.Resampling.LANCZOS)
            left = (src.width-(x2-x1))//2; top = (src.height-(y2-y1))//2
            crop = src.crop((left, top, left+x2-x1, top+y2-y1)).convert("RGBA")
            # Strong lower scrim protects white title text over bright deity artwork.
            scrim = Image.new("RGBA", crop.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(scrim)
            for yy in range(crop.height):
                t = yy / max(1, crop.height - 1)
                alpha = int(34 + 175 * max(0, (t - .35) / .65))
                sd.line((0, yy, crop.width, yy), fill=(16, 35, 63, alpha))
            crop = Image.alpha_composite(crop, scrim).convert("RGB")
            mask = Image.new("L", crop.size, 0); md = ImageDraw.Draw(mask)
            md.rounded_rectangle((0, 0, crop.width - 1, crop.height - 1), 28, fill=255)
            im.paste(crop, (x1, y1), mask)
        else:
            paste_ornament(im, "mandala_full", ((x1+x2)//2, y1 + int((y2-y1)*.34)), 300)
    else:
        # Quiet fallback: keep the mandala high and compact so the title has its own zone.
        paste_ornament(im, "mandala_full", ((x1+x2)//2, y1 + int((y2-y1)*.34)), 300)
    title_y = y2 - 155 if image_path and Path(image_path).is_file() else y2 - 105
    centered_wrapped(d, title_y, title, 52, WHITE, max_lines=max_title_lines, min_size=TYPE["body"])
