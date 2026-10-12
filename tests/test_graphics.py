"""Focused checks for the offline graphics engine."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from graphics.artwork import festival_artwork
from graphics.background_engine import BackgroundEngine
from graphics.ornament_engine import ornament
from make_cards import _mockup_spec, card_kundli, card_plan, card_chakra, main as cards_main
from make_post import ROOT, find_font
import promo_studio.mock_art as artwork
from promo_studio.mock_art import brand, render as render_mock_art

DATA = ROOT / "tests" / "fixtures" / "data-2026-10-05.json"
MUHU = ROOT / "tests" / "fixtures" / "muhu-2026-10-05.json"


def inputs():
    return (json.loads(DATA.read_text(encoding="utf-8")),
            json.loads(MUHU.read_text(encoding="utf-8")))


class GraphicsTests(unittest.TestCase):
    def test_themes_are_repeatable_and_distinct(self):
        a = BackgroundEngine.create("plan", 80, 100)
        b = BackgroundEngine.create("plan", 80, 100)
        self.assertEqual(a.tobytes(), b.tobytes())
        self.assertNotEqual(a.tobytes(), BackgroundEngine.create("chakra", 80, 100).tobytes())

    def test_svg_motifs_have_transparent_pixels(self):
        for name in ("mandala", "moon", "temple", "lotus", "kundli", "zodiac", "diya", "planet"):
            with self.subTest(name=name):
                image = ornament(name, 220)
                self.assertEqual(image.size, (220, 220))
                self.assertEqual(image.mode, "RGBA")
                lo, hi = image.getchannel("A").getextrema()
                self.assertEqual(lo, 0)
                self.assertGreater(hi, 0)

    def test_artwork_must_be_approved_local_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approved = root / "assets" / "illustrations" / "festivals" / "festival.png"
            approved.parent.mkdir(parents=True)
            Image.new("RGBA", (50, 60), (255, 0, 0, 100)).save(approved)
            entry = {"image": {"local_asset_path": "assets/illustrations/festivals/festival.png"}}
            art = festival_artwork(entry, root, (30, 30))
            self.assertIsNotNone(art)
            self.assertLessEqual(art.width, 30)
            self.assertIsNone(festival_artwork({"image": {"local_asset_path": "../elsewhere.png"}},
                                               root, (30, 30)))
            self.assertIsNone(festival_artwork({"image": {"github_raw_url": "https://example.org/a.png"}},
                                               root, (30, 30)))

    def test_promos_ignore_json_content_but_plan_uses_muhurta(self):
        font = find_font([r"C:\Windows\Fonts\Nirmala.ttc",
                          "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"])
        data, muhu = inputs()
        for render in (card_kundli, card_chakra):
            self.assertEqual(render(data, muhu, font).tobytes(), render({}, {}, font).tobytes())
        before = card_plan(data, muhu, font).tobytes()
        muhu["muhurtas"]["rahu_kaal"]["start"] = "8:00 AM"
        self.assertNotEqual(before, card_plan(data, muhu, font).tobytes())

    def test_six_card_cli_uses_mockups_and_marks_future_event(self):
        data, muhu = inputs()
        festival = _mockup_spec("03-upcoming-festival", data, muhu)
        self.assertEqual(festival.date, "2026-10-11")
        self.assertTrue(festival.facts["upcoming"])
        self.assertEqual(festival.facts["days_away"], 6)
        self.assertNotIn("tithi", festival.facts)
        with tempfile.TemporaryDirectory() as directory:
            args = ["make_cards.py", "--date", "2026-10-05", "--output-dir", directory,
                    "--data", str(DATA), "--muhurta", str(MUHU)]
            with patch("sys.argv", args):
                cards_main()
            files = sorted(Path(directory).glob("*.png"))
            self.assertEqual(len(files), 6)
            for name, path in zip(("01-daily-panchang", "02-plan-your-day",
                                   "03-upcoming-festival", "04-kundli-promo",
                                   "05-chakra-promo", "06-planetary-transit"), files):
                with self.subTest(name=name):
                    spec = _mockup_spec(name, data, muhu)
                    expected = render_mock_art(spec)
                    self.assertIsNotNone(expected)
                    with Image.open(path) as actual:
                        self.assertEqual(actual.size, (1080, 1350))
                        self.assertEqual(actual.convert("RGB").tobytes(),
                                         brand(expected, spec.kind).tobytes())
            self.assertTrue((Path(directory) / "caption-2026-10-05.txt").is_file())

    def test_reference_promos_and_festival_have_no_invented_readings(self):
        from datetime import date
        from PIL import ImageDraw
        from promo_studio import chakra_card, festival_card, kundli_card
        data, muhu = inputs()
        for card in ("03-upcoming-festival", "04-kundli-promo", "05-chakra-promo"):
            self.assertEqual(artwork.render(_mockup_spec(card, data, muhu)).size, (1080, 1350))
        draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))
        festival = _mockup_spec("03-upcoming-festival", data, muhu)
        values = [i.value for i in festival_card.plan(
            draw, festival.to_dict()["facts"], date.fromisoformat(festival.date),
            artwork.festival_art(festival.facts.get("festival_id")))]
        values += [i.value for i in kundli_card.plan(draw) + chakra_card.plan(draw)]
        text = " ".join(values)
        self.assertIn("Navratri Begins", text)
        self.assertIn("11 October 2026", text)
        self.assertIn("In 6 days", text)
        self.assertIn("SAMPLE", text)
        self.assertIn("Root", text)
        self.assertIn("not a personal assessment", text)
        self.assertNotIn("75%", text)
        self.assertNotIn("12:03 PM", text)


if __name__ == "__main__":
    unittest.main()
