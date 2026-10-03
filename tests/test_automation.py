import datetime as dt
from promo_studio.automation.panchang_engine import calculate_daily_panchang
from promo_studio.automation.card_generator import generate_slide_1_hook, generate_slide_2_value, generate_combined_card


def test_panchang_calculation():
    # Test fixed date
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
    assert p.content_theme in ("daily_panchang", "saturday_shani", "sunday_numerology", "festival_alert")


def test_card_generation(tmp_path):
    p = calculate_daily_panchang(dt.date(2026, 10, 4))
    s1 = tmp_path / "slide1.png"
    s2 = tmp_path / "slide2.png"
    cb = tmp_path / "combined.png"

    generate_slide_1_hook(p, s1)
    generate_slide_2_value(p, s2)
    generate_combined_card(p, cb)

    assert s1.exists() and s1.stat().st_size > 1000
    assert s2.exists() and s2.stat().st_size > 1000
    assert cb.exists() and cb.stat().st_size > 1000


def test_card_universe_generation(tmp_path):
    from promo_studio.automation.card_universe import (
        render_card_1_panchang,
        render_card_2_plan_day,
        render_card_3_festival,
        render_card_4_kundli,
        render_card_5_chakra,
        render_card_6_jyotish,
    )
    p = calculate_daily_panchang(dt.date(2026, 10, 4))

    c1 = tmp_path / "1_daily_panchang.png"
    c2 = tmp_path / "2_plan_your_day.png"
    c3 = tmp_path / "3_festival.png"
    c4 = tmp_path / "4_kundli.png"
    c5 = tmp_path / "5_chakra.png"
    c6 = tmp_path / "6_jyotish_insight.png"

    render_card_1_panchang(p, c1)
    render_card_2_plan_day(p, c2)
    render_card_3_festival(p, c3)
    render_card_4_kundli(p, c4)
    render_card_5_chakra(c5)
    render_card_6_jyotish(p, c6)

    for card_file in (c1, c2, c3, c4, c5, c6):
        assert card_file.exists()
        assert card_file.stat().st_size > 10000
