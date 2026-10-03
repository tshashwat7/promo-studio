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
