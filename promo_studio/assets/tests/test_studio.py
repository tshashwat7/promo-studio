import copy, json, pathlib, pytest
from PIL import Image
from promo_studio import PromoStudio, DataError
from promo_studio.models import parse_day

ROOT = pathlib.Path(__file__).parent.parent
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
BASE = json.load(open(ROOT / "sample_payload.json", encoding="utf-8"))
DAILY = json.load(open(FIXTURES / "daily_panchang.json", encoding="utf-8"))
MUHURTA = json.load(open(FIXTURES / "muhurta_data.json", encoding="utf-8"))
def P(**over):
    p = copy.deepcopy(BASE); p["today"].update(over); return p
def kind(tmp_path, p): return PromoStudio(tmp_path).generate(p)["post_type"]

def test_sample_is_panchang_1080x1350(tmp_path):
    r = PromoStudio(tmp_path).generate(BASE); assert r["post_type"] == "panchang"
    assert Image.open(r["path"]).size == (1080, 1350)

def test_upcoming_festival_is_not_today(tmp_path):
    assert kind(tmp_path, BASE) != "festival"

def test_festival_today_requires_date_and_days_away(tmp_path):
    ok = P(); ok["today"]["upcoming_festivals"][0].update(date="2026-10-04", days_away=0)
    assert kind(tmp_path, ok) == "festival"
    bad = P(); bad["today"]["upcoming_festivals"][0].update(date="2026-10-04", days_away=2)
    assert kind(tmp_path, bad) != "festival"
    assert any("disagree" in w for w in parse_day(bad).warnings)

def test_explicit_festivals_today_wins(tmp_path):
    assert kind(tmp_path, P(festivals_today=[{"name_en": "Maha Navami"}])) == "festival"

@pytest.mark.parametrize("day,date,expect", [("Tuesday","2026-10-06","muhurta"),("Thursday","2026-10-08","muhurta"),
    ("Saturday","2026-10-10","kundli"),("Wednesday","2026-10-07","chakra"),("Friday","2026-10-09","panchang"),
    ("Monday","2026-10-05","panchang")])
def test_weekday_rules(tmp_path, day, date, expect):
    p = P(day_of_week=day, date=date, upcoming_festivals=[]); assert kind(tmp_path, p) == expect

def test_muhurta_falls_back_without_windows(tmp_path):
    p = P(day_of_week="Tuesday", date="2026-10-06", upcoming_festivals=[], rahu_kaal=None, abhijit_muhurta=None)
    assert kind(tmp_path, p) == "panchang"

@pytest.mark.parametrize("over", [{"tithi": None}, {"nakshatra": ""}, {"paksha": "???"}, {"date": "04/10/2026"},
                                  {"day_of_week": "Tuesday"}])
def test_bad_core_data_refuses(tmp_path, over):
    with pytest.raises(DataError): PromoStudio(tmp_path).generate(P(**over))
    assert not list(pathlib.Path(tmp_path).glob("*"))          # nothing written

def test_missing_today_refuses(tmp_path):
    with pytest.raises(DataError): PromoStudio(tmp_path).generate({})

def test_invalid_optional_time_dropped_not_drawn(tmp_path):
    d = parse_day(P(sunrise="25:99 PM", rahu_kaal={"start": "x", "end": "y"}))
    assert d.sunrise is None and d.rahu_kaal is None and len(d.warnings) == 2

def test_long_festival_name_renders(tmp_path):
    p = P(); p["today"]["upcoming_festivals"][0].update(date="2026-10-04", days_away=0,
        name_en="Sharad Navratri Ghatasthapana Pratipada Kalash Sthapana Muhurta Observance")
    assert Image.open(PromoStudio(tmp_path).generate(p)["path"]).size == (1080, 1350)

def test_deterministic_bytes(tmp_path):
    a = PromoStudio(tmp_path / "a").generate(BASE)["sha256"]; b = PromoStudio(tmp_path / "b").generate(BASE)["sha256"]
    assert a == b

def test_showcases_flagged_illustrative(tmp_path):
    p = P(day_of_week="Saturday", date="2026-10-10", upcoming_festivals=[])
    assert PromoStudio(tmp_path).generate(p)["illustrative"] is True

def test_no_overwrite_skips(tmp_path):
    s = PromoStudio(tmp_path); s.generate(BASE); assert s.generate(BASE, overwrite=False)["skipped"]


def test_postspec_facts_are_immutable(tmp_path):
    from promo_studio.models import parse_day
    from promo_studio.selector import select
    spec = select(parse_day(BASE))
    with pytest.raises(TypeError):
        spec.facts["invented"] = "x"


def test_explicit_empty_festivals_today_is_authoritative(tmp_path):
    p = P(festivals_today=[])
    p["today"]["upcoming_festivals"][0].update(date="2026-10-04", days_away=0)
    assert kind(tmp_path, p) != "festival"


def test_invalid_festivals_today_shape_refuses(tmp_path):
    with pytest.raises(DataError):
        PromoStudio(tmp_path).generate(P(festivals_today={"name_en": "bad"}))


def test_caption_handshake_contains_only_spec_facts(tmp_path):
    r = PromoStudio(tmp_path).generate(BASE)
    assert set(r["caption_input"]) == {"post_type", "date", "facts", "illustrative"}
    assert r["caption_input"]["facts"] == r["caption_facts"]
    assert "ONLY the supplied facts" in r["caption_system_prompt"]

def test_real_siddhanta_binding(tmp_path):
    daily = copy.deepcopy(DAILY)
    muhurta = copy.deepcopy(MUHURTA)
    muhurta["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muhurta)
    assert r['post_type'] == 'panchang'
    assert r['caption_facts']['tithi'] == 'Krishna Navami'
    assert r['caption_facts']['nakshatra'] == 'Punarvasu'
    assert r['caption_facts']['abhijit'] == '12:03 PM – 12:51 PM'
    assert r['caption_facts']['location'] == 'Ujjain, India (Standard Astronomical Baseline)'


def test_real_siddhanta_explicit_empty_festival_is_authoritative(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily['today']['date'] = '2026-10-06'
    daily['today']['day_of_week_en'] = 'Tuesday'
    muhurta = copy.deepcopy(MUHURTA)
    muhurta["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muhurta)
    assert r['post_type'] == 'muhurta'


def test_real_siddhanta_transit_binding(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily['today']['date'] = '2026-10-09'
    daily['today']['day_of_week_en'] = 'Friday'
    daily['today']['festivals_today'] = []
    muhurta = copy.deepcopy(MUHURTA)
    muhurta["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muhurta)
    assert r['post_type'] == 'transit'
    assert r['caption_facts']['planet'] == 'Mars'
    assert r['caption_facts']['rashi'] == 'Cancer'
    assert 'phase_start' not in r['caption_facts']
    assert 'phase_end' not in r['caption_facts']


def test_real_siddhanta_muhurta_windows_are_bound(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily['today']['date'] = '2026-10-06'
    daily['today']['day_of_week_en'] = 'Tuesday'
    daily['today']['festivals_today'] = []
    muhurta = copy.deepcopy(MUHURTA)
    muhurta["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muhurta)
    assert r['post_type'] == 'muhurta'
    assert r['caption_facts']['abhijit'] == '12:03 PM – 12:51 PM'
    assert r['caption_facts']['location'] == 'Ujjain, India (Standard Astronomical Baseline)'
    assert r['caption_facts']['rahu'] == '4:42 PM – 6:12 PM'


def test_real_siddhanta_muhurta_date_mismatch_refuses(tmp_path):
    daily = copy.deepcopy(DAILY)
    muhurta = copy.deepcopy(MUHURTA)
    muhurta["date"] = "2026-10-03"
    with pytest.raises(DataError, match="muhurta_data.date"):
        PromoStudio(tmp_path).generate(daily, muhurta_data=muhurta)
    assert not list(pathlib.Path(tmp_path).glob("*"))


def test_siddhanta_nodes_are_normalized_retrograde(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily["today"]["date"] = "2026-10-09"
    daily["today"]["day_of_week_en"] = "Friday"
    daily["today"]["festivals_today"] = []
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    from promo_studio.adapter import adapt_siddhanta
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    adapted = adapt_siddhanta(daily, muh)
    assert adapted["transits"]["positions"]["rahu"]["is_retrograde"] is True
    assert adapted["transits"]["positions"]["rahu"]["motion_en"] == "Retrograde"
    assert adapted["transits"]["major_transits"]["ketu"]["motion_en"] == "Retrograde"


def test_siddhanta_location_reaches_facts(tmp_path):
    daily = copy.deepcopy(DAILY)
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["caption_facts"]["location"] == "Ujjain, India (Standard Astronomical Baseline)"


def test_siddhanta_missing_english_has_specific_error(tmp_path):
    daily = copy.deepcopy(DAILY)
    del daily["today"]["english"]
    with pytest.raises(DataError, match="not a Siddhanta payload"):
        PromoStudio(tmp_path).generate(daily, muhurta_data=copy.deepcopy(MUHURTA))


def test_raqm_is_available_for_devanagari_ci():
    from PIL import features
    assert features.check("raqm"), "Pillow libraqm/Harfbuzz/FriBiDi support is required"

def test_devanagari_fonts_are_resolvable():
    from promo_studio.theme import devanagari, devanagari_serif
    assert devanagari(24).getlength("पंचांग") > 0
    assert devanagari_serif(24).getlength("पंचांग") > 0


def test_muhurta_graphics_render_with_choghadiya(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily["today"]["date"] = "2026-10-06"
    daily["today"]["day_of_week_en"] = "Tuesday"
    daily["today"]["festivals_today"] = []
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["post_type"] == "muhurta"
    assert Image.open(r["path"]).size == (1080, 1350)

def test_corrupt_festival_asset_falls_back(monkeypatch, tmp_path):
    asset_dir = tmp_path / "assets"; asset_dir.mkdir()
    (asset_dir / "vishnu.webp").write_bytes(b"not-an-image")
    monkeypatch.setenv("SIDDHANTA_FESTIVAL_ASSET_DIR", str(asset_dir))
    daily = copy.deepcopy(DAILY)
    daily["today"]["festivals_today"] = [{"name_en": "Indira Ekadashi"}]
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path / "out").generate(daily, muhurta_data=muh)
    assert Image.open(r["path"]).size == (1080, 1350)


def test_oversized_festival_asset_falls_back(monkeypatch, tmp_path):
    asset_dir = tmp_path / "assets"; asset_dir.mkdir()
    # Valid image header with >40M pixels; renderer must reject before full decode.
    from PIL import Image
    huge = Image.new("RGB", (7000, 6000), "white")
    huge.save(asset_dir / "vishnu.webp", format="WEBP", quality=1)
    monkeypatch.setenv("SIDDHANTA_FESTIVAL_ASSET_DIR", str(asset_dir))
    daily = copy.deepcopy(DAILY)
    daily["today"]["festivals_today"] = [{"name_en": "Indira Ekadashi"}]
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path / "out").generate(daily, muhurta_data=muh)
    assert Image.open(r["path"]).size == (1080, 1350)


def test_location_display_is_separate_from_metadata_name(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily["metadata"]["location"]["display_name"] = "Ujjain"
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["caption_facts"]["location"] == "Ujjain, India (Standard Astronomical Baseline)"
    assert r["caption_facts"]["location_display"] == "Ujjain"


def test_node_normalisation_is_recorded_as_warning(tmp_path):
    daily = copy.deepcopy(DAILY)
    daily["today"]["date"] = "2026-10-09"
    daily["today"]["day_of_week_en"] = "Friday"
    daily["today"]["festivals_today"] = []
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert any("motion normalised" in w for w in r["warnings"])


def test_real_panchang_render_exercises_devanagari(tmp_path):
    daily = copy.deepcopy(DAILY)
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert Image.open(r["path"]).size == (1080, 1350)
    from promo_studio.theme import devanagari
    assert devanagari(24).getbbox("दैनिक पंचांग") is not None


def test_location_display_falls_back_to_city(tmp_path):
    daily = copy.deepcopy(DAILY)
    muh = copy.deepcopy(MUHURTA); muh["date"] = daily["today"]["date"]
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["caption_facts"]["location_display"] == "Ujjain"

GOLDEN_HASHES = {
    "panchang": "2158c1d50737586ae1876eeeb79d9de3f99db4d51ff5460dc49b3f18ac987b68",
    "muhurta": "e25d0924f0b43322c66711de7b74dc3460ae2a89406e89afb67a1b1f08b000d8",
    "transit": "e2e7a16bce96b7f7c44ad514d220b592c696501823087979274f23e820331ccc",
    "festival": "65f2f4b156f50f94b518cd2e9ce54a7649dbff278c320fe3c2a5759c4a017147",
    "kundli": "010ce47764f7e7540c68ff7143691d5765b080d3002db0542d80027dd28a7c04",
    "chakra": "efc2f0d4f86306cb65672c640c18c709a1354c5fbf0281a5afc50b831036bdc5",
}


def _real_post_payload(kind):
    d = copy.deepcopy(DAILY)
    dates = {
        "panchang": ("2026-10-04", "Sunday"),
        "muhurta": ("2026-10-06", "Tuesday"),
        "transit": ("2026-10-09", "Friday"),
        "festival": ("2026-10-11", "Sunday"),
        "kundli": ("2026-10-10", "Saturday"),
        "chakra": ("2026-10-07", "Wednesday"),
    }
    date_value, weekday = dates[kind]
    d["today"]["date"] = date_value
    d["today"]["day_of_week_en"] = weekday
    d["today"]["festivals_today"] = [{"name_en": "Navratri (Start)"}] if kind == "festival" else []
    m = copy.deepcopy(MUHURTA)
    m["date"] = date_value
    return d, m


def test_golden_hash_per_post_type(tmp_path):
    for kind, expected in GOLDEN_HASHES.items():
        daily, muh = _real_post_payload(kind)
        result = PromoStudio(tmp_path / kind).generate(daily, muhurta_data=muh)
        assert result["post_type"] == kind
        assert result["sha256"] == expected


def test_nested_postspec_facts_are_immutable(tmp_path):
    from promo_studio.models import parse_day
    from promo_studio.selector import select
    spec = select(parse_day(BASE))
    # The real sample does not contain Choghadiya; use a direct PostSpec to exercise nesting.
    from promo_studio.spec import PostSpec
    nested = PostSpec("x", "2026-10-04", {"items": [{"name": "A"}]})
    with pytest.raises(TypeError):
        nested.facts["items"][0]["name"] = "B"
    with pytest.raises(TypeError):
        nested.facts["items"] += ("x",)


def test_node_warnings_only_reach_transit(tmp_path):
    daily, muh = _real_post_payload("panchang")
    daily["today"]["date"] = "2026-10-04"
    muh["date"] = "2026-10-04"
    p = PromoStudio(tmp_path / "p").generate(daily, muhurta_data=muh)
    assert not any("motion normalised" in w for w in p["warnings"])
    daily, muh = _real_post_payload("transit")
    t = PromoStudio(tmp_path / "t").generate(daily, muhurta_data=muh)
    assert any("motion normalised" in w for w in t["warnings"])


def test_runtime_requires_raqm(monkeypatch, tmp_path):
    import promo_studio.pipeline as pipeline
    monkeypatch.setattr(pipeline, "require_raqm", lambda: (_ for _ in ()).throw(RuntimeError("raqm required")))
    with pytest.raises(RuntimeError, match="raqm required"):
        pipeline.PromoStudio(tmp_path)


def test_render_stack_versions_are_pinned():
    import PIL
    from PIL import features
    assert PIL.__version__ == "12.3.0"
    assert features.version("freetype2") == "2.14.3"
    assert features.version("raqm") == "0.10.5"


# ---------------------------------------------------------------------------
# v3.1: JSON-safe caption hand-off, Choghadiya/Rahu policy, timeline lanes
# ---------------------------------------------------------------------------
import json

def _muhurta_payload(rahu=None, choghadiya=None, abhijit=None, drop_abhijit=False):
    daily, muh = _real_post_payload("muhurta")
    if rahu: muh["muhurtas"]["rahu_kaal"].update(start=rahu[0], end=rahu[1])
    if abhijit: muh["muhurtas"]["abhijit_muhurta"].update(start=abhijit[0], end=abhijit[1])
    if choghadiya is not None: muh["choghadiya"]["day"] = choghadiya
    return daily, muh

def _slot(name, start, end, good=True):
    return {"name_en": name, "start": start, "end": end, "is_auspicious": good}


@pytest.mark.parametrize("post_kind", list(GOLDEN_HASHES))
def test_caption_hand_off_is_json_serialisable_for_every_post_type(tmp_path, post_kind):
    daily, muh = _real_post_payload(post_kind)
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["post_type"] == post_kind
    for key in ("caption_input", "caption_facts"):
        encoded = json.dumps(r[key])                      # mappingproxy/tuple regressions fail here
        assert json.loads(encoded) == r[key]              # plain dict/list/str all the way down


def test_muhurta_caption_input_with_nested_choghadiya_serialises(tmp_path):
    daily, muh = _muhurta_payload()
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    facts = json.loads(json.dumps(r["caption_input"]))["facts"]
    assert isinstance(facts["choghadiya_day"], list) and facts["choghadiya_day"]
    assert all(isinstance(x, dict) for x in facts["choghadiya_day"])


def test_caption_dicts_are_independent_copies_of_the_frozen_spec(tmp_path):
    from promo_studio.caption import caption_input
    from promo_studio.selector import select
    daily, muh = _muhurta_payload()
    from promo_studio.adapter import adapt_siddhanta
    spec = select(parse_day(adapt_siddhanta(daily, muh)))
    ci = caption_input(spec)
    first = ci.to_dict(); first["facts"]["choghadiya_day"].append({"name_en": "invented"})
    assert ci.to_dict()["facts"]["choghadiya_day"] == spec.to_dict()["facts"]["choghadiya_day"]
    with pytest.raises(TypeError):
        spec.facts["choghadiya_day"][0]["name_en"] = "tampered"      # frozen spec unaffected


def test_overlapping_choghadiya_is_omitted_and_listed_as_excluded(tmp_path):
    daily, muh = _muhurta_payload(rahu=("10:00 AM", "11:30 AM"), choghadiya=[
        _slot("Labh", "9:17 AM", "10:46 AM"), _slot("Amrit", "10:46 AM", "12:15 PM"),
        _slot("Shubh", "1:44 PM", "3:13 PM")])
    f = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)["caption_facts"]
    assert [x["name_en"] for x in f["choghadiya_day"]] == ["Shubh"]
    assert [x["name_en"] for x in f["choghadiya_excluded_overlapping_rahu"]] == ["Labh", "Amrit"]


def test_slot_touching_rahu_boundary_is_not_an_overlap(tmp_path):
    daily, muh = _muhurta_payload(rahu=("12:15 PM", "1:44 PM"), choghadiya=[
        _slot("Amrit", "10:46 AM", "12:15 PM"), _slot("Shubh", "1:44 PM", "3:13 PM")])
    f = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)["caption_facts"]
    assert [x["name_en"] for x in f["choghadiya_day"]] == ["Amrit", "Shubh"]
    assert "choghadiya_excluded_overlapping_rahu" not in f


def test_internal_policy_note_is_never_sent_to_the_caption_writer(tmp_path):
    from promo_studio.posts import muhurta
    daily, muh = _muhurta_payload(rahu=("10:00 AM", "11:30 AM"))
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert "choghadiya_policy" not in r["caption_facts"]
    assert "Jyotish judgement" not in json.dumps(r["caption_input"], ensure_ascii=False)
    assert "Jyotish judgement" not in r["caption_system_prompt"]
    assert muhurta.CHOGHADIYA_POLICY.startswith("Auspicious Choghadiya")   # kept in code


def test_muhurta_hides_choghadiya_card_when_every_slot_overlaps_rahu(monkeypatch, tmp_path):
    from promo_studio.posts import muhurta
    calls = []
    monkeypatch.setattr(muhurta, "choghadiya_list", lambda *a, **k: calls.append(a) or True)
    daily, muh = _muhurta_payload(rahu=("9:00 AM", "6:00 PM"), choghadiya=[
        _slot("Labh", "9:17 AM", "10:46 AM"), _slot("Amrit", "10:46 AM", "12:15 PM")])
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["post_type"] == "muhurta" and calls == []
    assert r["caption_facts"]["choghadiya_day"] == []
    assert len(r["caption_facts"]["choghadiya_excluded_overlapping_rahu"]) == 2
    assert Image.open(r["path"]).size == (1080, 1350)


def test_choghadiya_list_draws_nothing_for_empty_slots():
    from PIL import ImageDraw
    from promo_studio.graphics.components import choghadiya_list
    im = Image.new("RGB", (1080, 600), "#F7F0E3"); before = im.tobytes()
    assert choghadiya_list(ImageDraw.Draw(im), (76, 40, 1004, 440), []) is False
    assert im.tobytes() == before


def test_muhurta_falls_back_to_panchang_when_nothing_muhurta_specific_remains(tmp_path):
    daily, muh = _muhurta_payload(choghadiya=[_slot("Kaal", "9:17 AM", "10:46 AM", good=False)])
    del muh["muhurtas"]["abhijit_muhurta"]; del muh["muhurtas"]["rahu_kaal"]
    assert PromoStudio(tmp_path).generate(daily, muhurta_data=muh)["post_type"] == "panchang"


# -- timeline lanes --------------------------------------------------------
from promo_studio.graphics import components as gc
from promo_studio.theme import GOLD, MAROON, WHITE, H

SUNRISE, SUNSET = "6:19 AM", "6:12 PM"
BANDS_SEPARATE = [("Abhijit", "12:03 PM", "12:51 PM", GOLD), ("Rahu Kaal", "4:42 PM", "6:12 PM", MAROON)]
BANDS_OVERLAP = [("Abhijit", "12:03 PM", "12:51 PM", GOLD), ("Rahu Kaal", "12:00 PM", "1:30 PM", MAROON)]


def _lane_count(bands):
    return len(gc._plan_timeline(SUNRISE, SUNSET, bands, 104, 976))


def test_separate_windows_share_one_lane_and_overlapping_windows_get_two():
    assert _lane_count(BANDS_SEPARATE) == 1
    assert _lane_count(BANDS_OVERLAP) == 2


def test_adjacent_windows_with_colliding_labels_are_split_into_lanes():
    touching = [("Abhijit", "12:03 PM", "12:51 PM", GOLD), ("Rahu Kaal", "12:51 PM", "2:21 PM", MAROON)]
    assert _lane_count(touching) == 2          # bars do not overlap but their labels would


def test_timeline_card_grows_with_lanes_and_contains_sunrise_sunset_row():
    assert gc.timeline_height(SUNRISE, SUNSET, BANDS_OVERLAP) > gc.timeline_height(SUNRISE, SUNSET, BANDS_SEPARATE)
    from PIL import ImageDraw
    for bands in (BANDS_SEPARATE, BANDS_OVERLAP):
        need = gc.timeline_height(SUNRISE, SUNSET, bands)
        im = Image.new("RGB", (1080, 700), "#F7F0E3")
        bottom = gc.timeline_bar(ImageDraw.Draw(im), (76, 20, 1004, 20 + need), SUNRISE, SUNSET, bands)
        assert bottom == 20 + need
        # sunrise/sunset text (MUTED) must lie inside the card: nothing muted below its bottom edge
        muted = (0x74, 0x6B, 0x63)
        below = im.crop((76, bottom + 4, 1004, 700))
        assert muted not in {c for _, c in below.getcolors(maxcolors=1_000_000)}


def test_a_card_that_is_too_short_is_grown_not_overflowed():
    from PIL import ImageDraw
    im = Image.new("RGB", (1080, 700), "#F7F0E3")
    need = gc.timeline_height(SUNRISE, SUNSET, BANDS_OVERLAP)
    bottom = gc.timeline_bar(ImageDraw.Draw(im), (76, 20, 1004, 20 + 120), SUNRISE, SUNSET, BANDS_OVERLAP)
    assert bottom == 20 + need


def _ink_rows(im, color, x0, x1, y0, y1, tol=40):
    hits = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            px = im.getpixel((x, y))
            if all(abs(px[i] - color[i]) <= tol for i in range(3)):
                hits.append((x, y))
    return hits


@pytest.mark.parametrize("bands,expected_labels", [(BANDS_SEPARATE, 2), (BANDS_OVERLAP, 2)])
def test_every_band_label_is_visible_on_the_white_card(bands, expected_labels):
    """v3 drew maroon-band labels in white-on-white, so 'Rahu Kaal' was invisible."""
    from PIL import ImageDraw
    need = gc.timeline_height(SUNRISE, SUNSET, bands)
    im = Image.new("RGB", (1080, 700), "#F7F0E3")
    gc.timeline_bar(ImageDraw.Draw(im), (76, 20, 1004, 20 + need), SUNRISE, SUNSET, bands)
    lanes = gc._plan_timeline(SUNRISE, SUNSET, bands, 104, 976)
    pitch = gc._TL_LABEL_H + gc._TL_BAR_GAP + gc._TL_BAR_H + gc._TL_LANE_GAP
    seen = 0
    for i, lane in enumerate(lanes):
        row_top = 20 + gc._TL_TITLE_H + i * pitch
        for item in lane:
            text_x0 = int(item["label_x"]) + gc._TL_SWATCH + 8
            ink = _ink_rows(im, (0x6F, 0x26, 0x38), text_x0, int(item["label_x2"]), row_top, row_top + gc._TL_LABEL_H)
            assert len(ink) > 40, f"label {item['label']!r} has no visible ink"
            seen += 1
    assert seen == expected_labels


def test_panchang_overlap_case_fits_above_the_footer(tmp_path):
    daily, muh = _real_post_payload("panchang")
    muh["muhurtas"]["rahu_kaal"].update(start="12:00 PM", end="1:30 PM")
    r = PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert r["post_type"] == "panchang" and Image.open(r["path"]).size == (1080, 1350)
    # panchang layout: timeline top is y=916 with Masa line present
    assert 916 + gc.timeline_height(SUNRISE, SUNSET, BANDS_OVERLAP) <= H - 112


# Edge layouts, reviewed visually before pinning (see V3_1_UPDATE.md).
GOLDEN_EDGE_HASHES = {
    "panchang_overlap": "e6078409816a9773dba24d46d820d4c9fc9e752addadbe2c5d31f7fd41a45212",
    "muhurta_all_excluded": "9bf83c83c471cd38bb0d63d5e98a8a976938ed4b5df76b6672da89a1ec0814e3",
}


def test_golden_hash_edge_layouts(tmp_path):
    cases = {
        "panchang_overlap": ("panchang", {"rahu": ("12:00 PM", "1:30 PM")}),
        "muhurta_all_excluded": ("muhurta", {"rahu": ("9:00 AM", "6:00 PM")}),
    }
    for name, (kind, over) in cases.items():
        daily, muh = _real_post_payload(kind)
        if "rahu" in over: muh["muhurtas"]["rahu_kaal"].update(start=over["rahu"][0], end=over["rahu"][1])
        got = PromoStudio(tmp_path / name).generate(daily, muhurta_data=muh)["sha256"]
        assert got == GOLDEN_EDGE_HASHES[name], f"{name}: {got}"


# ---------------------------------------------------------------------------
# v3.2: procedural backgrounds (NumPy) and pre-rendered SVG ornaments
# ---------------------------------------------------------------------------
import hashlib, subprocess, sys
import numpy as np
from promo_studio.graphics.background import BackgroundEngine, THEMES
from promo_studio.graphics import ornaments as orn

GOLDEN_BACKGROUND_HASHES = {
    "cream": "6034c262d08942d5874fcdd580c6e9a3dd8522cd046a44a3fbbd4c4d4902ccaf",
    "festival_glow": "cc05b087ba9dbba4c089bc41acf8b7232252ac41d24bd940686ec031142a0d21",
    "solar": "f3a31151ef15ae7c3fb9cdd9d3b255c763c8ac10c0b277dbbb29feebcaafc446",
    "sunrise": "97e50161611cb8838e39c00d8db8a9a0b225a8b2bf0288dac49c2f9c3a3aa79a",
}   # reviewed visually


def _lum(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _contrast(fg, bg):
    hi, lo = sorted((float(_lum(fg)), float(_lum(bg))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def test_background_cream_is_the_flat_brand_colour():
    im = BackgroundEngine.create("cream")
    assert im.size == (1080, 1350) and im.getcolors() == [(1080 * 1350, _hexrgb("#F7F0E3"))]


@pytest.mark.parametrize("theme", sorted(THEMES))
def test_backgrounds_are_deterministic_and_correctly_sized(theme):
    a, b = BackgroundEngine.create(theme), BackgroundEngine.create(theme)
    assert a.size == (1080, 1350) and a.mode == "RGB" and a.tobytes() == b.tobytes()


def test_unknown_background_theme_is_rejected():
    with pytest.raises(ValueError, match="unknown background theme"):
        BackgroundEngine.create("neon")


@pytest.mark.parametrize("theme", sorted(THEMES))
def test_text_stays_readable_on_the_darkest_background_pixel(theme):
    px = np.asarray(BackgroundEngine.create(theme)).reshape(-1, 3)
    darkest = px[int(np.argmin(_lum(px)))]
    assert _contrast(_hexrgb("#6F2638"), darkest) >= 7       # maroon titles
    assert _contrast(_hexrgb("#2B2522"), darkest) >= 10      # ink
    assert _contrast(_hexrgb("#5E554D"), darkest) >= 4.5     # footer text (MUTED_DEEP)


def test_golden_hash_per_background_theme():
    got = {t: hashlib.sha256(BackgroundEngine.create(t).tobytes()).hexdigest() for t in sorted(THEMES)}
    assert got == GOLDEN_BACKGROUND_HASHES


def test_post_to_theme_mapping(monkeypatch, tmp_path):
    from promo_studio.graphics import components
    seen = []
    real = components.BackgroundEngine.create
    monkeypatch.setattr(components.BackgroundEngine, "create", staticmethod(lambda theme="cream", *a, **k: seen.append(theme) or real(theme, *a, **k)))
    for kind in ("panchang", "muhurta", "festival", "transit"):
        seen.clear()
        daily, muh = _real_post_payload(kind)
        PromoStudio(tmp_path / kind).generate(daily, muhurta_data=muh)
        assert seen == [{"panchang": "sunrise", "muhurta": "solar", "festival": "festival_glow", "transit": "cream"}[kind]]


def test_mandala_ornament_is_a_transparent_rgba_png():
    art = orn.ornament("mandala_full", 300)
    assert art.mode == "RGBA" and art.width == 300
    alpha = art.getchannel("A"); assert alpha.getextrema()[0] == 0 and alpha.getextrema()[1] == 255


@pytest.mark.parametrize("bad", ["../theme", "..\\x", "a/b", "MANDALA", "", "x.png"])
def test_ornament_names_cannot_traverse_the_filesystem(bad):
    with pytest.raises(orn.OrnamentError):
        orn.ornament(bad, 100)


def test_missing_ornament_has_a_clear_error():
    with pytest.raises(orn.OrnamentError, match="build_ornaments"):
        orn.ornament("does_not_exist", 100)


def test_every_svg_source_has_a_committed_png_and_vice_versa():
    d = pathlib.Path(orn._DIR)
    svgs = {p.stem for p in (d / "src").glob("*.svg")}
    pngs = {p.stem for p in d.glob("*.png")}
    assert svgs and svgs == pngs


def test_festival_fallback_uses_the_prerendered_mandala(monkeypatch, tmp_path):
    from promo_studio.graphics import components
    calls = []
    real = components.paste_ornament
    monkeypatch.setattr(components, "paste_ornament", lambda im, name, *a, **k: calls.append(name) or real(im, name, *a, **k))
    daily, muh = _real_post_payload("festival")
    PromoStudio(tmp_path).generate(daily, muhurta_data=muh)
    assert calls == ["mandala_full"]


def test_cairosvg_is_not_a_runtime_dependency():
    code = "import sys, promo_studio.pipeline; assert 'cairosvg' not in sys.modules and 'cairocffi' not in sys.modules"
    root = str(pathlib.Path(__file__).parent.parent)
    assert subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True).returncode == 0


def test_numpy_is_pinned_for_reproducible_backgrounds():
    assert np.__version__ == "2.4.4"
    reqs = (pathlib.Path(__file__).parent.parent / "requirements.txt").read_text()
    assert "numpy==2.4.4" in reqs and "cairosvg" not in reqs.lower()
