import datetime as dt
from PIL import Image

from promo_studio.automation.panchang_engine import calculate_daily_panchang
from promo_studio.automation.daily_worker import select_daily_post_type
from promo_studio.automation.card_universe import (
    render_card_1_panchang,
    render_card_2_plan_day,
    render_card_3_festival,
    render_card_4_kundli,
    render_card_5_chakra,
    render_card_6_jyotish,
    CARD_W,
    CARD_H,
)


def test_panchang_calculation():
    d = dt.date(2026, 10, 4)
    p = calculate_daily_panchang(d)
    assert p.date == d
    assert p.vara_sa == "Ravivar"
    assert p.vara_en == "Sunday"
    assert "Surya" in p.deity
    assert p.tithi_name != ""
    assert p.nakshatra_name != ""
    assert "AM" in p.sunrise_str or "PM" in p.sunrise_str
    assert " - " in p.abhijit_muhurta
    assert " - " in p.rahu_kaal


def test_daily_content_selection():
    # Festival priority check
    p_fest = calculate_daily_panchang(dt.date(2026, 10, 4))
    post_type, title = select_daily_post_type(p_fest)
    assert post_type in ("festival", "panchang", "plan_day", "kundli", "chakra", "jyotish")


def test_card_universe_4_5_dimensions(tmp_path):
    p = calculate_daily_panchang(dt.date(2026, 10, 4))

    cards = {
        "1_panchang.png": lambda path: render_card_1_panchang(p, path, lang="en"),
        "1_panchang_hindi.png": lambda path: render_card_1_panchang(p, path, lang="hi"),
        "2_plan_day.png": lambda path: render_card_2_plan_day(p, path),
        "3_festival.png": lambda path: render_card_3_festival(p, path),
        "4_kundli.png": lambda path: render_card_4_kundli(p, path),
        "5_chakra.png": lambda path: render_card_5_chakra(path),
        "6_jyotish.png": lambda path: render_card_6_jyotish(p, path),
    }

    assert CARD_W == 1080
    assert CARD_H == 1350

    for fname, render_fn in cards.items():
        out_file = tmp_path / fname
        render_fn(out_file)
        assert out_file.exists()
        
        with Image.open(out_file) as img:
            assert img.size == (1080, 1350), f"{fname} has invalid dimensions {img.size}"


def test_authoritative_cross_repo_ingestion():
    from promo_studio.automation.panchang_data_client import get_authoritative_daily_panchang
    p = get_authoritative_daily_panchang(dt.date(2026, 10, 4))
    assert p.date == dt.date(2026, 10, 4)
    assert p.vara_sa in ("Sunday", "Ravivar")
    assert "Navami" in p.tithi_name
    assert "Punarvasu" in p.nakshatra_name
    assert p.sunrise_str == "6:19 AM"
    assert p.sunset_str == "6:12 PM"
    assert p.tithi_end == "3:55 AM"
    assert p.nakshatra_end == "12:14 AM"
    assert p.choghadiya_name == "Labh"
    assert p.choghadiya_time == "9:17 AM – 10:46 AM"
    assert p.gochar is not None
    assert p.gochar.spotlight_planet in ("Venus", "Jupiter", "Mercury", "Saturn")
