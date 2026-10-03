"""Panchang calculation engine for Siddhanta Daily Cosmic Blueprint.

Computes astronomical Sun & Moon positions, Lahiri Ayanamsha, Tithi,
Nakshatra, Sunrise, Sunset, Rahu Kaal, Abhijit Muhurta, active deity,
and handles the 7-day content rotation with festival alerts.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field

# ── Astronomical Constants & Names ──────────────────────────────────────────

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya"
]

TITHI_NAMES_HI = [
    "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी",
    "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी",
    "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा",
    "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी",
    "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी",
    "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "अमावस्या"
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

NAKSHATRA_NAMES_HI = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा",
    "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा",
    "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी", "हस्त", "चित्रा", "स्वाती",
    "विशाखा", "अनुराधा", "ज्येष्ठा", "मूल", "पूर्वाषाढ़ा",
    "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा",
    "पूर्वभाद्रपद", "उत्तरभाद्रपद", "रेवती"
]

MASA_NAMES = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwina", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna"
]

MASA_NAMES_HI = [
    "चैत्र", "वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद",
    "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन"
]

RASHI_NAMES = [
    "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)", "Karka (Cancer)",
    "Simha (Leo)", "Kanya (Virgo)", "Tula (Libra)", "Vrishchika (Scorpio)",
    "Dhanu (Sagittarius)", "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)"
]

RASHI_NAMES_HI = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"
]

VARA_INFO = {
    0: {  # Monday
        "name_sa": "Somavara", "name_en": "Monday", "name_hi": "सोमवार",
        "deity": "Lord Shiva & Chandra Dev", "deity_hi": "भगवान शिव एवं चंद्र देव",
        "color": "White / Pearl",
        "significance": "Mental peace, emotional balance, motherly grace, and Lord Shiva's divine blessings.",
        "remedy": "Offer pure water or milk to a Shiva Lingam, chant 'Om Namah Shivaya', and practice mindful meditation."
    },
    1: {  # Tuesday
        "name_sa": "Mangalavara", "name_en": "Tuesday", "name_hi": "मंगलवार",
        "deity": "Lord Hanuman & Mangal Dev", "deity_hi": "श्री हनुमान जी एवं मंगल देव",
        "color": "Red / Coral",
        "significance": "Courage, physical vitality, triumph over obstacles, and inner strength.",
        "remedy": "Recite Hanuman Chalisa, light a mustard or jasmine oil lamp, and avoid conflict or hasty decisions."
    },
    2: {  # Wednesday
        "name_sa": "Budhavara", "name_en": "Wednesday", "name_hi": "बुधवार",
        "deity": "Lord Ganesha & Budha Dev", "deity_hi": "भगवान श्री गणेश एवं बुध देव",
        "color": "Green / Emerald",
        "significance": "Intellect, business acumen, communication clarity, and learning.",
        "remedy": "Offer Durva grass to Lord Ganesha, chant 'Om Gan Ganapataye Namah', and plan financial or study goals."
    },
    3: {  # Thursday
        "name_sa": "Brihaspativara", "name_en": "Thursday", "name_hi": "गुरुवार",
        "deity": "Lord Vishnu & Guru Brihaspati", "deity_hi": "भगवान श्री विष्णु एवं देवगुरु बृहस्पति",
        "color": "Yellow / Gold",
        "significance": "Higher wisdom, spiritual growth, auspicious prosperity, and divine mentor guidance.",
        "remedy": "Chant 'Om Namo Bhagavate Vasudevaya', wear shades of yellow, and honor your teachers/gurus."
    },
    4: {  # Friday
        "name_sa": "Shukravara", "name_en": "Friday", "name_hi": "शुक्रवार",
        "deity": "Goddess Mahalakshmi & Shukra Dev", "deity_hi": "मां महालक्ष्मी एवं शुक्र देव",
        "color": "Silver / Pink / White",
        "significance": "Abundance, harmony in relationships, creative arts, and inner and outer beauty.",
        "remedy": "Chant 'Om Shreem Mahalakshmiyei Namah', express gratitude for your blessings, and nurture healthy relationships."
    },
    5: {  # Saturday
        "name_sa": "Shanivara", "name_en": "Saturday", "name_hi": "शनिवार",
        "deity": "Shani Dev & Lord Hanuman", "deity_hi": "सूर्यपुत्र शनि देव एवं हनुमान जी",
        "color": "Black / Dark Blue",
        "significance": "Discipline, karmic cleansing, endurance, justice, and protection from negative transits.",
        "remedy": "Light a sesame/mustard oil lamp under a Peepal tree, feed stray animals, and practice selfless humility."
    },
    6: {  # Sunday
        "name_sa": "Ravivar", "name_en": "Sunday", "name_hi": "रविवार",
        "deity": "Bhagwan Surya (Sun God)", "deity_hi": "भगवान भुवन भास्कर सूर्य देव",
        "color": "Saffron / Copper",
        "significance": "Soul vitality (Atma Karaka), leadership, health, willpower, and fatherly blessings.",
        "remedy": "Offer Arghya (fresh water in a copper vessel) to the rising Sun while chanting the Gayatri Mantra."
    }
}

# Rahu Kaal day fractions (each part is 1/8th of daylight duration)
RAHU_KAAL_PARTS = {
    0: (1, 2),  # Monday: 2nd period
    1: (6, 7),  # Tuesday: 7th period
    2: (4, 5),  # Wednesday: 5th period
    3: (5, 6),  # Thursday: 6th period
    4: (3, 4),  # Friday: 4th period
    5: (2, 3),  # Saturday: 3rd period
    6: (7, 8),  # Sunday: 8th period
}

VIMSHOTTARI_MAHADASHAS = [
    ("Ketu Mahadasha (7 yrs)", "Spiritual detachment, sudden intuitive awakenings, research, and inward reflection."),
    ("Venus / Shukra Mahadasha (20 yrs)", "Creative flourish, relationships, material comfort, arts, and emotional expansion."),
    ("Sun / Surya Mahadasha (6 yrs)", "Soul vitality, leadership responsibilities, authority, and building core self-confidence."),
    ("Moon / Chandra Mahadasha (10 yrs)", "Emotional depth, travel, public recognition, intuitive sensitivity, and nurturing life."),
    ("Mars / Mangal Mahadasha (7 yrs)", "Dynamic initiative, courage, physical vitality, property decisions, and ambition."),
    ("Rahu Mahadasha (18 yrs)", "Intense ambition, tech innovation, global opportunities, and navigating unconventional paths."),
    ("Jupiter / Guru Mahadasha (16 yrs)", "Higher wisdom, auspicious milestones, education, mentorship, and ethical wealth."),
    ("Saturn / Shani Mahadasha (19 yrs)", "Karmic accountability, endurance, career restructuring, discipline, and lasting foundations."),
    ("Mercury / Budha Mahadasha (17 yrs)", "Commercial growth, communication excellence, analytical skills, and intellectual mastery.")
]


@dataclass
class GocharSnapshot:
    sun_sign: str
    moon_sign: str
    jupiter_sign: str
    saturn_sign: str
    rahu_sign: str
    ketu_sign: str
    favorable_rashis: list[str]
    caution_rashis: list[str]
    dasha_spotlight_title: str
    dasha_spotlight_desc: str


@dataclass
class DailyPanchang:
    date: dt.date
    date_formatted: str
    date_formatted_hi: str
    weekday_index: int
    vara_sa: str
    vara_en: str
    vara_hi: str
    deity: str
    deity_hi: str
    color: str
    significance: str
    remedy: str
    
    # Core Panchang
    paksha: str               # "Shukla" or "Krishna"
    paksha_hi: str            # "शुक्ल पक्ष" or "कृष्ण पक्ष"
    tithi_index: int          # 0..29
    tithi_name: str           # e.g. "Shukla Dashami" or "Ekadashi"
    tithi_name_hi: str        # e.g. "शुक्ल नवमी"
    masa_name: str            # e.g. "Ashwina"
    masa_name_hi: str         # e.g. "आश्विन"
    nakshatra_index: int      # 0..26
    nakshatra_name: str       # e.g. "Rohini"
    nakshatra_name_hi: str    # e.g. "रोहिणी"
    moon_rashi: str           # e.g. "Vrishabha (Taurus)"
    moon_rashi_hi: str        # e.g. "वृषभ"
    sun_rashi: str            # e.g. "Kanya (Virgo)"
    sun_rashi_hi: str         # e.g. "कन्या"
    
    # Auspicious & Inauspicious Timings
    sunrise_str: str          # e.g. "06:16 AM"
    sunset_str: str           # e.g. "06:04 PM"
    abhijit_muhurta: str      # e.g. "11:45 AM - 12:33 PM"
    rahu_kaal: str            # e.g. "04:30 PM - 06:00 PM"
    
    # Universal Planetary Transits & Dasha Spotlight
    gochar: GocharSnapshot | None = None
    
    # Rotation & Content Flags
    content_theme: str = "daily_panchang"
    is_festival: bool = False
    festival_name: str = ""
    festival_note: str = ""
    
    # Astro-Numerology (Sunday focus)
    root_number: int = 1
    destiny_number: int = 1
    numerology_focus: str = ""


# ── Astronomical Helpers ─────────────────────────────────────────────────────

def _julian_day(year: int, month: int, day: int, hour: float = 0.0) -> float:
    if month <= 2:
        year -= 1
        month += 12
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + hour / 24.0 + B - 1524.5


def _lahiri_ayanamsha(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return 23.85833 + (50.290966 * t * 100) / 3600.0


def _sun_longitude(jd: float) -> float:
    """Mean and true ecliptic longitude of the Sun (Meeus Ch. 25)."""
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    M_rad = math.radians(M)
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
    C += (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
    C += 0.000289 * math.sin(3 * M_rad)
    return (L0 + C) % 360.0


def _moon_longitude(jd: float) -> float:
    """Lunar ecliptic longitude (Meeus Ch. 47 truncated)."""
    T = (jd - 2451545.0) / 36525.0
    L_prime = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T
    M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T * T
    M_prime = 134.9633964 + 477198.8675055 * T + 0.0087414 * T * T
    F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T * T

    # Principal periodic terms in longitude (degrees)
    l_sum = (
        6.288774 * math.sin(math.radians(M_prime))
        + 1.274027 * math.sin(math.radians(2 * D - M_prime))
        + 0.658314 * math.sin(math.radians(2 * D))
        + 0.213618 * math.sin(math.radians(2 * M_prime))
        - 0.185116 * math.sin(math.radians(M))
        - 0.114332 * math.sin(math.radians(2 * F))
        + 0.058793 * math.sin(math.radians(2 * D - 2 * M_prime))
        + 0.057066 * math.sin(math.radians(2 * D - M - M_prime))
        + 0.053322 * math.sin(math.radians(2 * D + M_prime))
        + 0.045758 * math.sin(math.radians(2 * D - M))
        - 0.040923 * math.sin(math.radians(M - M_prime))
    )
    return (L_prime + l_sum) % 360.0


def _approx_sun_times(date: dt.date, lat: float = 28.6139, lon: float = 77.2090) -> tuple[dt.time, dt.time]:
    """Computes approximate sunrise and sunset for India/IST."""
    # Standard solar declination calculation
    day_of_year = date.timetuple().tm_yday
    declination = 23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81)))
    lat_rad = math.radians(lat)
    dec_rad = math.radians(declination)
    
    # Zenith angle for atmospheric refraction: 90°50' = 90.833°
    cos_omega = (math.cos(math.radians(90.833)) - math.sin(lat_rad) * math.sin(dec_rad)) / (math.cos(lat_rad) * math.cos(dec_rad))
    cos_omega = max(-1.0, min(1.0, cos_omega))
    omega = math.degrees(math.acos(cos_omega))
    daylight_hours = (2 * omega) / 15.0

    # Solar noon in IST (82.5° E is IST meridian)
    # Longitude offset: (82.5 - lon) * 4 minutes
    time_offset_min = (82.5 - lon) * 4.0
    # Equation of time approx (minutes)
    B = math.radians(360 / 365 * (day_of_year - 81))
    eot_min = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    solar_noon_min = 12 * 60 + time_offset_min - eot_min

    sunrise_min = solar_noon_min - (daylight_hours / 2.0) * 60
    sunset_min = solar_noon_min + (daylight_hours / 2.0) * 60

    sunrise_h, sunrise_m = int(sunrise_min // 60), int(sunrise_min % 60)
    sunset_h, sunset_m = int(sunset_min // 60), int(sunset_min % 60)

    return dt.time(sunrise_h, sunrise_m), dt.time(sunset_h, sunset_m)


def _fmt_time(t: dt.time) -> str:
    h = t.hour % 12 or 12
    am_pm = "AM" if t.hour < 12 else "PM"
    return f"{h:02d}:{t.minute:02d} {am_pm}"


def _fmt_window(start: dt.datetime, end: dt.datetime) -> str:
    return f"{_fmt_time(start.time())} - {_fmt_time(end.time())}"


# ── Festival & Special Tithi Detection ───────────────────────────────────────

SPECIAL_FESTIVALS = {
    # (Masa_index, Paksha, Tithi_number_in_paksha): ("Festival Name", "Observance Note")
    (0, "Shukla", 1): ("Chaitra Navratri Day 1 / Ugadi / Gudi Padwa", "Hindu New Year begins. Great auspiciousness."),
    (0, "Shukla", 9): ("Ram Navami", "Appearance day of Bhagwan Sri Ram."),
    (4, "Shukla", 5): ("Nag Panchami", "Dedicated to Serpent deities and spiritual protection."),
    (4, "Shukla", 15): ("Raksha Bandhan", "Celebration of sibling bonds and protection."),
    (5, "Krishna", 8): ("Krishna Janmashtami", "Midnight appearance of Bhagwan Sri Krishna."),
    (5, "Shukla", 4): ("Ganesh Chaturthi", "Welcoming Lord Ganesha, remover of all obstacles."),
    (6, "Shukla", 1): ("Sharad Navratri Day 1", "Worship of Maa Durga begins."),
    (6, "Shukla", 10): ("Vijayadashami / Dussehra", "Triumph of dharma over adharma."),
    (7, "Krishna", 13): ("Dhanteras", "Welcoming Lord Dhanvantari & Goddess Lakshmi."),
    (7, "Krishna", 30): ("Deepawali / Diwali", "Maha Lakshmi Puja & festival of lights."),
    (10, "Krishna", 14): ("Maha Shivratri", "The Great Night of Lord Shiva. All-night vigil & meditation."),
    (11, "Shukla", 15): ("Holi", "Festival of colors, devotion of Prahlada, victory of faith.")
}


def _detect_festival(masa_idx: int, paksha: str, tithi_in_paksha: int) -> tuple[bool, str, str]:
    # Check fixed named festivals
    key = (masa_idx, paksha, tithi_in_paksha)
    if key in SPECIAL_FESTIVALS:
        name, note = SPECIAL_FESTIVALS[key]
        return True, name, note

    # Recurring high-significance Tithis
    if tithi_in_paksha == 11:
        return True, f"{paksha} Ekadashi Vrat", "Supreme day of Lord Vishnu devotion, fasting, and spiritual purification."
    if tithi_in_paksha == 13:
        return True, f"{paksha} Pradosh Vrat", "Evening twilight dedicated to Lord Shiva; dissolves karmic hurdles."
    if paksha == "Shukla" and tithi_in_paksha == 15:
        return True, "Purnima (Full Moon)", "Peak spiritual energy, Satyanarayan Puja, and gratitude meditation."
    if paksha == "Krishna" and tithi_in_paksha == 15:
        return True, "Amavasya (New Moon)", "Ancestral blessings (Pitru Tarpan), self-reflection, and inner stillness."

    return False, "", ""


# ── Main Panchang Calculator ────────────────────────────────────────────────

def calculate_daily_panchang(target_date: dt.date | None = None) -> DailyPanchang:
    """Calculates full Daily Cosmic Blueprint Panchang for given date (default today IST)."""
    if target_date is None:
        ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
        target_date = dt.datetime.now(ist_tz).date()

    # Sunrise reference for India (06:00 IST = 00:30 UTC)
    sunrise_time, sunset_time = _approx_sun_times(target_date)
    sunrise_dt = dt.datetime.combine(target_date, sunrise_time)
    sunset_dt = dt.datetime.combine(target_date, sunset_time)
    
    # Julian day at sunrise UTC (IST is UTC+5:30)
    sunrise_utc_hour = (sunrise_time.hour + sunrise_time.minute / 60.0) - 5.5
    jd = _julian_day(target_date.year, target_date.month, target_date.day, sunrise_utc_hour)
    ayanamsha = _lahiri_ayanamsha(jd)

    # Tropical & Sidereal (Nirayana) Positions
    sun_trop = _sun_longitude(jd)
    moon_trop = _moon_longitude(jd)
    sun_sidereal = (sun_trop - ayanamsha) % 360.0
    moon_sidereal = (moon_trop - ayanamsha) % 360.0

    # Tithi Calculation (0 to 29)
    diff = (moon_sidereal - sun_sidereal) % 360.0
    tithi_index = int(diff // 12.0)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_in_paksha = (tithi_index % 15) + 1
    tithi_base_name = TITHI_NAMES[tithi_index]
    tithi_name = f"{paksha} {tithi_base_name}" if tithi_base_name not in ("Purnima", "Amavasya") else tithi_base_name

    # Nakshatra Calculation (0 to 26)
    nakshatra_index = int((moon_sidereal % 360.0) // (360.0 / 27.0))
    nakshatra_name = NAKSHATRA_NAMES[nakshatra_index]

    # Rashi Calculation (0 to 11)
    sun_rashi_idx = int(sun_sidereal // 30.0)
    moon_rashi_idx = int(moon_sidereal // 30.0)
    sun_rashi = RASHI_NAMES[sun_rashi_idx]
    moon_rashi = RASHI_NAMES[moon_rashi_idx]

    # Hindu Lunar Month (Amanta system based on Sun sign + alignment)
    # Sun sign in Aries (0) -> Chaitra/Vaishakha
    masa_idx = (sun_rashi_idx) % 12
    masa_name = MASA_NAMES[masa_idx]

    # Weekday & Deity
    weekday_idx = target_date.weekday()  # 0=Monday, 6=Sunday
    vara = VARA_INFO[weekday_idx]

    # Abhijit Muhurta: approx 48 minutes centered on solar noon
    daylight_duration = sunset_dt - sunrise_dt
    solar_noon = sunrise_dt + daylight_duration / 2
    abhijit_start = solar_noon - dt.timedelta(minutes=24)
    abhijit_end = solar_noon + dt.timedelta(minutes=24)
    abhijit_str = _fmt_window(abhijit_start, abhijit_end)

    # Rahu Kaal: 1/8th of daylight duration
    rahu_start_part, rahu_end_part = RAHU_KAAL_PARTS[weekday_idx]
    part_duration = daylight_duration / 8
    rahu_start = sunrise_dt + part_duration * rahu_start_part
    rahu_end = sunrise_dt + part_duration * rahu_end_part
    rahu_str = _fmt_window(rahu_start, rahu_end)

    # Festival / Vrat Check
    is_fest, fest_name, fest_note = _detect_festival(masa_idx, paksha, tithi_in_paksha)

    # Determine 7-day content rotation theme
    if is_fest:
        content_theme = "festival_alert"
    elif weekday_idx == 5:  # Saturday
        content_theme = "saturday_shani"
    elif weekday_idx == 6:  # Sunday
        content_theme = "sunday_numerology"
    else:  # Monday - Friday
        content_theme = "daily_panchang"

    # Numerology (Sunday calculation or daily root number)
    def sum_digits(n: int) -> int:
        while n > 9:
            n = sum(int(d) for d in str(n))
        return n

    root_num = sum_digits(target_date.day)
    destiny_num = sum_digits(target_date.day + target_date.month + target_date.year)

    # Planetary Transits (Gochar) & Classical Shastra Rashi Analysis
    T = (jd - 2451545.0) / 36525.0
    L_jup = (34.351519 + 3034.905661 * T) % 360.0 - ayanamsha
    L_sat = (50.077444 + 1222.113794 * T) % 360.0 - ayanamsha
    L_rahu = (259.183275 - 1934.134925 * T) % 360.0 - ayanamsha

    jup_rashi_idx = int((L_jup % 360.0) // 30.0)
    sat_rashi_idx = int((L_sat % 360.0) // 30.0)
    rahu_rashi_idx = int((L_rahu % 360.0) // 30.0)
    ketu_rashi_idx = (rahu_rashi_idx + 6) % 12

    # Favorable and caution rashis from Jupiter (2,5,7,9,11) and Saturn (3,6,11)
    favorable_rashis, caution_rashis = [], []
    for r_idx in range(12):
        dist_jup = ((jup_rashi_idx - r_idx + 12) % 12) + 1
        dist_sat = ((sat_rashi_idx - r_idx + 12) % 12) + 1
        name = RASHI_NAMES[r_idx].split()[0]
        if dist_jup in (2, 5, 7, 9, 11) or dist_sat in (3, 6, 11):
            if name not in favorable_rashis:
                favorable_rashis.append(name)
        elif dist_sat in (12, 1, 2, 4, 8):
            if name not in caution_rashis:
                caution_rashis.append(name)

    # Rotating Dasha Educational Spotlight
    dasha_idx = (target_date.timetuple().tm_yday) % len(VIMSHOTTARI_MAHADASHAS)
    d_title, d_desc = VIMSHOTTARI_MAHADASHAS[dasha_idx]

    gochar_snapshot = GocharSnapshot(
        sun_sign=sun_rashi,
        moon_sign=moon_rashi,
        jupiter_sign=RASHI_NAMES[jup_rashi_idx],
        saturn_sign=RASHI_NAMES[sat_rashi_idx],
        rahu_sign=RASHI_NAMES[rahu_rashi_idx],
        ketu_sign=RASHI_NAMES[ketu_rashi_idx],
        favorable_rashis=favorable_rashis[:4],
        caution_rashis=caution_rashis[:3],
        dasha_spotlight_title=d_title,
        dasha_spotlight_desc=d_desc
    )

    tithi_name_hi = f"{'शुक्ल' if paksha == 'Shukla' else 'कृष्ण'} {TITHI_NAMES_HI[tithi_index]}" if tithi_base_name not in ("Purnima", "Amavasya") else ("पूर्णिमा" if tithi_base_name == "Purnima" else "अमावस्या")
    nakshatra_name_hi = NAKSHATRA_NAMES_HI[nakshatra_index]
    masa_name_hi = MASA_NAMES_HI[masa_idx]
    paksha_hi = "शुक्ल पक्ष" if paksha == "Shukla" else "कृष्ण पक्ष"
    moon_rashi_hi = RASHI_NAMES_HI[moon_rashi_idx]
    sun_rashi_hi = RASHI_NAMES_HI[sun_rashi_idx]
    vara_hi = vara.get("name_hi", vara["name_sa"])
    deity_hi = vara.get("deity_hi", vara["deity"])
    date_formatted_hi = f"{vara_hi}, {target_date.day} {masa_name_hi} {target_date.year}"

    date_formatted = target_date.strftime("%A, %d %B %Y")

    return DailyPanchang(
        date=target_date,
        date_formatted=date_formatted,
        date_formatted_hi=date_formatted_hi,
        weekday_index=weekday_idx,
        vara_sa=vara["name_sa"],
        vara_en=vara["name_en"],
        vara_hi=vara_hi,
        deity=vara["deity"],
        deity_hi=deity_hi,
        color=vara["color"],
        significance=vara["significance"],
        remedy=vara["remedy"],
        paksha=paksha,
        paksha_hi=paksha_hi,
        tithi_index=tithi_index,
        tithi_name=tithi_name,
        tithi_name_hi=tithi_name_hi,
        masa_name=masa_name,
        masa_name_hi=masa_name_hi,
        nakshatra_index=nakshatra_index,
        nakshatra_name=nakshatra_name,
        nakshatra_name_hi=nakshatra_name_hi,
        moon_rashi=moon_rashi,
        moon_rashi_hi=moon_rashi_hi,
        sun_rashi=sun_rashi,
        sun_rashi_hi=sun_rashi_hi,
        sunrise_str=_fmt_time(sunrise_time),
        sunset_str=_fmt_time(sunset_time),
        abhijit_muhurta=abhijit_str,
        rahu_kaal=rahu_str,
        gochar=gochar_snapshot,
        content_theme=content_theme,
        is_festival=is_fest,
        festival_name=fest_name,
        festival_note=fest_note,
        root_number=root_num,
        destiny_number=destiny_num,
        numerology_focus=f"Root {root_num} • Destiny {destiny_num} (Surya Solar Resonance)"
    )
