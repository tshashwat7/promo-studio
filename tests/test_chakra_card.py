"""Chakra promotion: bilingual, illustrative, measured and reproducible."""
import tempfile
import unittest
from datetime import date
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from promo_studio import PromoStudio, mock_art
from promo_studio.chakra_card import COPY, plan
from promo_studio.models import PostSpec
from test_daily import inputs, on_day
from test_panchang_card import overlaps

ROOT = Path(__file__).resolve().parent.parent
WEDNESDAY = date(2026, 10, 7)


class ChakraCardTests(unittest.TestCase):
    def spec(self):
        return PostSpec("chakra", WEDNESDAY.isoformat(), {}, True)

    def test_bilingual_copy_is_measured_and_never_overlaps(self):
        draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))
        fonts = (mock_art.ROOT / "fonts").resolve()
        for language in ("en", "hi"):
            with self.subTest(language=language):
                items = plan(draw, language)
                roles = {i.role: i for i in items}
                self.assertEqual(tuple(roles[f"chakra:{n}"].value for n in range(7)),
                                 COPY[language]["names"])
                self.assertEqual(roles["disclaimer"].value, COPY[language]["disclaimer"])
                for a, b in combinations(items, 2):
                    self.assertFalse(overlaps(a.box, b.box), f"{a.role} overlaps {b.role}")
                for item in items:
                    self.assertLessEqual(item.box[2], 1040, item.role)
                    self.assertTrue(Path(item.font.path).resolve().is_relative_to(fonts))
                    if language == "hi" and item.kind == "text":
                        self.assertTrue(item.font.covers(item.value), item.value)

    def test_pipeline_writes_both_languages_on_wednesday(self):
        for language in ("en", "hi"):
            daily, muhu = inputs()
            on_day(daily, muhu, WEDNESDAY)
            with tempfile.TemporaryDirectory() as folder:
                result = PromoStudio(folder).generate(daily, muhu, expected_date=WEDNESDAY,
                                                     language=language)
                self.assertEqual((result["post_type"], result["illustrative"]), ("chakra", True))
                self.assertEqual(result["caption_input"]["facts"], {})
                with Image.open(result["path"]) as saved:
                    expected = mock_art.render(self.spec(), language)
                    self.assertIsNone(ImageChops.difference(saved.convert("RGB"), expected).getbbox())

    def test_approved_english_and_hindi_images(self):
        for language in ("en", "hi"):
            path = ROOT / "tests" / "golden" / f"chakra-{language}.png"
            if not path.is_file():
                continue
            with self.subTest(language=language), Image.open(path) as golden:
                diff = ImageChops.difference(mock_art.render(self.spec(), language),
                                             golden.convert("RGB"))
                self.assertLessEqual(max(ImageStat.Stat(diff).mean), 1.0)


if __name__ == "__main__":
    unittest.main()
