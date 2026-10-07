"""Kundli feature-preview checks: bilingual, illustrative, measured and reproducible."""
import tempfile
import unittest
from datetime import date
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from promo_studio import PromoStudio, mock_art
from promo_studio.kundli_card import COPY, FEATURE_BOXES, plan
from promo_studio.models import PostSpec
from test_daily import inputs, on_day
from test_panchang_card import overlaps


ROOT = Path(__file__).resolve().parent.parent
SATURDAY = date(2026, 10, 10)


class KundliCardTests(unittest.TestCase):
    def spec(self):
        return PostSpec("kundli", SATURDAY.isoformat(), {}, True)

    def test_bilingual_copy_is_measured_and_clear_of_artwork(self):
        canvas = Image.new("RGB", (1080, 1350))
        for language in ("en", "hi"):
            with self.subTest(language=language):
                items = plan(ImageDraw.Draw(canvas), language)
                roles = {item.role: item for item in items}
                self.assertEqual(roles["title"].value, COPY[language]["title"])
                self.assertEqual(roles["sample"].value, COPY[language]["sample"])
                self.assertEqual(roles["disclaimer"].value, COPY[language]["disclaimer"])
                self.assertEqual(roles["button"].value, COPY[language]["button"])
                self.assertEqual(tuple(roles[f"feature-panel:{n}"].box for n in range(4)),
                                 FEATURE_BOXES)
                self.assertEqual(tuple(roles[f"feature:{n}"].value for n in range(4)),
                                 COPY[language]["features"])
                texts = [item for item in items if item.kind == "text"]
                for a, b in combinations(texts, 2):
                    self.assertFalse(overlaps(a.box, b.box), f"{a.role} overlaps {b.role}")
                for n, box in enumerate(FEATURE_BOXES):
                    child = roles[f"feature:{n}"].box
                    self.assertTrue(box[0] < child[0] and child[2] < box[2] and
                                    box[1] < child[1] and child[3] < box[3])
                self.assertTrue(0 < roles["button"].box[0] < roles["button"].box[2] < 1080)
                for item in texts + [roles["button"]]:
                    self.assertTrue(Path(item.font.path).resolve().is_relative_to(
                        (mock_art.ROOT / "fonts").resolve()), item.role)
                    if language == "hi" and item.kind == "text":
                        self.assertTrue(item.font.covers(item.value), item.value)

    def test_chart_is_only_a_sample_and_ignores_personal_facts(self):
        spec = self.spec()
        self.assertEqual(spec.to_dict()["facts"], {})
        self.assertTrue(spec.illustrative)
        for language in ("en", "hi"):
            expected = mock_art.render(spec, language)
            unexpected = PostSpec("kundli", spec.date,
                                  {"planet": "Mars", "rashi": "Cancer"}, True)
            actual = mock_art.render(unexpected, language)
            self.assertIsNotNone(expected)
            self.assertIsNone(ImageChops.difference(expected, actual).getbbox())

    def test_pipeline_writes_both_language_versions_without_a_duplicate_label(self):
        for language in ("en", "hi"):
            daily, muhu = inputs()
            on_day(daily, muhu, SATURDAY)
            with tempfile.TemporaryDirectory() as folder:
                result = PromoStudio(folder).generate(daily, muhu, expected_date=SATURDAY,
                                                     language=language)
                self.assertEqual(result["post_type"], "kundli")
                self.assertTrue(result["illustrative"])
                self.assertEqual(result["caption_input"]["facts"], {})
                self.assertEqual(Path(result["path"]).name,
                                 f"2026-10-10_kundli{'_hi' if language == 'hi' else ''}_1080x1350.png")
                with Image.open(result["path"]) as saved:
                    self.assertEqual(saved.size, (1080, 1350))
                    expected = mock_art.render(self.spec(), language)
                    self.assertIsNone(ImageChops.difference(saved.convert("RGB"), expected).getbbox())

    def test_approved_english_and_hindi_images(self):
        for language in ("en", "hi"):
            path = ROOT / "tests" / "golden" / f"kundli-2026-10-10-{language}.png"
            if not path.is_file():
                continue
            with self.subTest(language=language), Image.open(path) as golden:
                actual = mock_art.render(self.spec(), language)
                difference = ImageChops.difference(actual, golden.convert("RGB"))
                self.assertLessEqual(max(ImageStat.Stat(difference).mean), 1.0)


if __name__ == "__main__":
    unittest.main()
