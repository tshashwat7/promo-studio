"""Acceptance tests for the Plan Your Day (Muhurta) card in English and Hindi."""
import tempfile
import unittest
from datetime import date
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageStat

from promo_studio import PromoStudio, mock_art, muhurta_card as card
from promo_studio.adapter import DAY_CYCLE, DAY_START, adapt_siddhanta, choghadiya_order
from promo_studio.card_kit import LEFT
from promo_studio.models import minutes
from promo_studio.selector import select
from test_daily import inputs, on_day
from test_panchang_card import luminance, overlaps

ROOT = Path(__file__).resolve().parent.parent
TUESDAY = date(2026, 10, 6)
GOLDEN = {lang: ROOT / "tests" / "golden" / f"muhurta-2026-10-06{'' if lang == 'en' else '-hi'}.png"
          for lang in ("en", "hi")}


def tuesday():
    """The frozen 5 Oct export moved to a Tuesday, with internally consistent windows."""
    daily, muhu = inputs()
    on_day(daily, muhu, TUESDAY)
    return daily, muhu


def tuesday_spec():
    return select(*adapt_siddhanta(*tuesday(), TUESDAY))


class MuhurtaCardTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))
        self.spec = tuesday_spec()
        self.facts = self.spec.to_dict()["facts"]

    def plan(self, language="en", facts=None):
        return card.plan(self.draw, facts or self.facts, TUESDAY, language)

    def roles(self, items):
        return {item.role: item for item in items if item.role}

    def assert_geometry(self, items):
        placed = [i for i in items if i.kind in ("text", "icon", "dot", "ring", "rule", "bar")]
        for item in placed:
            left, top, right, bottom = item.box
            self.assertGreaterEqual(left, LEFT, item.role)
            self.assertLessEqual(right, card.HEADER_RIGHT if top < 300 else card.RIGHT, item.role)
            self.assertLessEqual(bottom, card.FACT_BOTTOM, item.role)
        for a, b in combinations(placed, 2):
            self.assertFalse(overlaps(a.box, b.box), f"{a.role} overlaps {b.role}")

    def test_selected_on_tuesday_with_all_validated_windows(self):
        self.assertEqual(self.spec.kind, "muhurta")
        for key in ("abhijit", "rahu", "yamaganda", "gulika"):
            self.assertIn(key, self.facts)
        self.assertEqual([s["name_en"] for s in self.facts["choghadiya"]],
                         choghadiya_order(DAY_CYCLE, DAY_START["Tuesday"]))

    def test_every_value_is_the_exact_source_fact(self):
        daily, muhu = tuesday()
        for language, suffix in (("en", "en"), ("hi", "hi")):
            roles = self.roles(self.plan(language))
            for i, slot in enumerate(muhu["choghadiya"]["day"]):
                self.assertEqual(roles[f"slot:{i}"].value, slot[f"name_{suffix}"])
                self.assertEqual(roles[f"time:{i}"].value, f"{slot['start']} – {slot['end']}")
                quality = slot[f"quality_{suffix}"]
                self.assertEqual(roles[f"quality:{i}"].value,
                                 quality.upper() if language == "en" else quality)
            for key, source in (("rahu", "rahu_kaal"), ("yamaganda", "yamaghanta"),
                                ("gulika", "gulika_kaal")):
                window = muhu["muhurtas"][source]
                self.assertEqual(roles[f"value:{key}"].value, f"{window['start']} – {window['end']}")
                label = window[f"name_{suffix}"]
                self.assertEqual(roles[f"label:{key}"].value,
                                 label.upper() if language == "en" else label)
            self.assertEqual(roles["sunrise"].value, daily["today"]["english"]["sunrise"])
            self.assertEqual(roles["sunset"].value, daily["today"]["english"]["sunset"])

    def test_timeline_is_proportional_and_coloured_by_source_quality(self):
        bars = [i for i in self.plan() if i.role.startswith("bar:")]
        self.assertEqual(len(bars), 8)
        self.assertEqual(bars[0].box[0], LEFT)
        self.assertEqual(bars[-1].box[2], card.RIGHT)
        widths = [b.box[2] - b.box[0] for b in bars]
        self.assertLessEqual(max(widths) - min(widths), card.BAR_GAP + 1)
        for bar, slot in zip(bars, self.facts["choghadiya"]):
            self.assertEqual(bar.fill, card.QUALITY_COLOURS[slot["quality_en"]])

    def test_geometry_in_both_languages_and_with_a_long_city(self):
        long_city = {**self.facts, "location": "Thiruvananthapuram, India"}
        for language in ("en", "hi"):
            with self.subTest(language=language):
                self.assert_geometry(self.plan(language))
                self.assert_geometry(self.plan(language, long_city))

    def test_invalid_window_is_hidden_and_the_rest_close_up(self):
        daily, muhu = tuesday()
        muhu["muhurtas"]["abhijit_muhurta"].update(start="12:03 PM", end="12:51 PM")
        spec = select(*adapt_siddhanta(daily, muhu, TUESDAY))
        self.assertEqual(spec.kind, "muhurta")
        short = self.roles(card.plan(self.draw, spec.to_dict()["facts"], TUESDAY))
        full = self.roles(self.plan())
        self.assertNotIn("value:abhijit", short)
        self.assertEqual(short["icon:rahu"].box, full["icon:abhijit"].box)
        self.assertEqual(short["icon:yamaganda"].box, full["icon:rahu"].box)
        self.assertEqual(short["icon:gulika"].box, full["icon:yamaganda"].box)
        for role in ("slot:0", "note"):
            self.assertEqual(full[role].box, short[role].box)

    def test_card_can_be_requested_for_any_weekday(self):
        data, windows = adapt_siddhanta(*inputs(), date(2026, 10, 5))
        self.assertEqual(select(data, windows).kind, "panchang")
        monday = select(data, windows, "muhurta")
        self.assertEqual(monday.kind, "muhurta")
        self.assertNotIn("abhijit", monday.facts)
        self.assertEqual([s["name_en"] for s in monday.facts["choghadiya"]],
                         choghadiya_order(DAY_CYCLE, DAY_START["Monday"]))
        self.assertIsNotNone(card.plan(self.draw, monday.to_dict()["facts"], date(2026, 10, 5)))

    def test_wrong_choghadiya_order_falls_back_to_panchang(self):
        daily, muhu = tuesday()
        day = muhu["choghadiya"]["day"]
        day[0], day[1] = day[1], day[0]
        data, windows = adapt_siddhanta(daily, muhu, TUESDAY)
        self.assertEqual(windows["choghadiya"]["day"], [])
        self.assertIn("Day Choghadiya order", windows["warnings"][0])
        self.assertEqual(select(data, windows).kind, "panchang")

    def test_contrast_fonts_and_glyph_coverage(self):
        background = card.wash(mock_art._canvas("muhurta"))
        fonts = (mock_art.ROOT / "fonts").resolve()
        for language in ("en", "hi"):
            for item in self.plan(language):
                if item.kind not in ("text", "button"):
                    continue
                self.assertTrue(Path(item.font.path).resolve().is_relative_to(fonts), item.role)
                if language == "hi":
                    self.assertTrue(item.font.covers(item.value), item.value)
                if item.kind == "text":
                    mean = ImageStat.Stat(background.crop(item.box)).mean
                    fg, bg = luminance(ImageColor.getrgb(item.fill)), luminance(mean)
                    ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
                    self.assertGreaterEqual(ratio, 4.5, f"{language} {item.role} {ratio:.2f}")

    def test_slot_times_follow_the_bar_order(self):
        starts = [minutes(s["start"]) for s in self.facts["choghadiya"]]
        self.assertEqual(starts, sorted(starts))
        roles = self.roles(self.plan())
        self.assertLess(roles["slot:0"].origin[1], roles["slot:3"].origin[1])
        self.assertEqual(roles["slot:0"].origin[1], roles["slot:4"].origin[1])
        self.assertGreater(roles["slot:4"].origin[0], roles["slot:3"].origin[0])

    def test_pipeline_writes_english_and_hindi_files(self):
        with tempfile.TemporaryDirectory() as folder:
            for language in ("en", "hi"):
                result = PromoStudio(folder).generate(*tuesday(), expected_date=TUESDAY,
                                                      language=language)
                self.assertEqual(result["post_type"], "muhurta")
                with Image.open(result["path"]) as image:
                    self.assertEqual(image.size, (1080, 1350))

    def test_renders_match_approved_golden_images(self):
        for language, path in GOLDEN.items():
            if not path.is_file():
                continue
            with self.subTest(language=language):
                image = mock_art.render(self.spec, language)
                with Image.open(path) as golden:
                    diff = ImageChops.difference(image.convert("RGB"), golden.convert("RGB"))
                self.assertLessEqual(max(ImageStat.Stat(diff).mean), 1.0)


if __name__ == "__main__":
    unittest.main()
