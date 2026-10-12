"""Acceptance tests for the production Daily Panchang card (docs/panchang-design-guide.md §9)."""
import json
import tempfile
import unittest
from datetime import date
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageStat

from promo_studio import DataError, PromoStudio, mock_art, panchang_card as card
from promo_studio.adapter import adapt_siddhanta
from promo_studio.models import end_date
from promo_studio.selector import select

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 5)
GOLDEN = ROOT / "tests" / "golden" / "panchang-2026-10-05.png"
WORST_CASE = {"tithi": "Krishna Chaturdashi", "nakshatra": "Uttara Bhadrapada",
              "yoga": "Vishkambha", "karana": "Chatushpada", "masa": "Margashirsha",
              "location": "Thiruvananthapuram, India",
              "abhijit": "10:46 AM – 12:15 PM", "rahu": "10:46 AM – 12:15 PM"}


def inputs():
    fixtures = ROOT / "tests" / "fixtures"
    return (json.loads((fixtures / "data-2026-10-05.json").read_text(encoding="utf-8")),
            json.loads((fixtures / "muhu-2026-10-05.json").read_text(encoding="utf-8")))


def real_spec():
    return select(*adapt_siddhanta(*inputs(), TODAY))


def luminance(rgb):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class PanchangCardTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))
        self.facts = real_spec().to_dict()["facts"]

    def plan(self, facts=None, when=TODAY):
        return card.plan(self.draw, facts or self.facts, when)

    def roles(self, items):
        return {item.role: item for item in items if item.role}

    def assert_geometry(self, items):
        placed = [i for i in items if i.kind in ("text", "icon", "dot", "ring", "rule")]
        for item in placed:
            left, top, right, bottom = item.box
            self.assertGreaterEqual(left, card.LEFT, item.role)
            self.assertLessEqual(right, card.RIGHT, item.role)
            if top < 330:
                self.assertLessEqual(right, card.HEADER_RIGHT, f"{item.role} touches the moon")
            else:
                self.assertLessEqual(bottom, card.FACT_BOTTOM, f"{item.role} reaches the horizon")
        for a, b in combinations(placed, 2):
            self.assertFalse(overlaps(a.box, b.box), f"{a.role} overlaps {b.role}")
        button = next(i for i in items if i.kind == "button")
        self.assertEqual(button.box[0], card.LEFT)
        self.assertGreaterEqual(button.box[1], 1243, "button must clear the diya base")

    def test_every_value_is_the_exact_source_fact(self):
        roles = self.roles(self.plan())
        for key in ("tithi", "nakshatra", "yoga", "karana", "sunrise", "sunset",
                    "moonrise", "rahu"):
            self.assertEqual(roles[f"value:{key}"].value, self.facts[key])
        self.assertEqual(roles["detail:tithi"].value,
                         "Ashwin Masa (Purnimanta) · Until 2:08 AM, 6 Oct")
        self.assertEqual(roles["detail:nakshatra"].value, "Until 11:09 PM")
        self.assertEqual(next(i.value for i in self.plan() if i.kind == "button"),
                 "Check your city's Panchang on Siddhanta")
        self.assertEqual(roles["date"].value, "Monday, 5 October 2026 · Ujjain")
        self.assertEqual(roles["note"].value, "All times for Ujjain · IST")
        self.assertEqual(roles["tag:rahu"].value, "Inauspicious")
        self.assertFalse(self.facts["rahu_auspicious"])
        # The source Abhijit contradicts its own sunrise/sunset, so it is not published.
        self.assertNotIn("abhijit", self.facts)
        self.assertNotIn("value:abhijit", roles)

    def test_end_times_carry_their_calendar_date(self):
        self.assertEqual(self.facts["tithi_end_date"], "2026-10-06")
        self.assertEqual(self.facts["nakshatra_end_date"], "2026-10-05")
        daily, _ = inputs()
        upcoming = {f["name_en"]: f["date"] for f in daily["upcoming_festivals"]}
        # Dashami ending at 2:08 AM on 6 Oct is what makes 6 Oct Indira Ekadashi.
        self.assertEqual(upcoming["Indira Ekadashi"], self.facts["tithi_end_date"])
        self.assertEqual(end_date(TODAY, "6:19 AM", "6:20 AM"), date(2026, 10, 6))
        self.assertEqual(end_date(TODAY, "6:20 AM", "6:20 AM"), TODAY)

    def test_inconsistent_muhurtas_are_dropped_with_warnings(self):
        _, windows = adapt_siddhanta(*inputs(), TODAY)
        self.assertNotIn("abhijit_muhurta", windows["muhurtas"])
        self.assertIn("rahu_kaal", windows["muhurtas"])
        self.assertEqual(len(windows["warnings"]), 4)
        self.assertIn("+12 min from solar noon", windows["warnings"][0])
        self.assertIn("Night Choghadiya order", windows["warnings"][1])
        # The 5 Oct engine also mis-listed Mars's and Ketu's favourable Moon signs.
        self.assertTrue(all("rashis disagree" in w for w in windows["warnings"][2:]))
        self.assertEqual(len(windows["choghadiya"]["day"]), 8)

        daily, muhu = inputs()
        muhu["muhurtas"]["abhijit_muhurta"].update(start="11:51 AM", end="12:39 PM")
        muhu["muhurtas"]["rahu_kaal"].update(start="9:17 AM", end="10:46 AM")
        _, windows = adapt_siddhanta(daily, muhu, TODAY)
        self.assertIn("abhijit_muhurta", windows["muhurtas"])
        self.assertNotIn("rahu_kaal", windows["muhurtas"])
        self.assertIn("Monday daylight segment", windows["warnings"][0])

    def test_files_for_different_locations_are_refused(self):
        daily, muhu = inputs()
        muhu["metadata"]["location"]["longitude"] = 77.2090
        with self.assertRaises(DataError):
            adapt_siddhanta(daily, muhu, TODAY)

    def test_pipeline_reports_warnings(self):
        with tempfile.TemporaryDirectory() as folder:
            result = PromoStudio(folder).generate(*inputs(), expected_date=TODAY)
        self.assertEqual(len(result["warnings"]), 4)
        self.assertNotIn("abhijit", result["caption_input"]["facts"])

    def test_real_fixture_geometry(self):
        self.assert_geometry(self.plan())

    def test_worst_case_fixture_fits_and_moves_place_to_its_own_line(self):
        items = self.plan({**self.facts, **WORST_CASE}, date(2026, 9, 30))
        roles = self.roles(items)
        self.assertEqual(roles["date"].value, "Wednesday, 30 September 2026")
        self.assertEqual(roles["place"].value, "Thiruvananthapuram")
        for key, value in WORST_CASE.items():
            if f"value:{key}" in roles:
                self.assertEqual(roles[f"value:{key}"].value, value)
        self.assert_geometry(items)

    def test_overlong_value_is_refused_not_truncated(self):
        with self.assertRaises(ValueError):
            self.plan({**self.facts, "tithi": "Krishna Chaturdashi " * 3})

    def test_missing_muhurta_hides_section_without_moving_others(self):
        partial = {k: v for k, v in self.facts.items()
                   if not k.startswith(("abhijit", "rahu"))}
        full, short = self.roles(self.plan()), self.roles(self.plan(partial))
        self.assertNotIn("value:abhijit", short)
        self.assertNotIn("label:rahu", short)
        for role in ("value:tithi", "value:yoga", "value:sunrise", "value:moonrise"):
            self.assertEqual(full[role].box, short[role].box)

    def test_type_never_below_minimum_sizes(self):
        minimum = {"label": 24, "value": 30, "detail": 22, "tag": 22, "note": 22}
        for item in self.plan({**self.facts, **WORST_CASE}, date(2026, 9, 30)):
            prefix = item.role.split(":")[0]
            if item.kind == "text" and prefix in minimum:
                self.assertGreaterEqual(item.font.size, minimum[prefix], item.role)
                if item.role in ("value:tithi", "value:nakshatra"):
                    self.assertGreaterEqual(item.font.size, 40)

    def test_text_contrast_against_actual_artwork(self):
        background = card.wash(mock_art._canvas("panchang"))
        for item in self.plan():
            if item.kind != "text":
                continue
            mean = ImageStat.Stat(background.crop(item.box)).mean
            fg, bg = luminance(ImageColor.getrgb(item.fill)), luminance(mean)
            ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
            self.assertGreaterEqual(ratio, 4.5, f"{item.role} contrast {ratio:.2f}")

    def test_bundled_fonts_and_transparent_square_icons(self):
        fonts = (mock_art.ROOT / "fonts").resolve()
        for item in self.plan():
            if item.kind in ("text", "button"):
                self.assertTrue(Path(item.font.path).resolve().is_relative_to(fonts), item.role)
        for name in card.ICONS:
            icon = card._icon_image(name, card.ICON)
            self.assertEqual((icon.mode, icon.size), ("RGBA", (card.ICON, card.ICON)))
            self.assertEqual(icon.getpixel((0, 0))[3], 0, f"{name} has a background")

    def test_wash_leaves_moon_temple_and_diya_untouched(self):
        canvas = mock_art._canvas("panchang")
        washed = card.wash(canvas)
        for point in ((880, 180), (956, 930), (150, 1150), (600, 1200)):
            self.assertEqual(washed.getpixel(point), canvas.getpixel(point), point)
        self.assertNotEqual(washed.getpixel((500, 600)), canvas.getpixel((500, 600)))

    def test_auspicious_flag_must_be_boolean(self):
        daily, muhu = inputs()
        muhu["muhurtas"]["rahu_kaal"]["is_auspicious"] = "no"
        with self.assertRaises(DataError):
            adapt_siddhanta(daily, muhu, TODAY)

    def test_render_matches_approved_golden_image(self):
        if not GOLDEN.is_file():
            self.skipTest("Golden image not present")
        image = mock_art.render(real_spec())
        with Image.open(GOLDEN) as golden:
            diff = ImageChops.difference(image.convert("RGB"), golden.convert("RGB"))
        self.assertLessEqual(max(ImageStat.Stat(diff).mean), 1.0,
                             "Panchang render drifted from the approved golden image")


HINDI_GOLDEN = ROOT / "tests" / "golden" / "panchang-2026-10-05-hi.png"
HINDI_WORST_CASE = {"paksha_hi": "शुक्ल पक्ष", "tithi_name_hi": "चतुर्दशी",
                    "nakshatra_hi": "उत्तर भाद्रपद", "yoga_hi": "विष्कुम्भ",
                    "karana_hi": "चतुष्पद", "masa_hi": "मार्गशीर्ष",
                    "location": "Thiruvananthapuram, India",
                    "abhijit": "10:46 AM – 12:15 PM", "rahu": "10:46 AM – 12:15 PM"}


class HindiPanchangCardTests(unittest.TestCase):
    assert_geometry = PanchangCardTests.assert_geometry
    roles = PanchangCardTests.roles

    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))
        self.facts = real_spec().to_dict()["facts"]

    def plan(self, facts=None, when=TODAY):
        return card.plan(self.draw, facts or self.facts, when, "hi")

    def test_every_value_is_the_exact_hindi_source_fact(self):
        daily, _ = inputs()
        hindi = daily["today"]["hindi"]
        roles = self.roles(self.plan())
        self.assertEqual(roles["value:tithi"].value, f"{hindi['paksha']} {hindi['tithi_name']}")
        for key in ("nakshatra", "yoga", "karana"):
            self.assertEqual(roles[f"value:{key}"].value, hindi[key])
        for key in ("sunrise", "sunset", "moonrise", "rahu"):
            self.assertEqual(roles[f"value:{key}"].value, self.facts[key])
        self.assertEqual(roles["detail:tithi"].value,
                         "आश्विन मास (पूर्णिमांत) · समाप्ति: 2:08 AM, 6 अक्टूबर")
        self.assertEqual(roles["detail:nakshatra"].value, "समाप्ति: 11:09 PM")
        self.assertEqual(next(i.value for i in self.plan() if i.kind == "button"),
                 "अपने शहर का पंचांग सिद्धान्त पर देखें")
        self.assertEqual(roles["date"].value, "सोमवार, 5 अक्टूबर 2026 · उज्जैन")
        self.assertEqual(hindi["date_formatted"], "5 अक्टूबर 2026, सोमवार")
        self.assertEqual(roles["tag:rahu"].value, "अशुभ")
        self.assertEqual(roles["note"].value, "सभी समय उज्जैन के अनुसार · IST")
        self.assertEqual(roles["label:rahu"].value,
                         inputs()[1]["muhurtas"]["rahu_kaal"]["name_hi"])

    def test_every_hindi_string_is_fully_covered_by_its_font(self):
        items = self.plan({**self.facts, **HINDI_WORST_CASE}, date(2026, 9, 30))
        for item in items:
            if item.kind in ("text", "button"):
                self.assertTrue(item.font.covers(item.value), f"{item.role}: {item.value}")

    def test_real_and_worst_case_geometry(self):
        self.assert_geometry(self.plan())
        items = self.plan({**self.facts, **HINDI_WORST_CASE}, date(2026, 9, 30))
        roles = self.roles(items)
        self.assertEqual(roles["value:tithi"].value, "शुक्ल पक्ष चतुर्दशी")
        self.assertEqual(roles["place"].value, "Thiruvananthapuram")
        self.assert_geometry(items)

    def test_hindi_type_minimums_and_contrast(self):
        minimum = {"label": 24, "value": 28, "detail": 22, "tag": 22, "note": 22}
        for item in self.plan({**self.facts, **HINDI_WORST_CASE}, date(2026, 9, 30)):
            prefix = item.role.split(":")[0]
            if item.kind == "text" and prefix in minimum:
                self.assertGreaterEqual(item.font.size, minimum[prefix], item.role)
        background = card.wash(mock_art._canvas("panchang"))
        for item in self.plan():
            if item.kind == "text":
                mean = ImageStat.Stat(background.crop(item.box)).mean
                fg, bg = luminance(ImageColor.getrgb(item.fill)), luminance(mean)
                ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
                self.assertGreaterEqual(ratio, 4.5, f"{item.role} contrast {ratio:.2f}")

    def test_bundled_devanagari_fonts_only(self):
        fonts = (mock_art.ROOT / "fonts").resolve()
        for item in self.plan():
            if item.kind in ("text", "button"):
                self.assertTrue(Path(item.font.path).resolve().is_relative_to(fonts), item.role)

    def test_pipeline_writes_a_separate_hindi_file(self):
        with tempfile.TemporaryDirectory() as folder:
            result = PromoStudio(folder).generate(*inputs(), expected_date=TODAY, language="hi")
            self.assertEqual(result["language"], "hi")
            self.assertTrue(result["path"].endswith("2026-10-05_panchang_hi_1080x1350.png"))
            with Image.open(result["path"]) as image:
                self.assertEqual(image.size, (1080, 1350))

    def test_unsupported_language_is_refused(self):
        spec = select(*adapt_siddhanta(*inputs(), TODAY))
        with self.assertRaises(ValueError):
            mock_art.render(spec, "ta")

    def test_render_matches_approved_hindi_golden_image(self):
        if not HINDI_GOLDEN.is_file():
            self.skipTest("Hindi golden image not present")
        image = mock_art.render(real_spec(), "hi")
        with Image.open(HINDI_GOLDEN) as golden:
            diff = ImageChops.difference(image.convert("RGB"), golden.convert("RGB"))
        self.assertLessEqual(max(ImageStat.Stat(diff).mean), 1.0,
                             "Hindi Panchang render drifted from the approved golden image")


if __name__ == "__main__":
    unittest.main()
