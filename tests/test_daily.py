"""Offline daily selection and rendering contract tests using real local inputs."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from promo_studio import DataError, PromoStudio
from promo_studio.adapter import (DAY_CYCLE, DAY_START, NIGHT_CYCLE, NIGHT_START, OCTANT_WINDOWS,
                                  adapt_siddhanta, choghadiya_order)
from promo_studio.models import minutes
from promo_studio.selector import select

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
TODAY = date(2026, 10, 5)


def inputs():
    return (json.loads((FIXTURES / "data-2026-10-05.json").read_text(encoding="utf-8")),
            json.loads((FIXTURES / "muhu-2026-10-05.json").read_text(encoding="utf-8")))


def clock(total: float) -> str:
    hour, minute = divmod(int(total), 60)
    return f"{(hour - 1) % 12 + 1}:{minute:02d} {'PM' if hour >= 12 else 'AM'}"


def on_day(daily, muhurta, day):
    """Move the fixture to another weekday with windows consistent with its sunrise/sunset."""
    weekday = day.strftime("%A")
    daily["today"]["date"] = day.isoformat()
    daily["today"]["day_of_week_en"] = weekday
    muhurta["date"] = day.isoformat()
    english = daily["today"]["english"]
    rise, sset = minutes(english["sunrise"]), minutes(english["sunset"])
    eighth, noon = (sset - rise) / 8, (rise + sset) / 2
    for key, octants in OCTANT_WINDOWS.items():
        start = rise + (octants[weekday] - 1) * eighth
        muhurta["muhurtas"][key].update(start=clock(start), end=clock(start + eighth))
    muhurta["muhurtas"]["abhijit_muhurta"].update(start=clock(noon - 24), end=clock(noon + 24))
    sun = daily["transits"]["positions"]["sun"]
    total = sun["longitude_total"] + 0.9856 * (day - TODAY).days  # Mean daily solar motion.
    sun.update(longitude_total=round(total, 2), degree_in_rashi=round(total % 30, 2))
    chog = muhurta["choghadiya"]
    attributes = {s["name_en"]: {k: v for k, v in s.items() if k not in ("slot_number", "start", "end")}
                  for s in chog["day"] + chog["night"]}
    for part, cycle, starts in (("day", DAY_CYCLE, DAY_START), ("night", NIGHT_CYCLE, NIGHT_START)):
        for slot, name in zip(chog[part], choghadiya_order(cycle, starts[weekday])):
            slot.update(attributes[name])


class DailyTests(unittest.TestCase):
    def test_real_inputs_render_and_repeat(self):
        daily, muhu = inputs()
        with tempfile.TemporaryDirectory() as folder:
            studio = PromoStudio(folder)
            one = studio.generate(daily, muhu, expected_date=TODAY)
            two = studio.generate(daily, muhu, expected_date=TODAY)
            self.assertEqual(one["post_type"], "panchang")
            self.assertEqual(one["sha256"], two["sha256"])
            self.assertEqual(one["sha256"], hashlib.sha256(Path(one["path"]).read_bytes()).hexdigest())
            with Image.open(one["path"]) as image:
                self.assertEqual(image.size, (1080, 1350))
            self.assertEqual(studio.generate(daily, muhu, expected_date=TODAY,
                                            overwrite=False)["skipped"], True)
            self.assertNotIn("ready_caption", json.dumps(one["caption_input"]))
            self.assertNotIn("upcoming_festivals", json.dumps(one["caption_input"]))

    def test_invalid_or_stale_data_writes_nothing(self):
        for mutation in (lambda d, m: m.update(date="2026-10-04"),
                         lambda d, m: d["today"].update(festivals_today={}),
                         lambda d, m: d["today"]["english"].update(tithi_name=""),
                         lambda d, m: d["today"].update(day_of_week_en="Sunday")):
            daily, muhu = inputs()
            mutation(daily, muhu)
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(DataError):
                    PromoStudio(folder).generate(daily, muhu, expected_date=TODAY)
                self.assertFalse(list(Path(folder).iterdir()))

    def test_future_festival_is_never_today(self):
        daily, muhu = inputs()
        data, windows = adapt_siddhanta(daily, muhu, TODAY)
        self.assertEqual(select(data, windows).kind, "panchang")
        daily["today"]["festivals_today"] = [{"id": "indira_ekadashi",
                              "name_en": "Indira Ekadashi",
                              "name_hi": "इन्दिरा एकादशी"}]
        data, windows = adapt_siddhanta(daily, muhu, TODAY)
        spec = select(data, windows)
        self.assertEqual(spec.kind, "festival")
        self.assertEqual(spec.to_dict()["facts"]["festival_id"], "indira_ekadashi")
        self.assertEqual(spec.to_dict()["facts"]["festival"], "Indira Ekadashi")

    def test_weekday_rules_and_factual_transit(self):
        expected = {6: "muhurta", 7: "chakra", 8: "muhurta", 9: "transit", 10: "kundli"}
        for day_number, kind in expected.items():
            daily, muhu = inputs()
            target = date(2026, 10, day_number)
            on_day(daily, muhu, target)
            data, windows = adapt_siddhanta(daily, muhu, target)
            spec = select(data, windows)
            self.assertEqual(spec.kind, kind)
            self.assertEqual(spec.illustrative, kind in ("kundli", "chakra"))
            if kind == "transit":
                self.assertEqual(spec.facts["planet"], "Mars")
                self.assertEqual(spec.facts["rashi"], "Cancer")
                self.assertNotIn("phase_end", spec.facts)
            if spec.illustrative:
                self.assertEqual(spec.to_dict()["facts"], {})

    def test_each_selected_card_renders(self):
        scenarios = [(6, "muhurta"), (7, "chakra"), (9, "transit"),
                     (10, "kundli"), (11, "festival")]
        with tempfile.TemporaryDirectory() as folder:
            for day_number, kind in scenarios:
                daily, muhu = inputs()
                target = date(2026, 10, day_number)
                on_day(daily, muhu, target)
                if kind == "festival":
                    daily["today"]["festivals_today"] = [{"id": "navratri_start_shaiva",
                                                           "name_en": "Navratri (Start)",
                                                           "name_hi": "नवरात्रि"}]
                result = PromoStudio(Path(folder) / kind).generate(
                    daily, muhu, expected_date=target)
                self.assertEqual(result["post_type"], kind)
                with Image.open(result["path"]) as image:
                    self.assertEqual(image.size, (1080, 1350))
                json.dumps(result["caption_input"], ensure_ascii=False)

    def test_node_motion_is_normalized_without_mutating_source(self):
        daily, muhu = inputs()
        original = copy.deepcopy(daily)
        data, _ = adapt_siddhanta(daily, muhu, TODAY)
        self.assertEqual(data["transits"]["positions"]["rahu"]["motion_en"], "Retrograde")
        self.assertEqual(daily, original)

    def test_template_changes_art_not_caption_facts(self):
        import promo_studio.mock_art as artwork
        daily, muhu = inputs()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            templated = PromoStudio(root / "templates").generate(daily, muhu, expected_date=TODAY)
            with patch.object(artwork, "ROOT", root / "missing"):
                fallback = PromoStudio(root / "fallback").generate(daily, muhu, expected_date=TODAY)
            self.assertNotEqual(templated["sha256"], fallback["sha256"])
            self.assertEqual(templated["caption_input"], fallback["caption_input"])

    def test_festival_art_exact_match_and_neutral_unknown(self):
        import promo_studio.mock_art as artwork
        cases = {event_id: Path(path).name for event_id, path in artwork.FESTIVAL_ART.items()}
        for event_id, filename in cases.items():
            with self.subTest(event_id=event_id):
                self.assertEqual(artwork.festival_art(event_id), f"content/festivals/{filename}")
                self.assertTrue((artwork.ROOT / artwork.festival_art(event_id)).is_file())
        self.assertEqual(artwork.ROOT.name, "assets")
        self.assertTrue(all(path.startswith("templates/active/") for path in artwork.TEMPLATES.values()))
        self.assertEqual(artwork.LOGO, "branding/logo.webp")
        self.assertEqual(artwork.GENERIC_FESTIVAL_ART, "content/festivals/Generic festival.webp")
        self.assertEqual(artwork.festival_art("unknown_event_id"), artwork.GENERIC_FESTIVAL_ART)
        self.assertNotEqual(artwork.festival_art("janmashtami"),
                            artwork.festival_art("shivratri_monthly"))
        daily, muhu = inputs()
        for event_id in (*cases, "unknown_event_id"):
            with self.subTest(render=event_id):
                daily["today"]["festivals_today"] = [{"id": event_id,
                                                       "name_en": "Example Festival",
                                                       "name_hi": "उदाहरण पर्व"}]
                data, windows = adapt_siddhanta(daily, muhu, TODAY)
                spec = select(data, windows)
                self.assertEqual(spec.kind, "festival")
                image = artwork.render(spec)
                self.assertIsNotNone(image)
                self.assertEqual(image.size, (1080, 1350))

    def test_missing_specific_festival_uses_neutral_scene(self):
        import promo_studio.mock_art as artwork
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            generic = root / artwork.GENERIC_FESTIVAL_ART
            generic.parent.mkdir(parents=True)
            Image.new("RGB", (32, 32), "#F0D5AA").save(generic)
            with patch.object(artwork, "ROOT", root):
                self.assertEqual(artwork.festival_art("navratri_start_shaiva"),
                                 artwork.GENERIC_FESTIVAL_ART)
                self.assertEqual(artwork.festival_art("unknown_event_id"),
                                 artwork.GENERIC_FESTIVAL_ART)

    def test_panchang_facts_overlay_art_without_panels(self):
        import promo_studio.mock_art as artwork
        daily, muhu = inputs()
        data, windows = adapt_siddhanta(daily, muhu, TODAY)
        image = artwork.render(select(data, windows))
        self.assertIsNotNone(image)
        # Moon and temple stay untouched by the wash and the type.
        background = artwork._canvas("panchang")
        self.assertEqual(image.getpixel((880, 180)), background.getpixel((880, 180)))
        self.assertEqual(image.getpixel((956, 930)), background.getpixel((956, 930)))
        tithi_icon = (190, 312, 230, 352)
        self.assertNotEqual(image.crop(tithi_icon).tobytes(),
                            background.crop(tithi_icon).tobytes())
        self.assertEqual(image.size, (1080, 1350))

    def test_festival_render_and_missing_art_preserve_facts(self):
        import promo_studio.mock_art as artwork
        daily, muhu = inputs()
        daily["today"]["festivals_today"] = [{"id": "navratri_start_shaiva",
                             "name_en": "Navratri (Start)",
                                                 "name_hi": "नवरात्रि"}]
        daily["today"]["image"] = {"local_asset_path": "../../untrusted.webp"}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            illustrated = PromoStudio(root / "art").generate(daily, muhu, expected_date=TODAY)
            with patch.object(artwork, "ROOT", root / "missing"):
                fallback = PromoStudio(root / "fallback").generate(daily, muhu, expected_date=TODAY)
            self.assertEqual(illustrated["post_type"], "festival")
            self.assertEqual(illustrated["caption_input"], fallback["caption_input"])
            self.assertNotEqual(illustrated["sha256"], fallback["sha256"])
            self.assertNotIn("untrusted.webp", json.dumps(illustrated["caption_input"]))
            with Image.open(illustrated["path"]) as image:
                self.assertEqual(image.size, (1080, 1350))

    def test_logo_on_all_daily_paths_and_missing_logo_fallback(self):
        import promo_studio.mock_art as artwork
        from promo_studio.festival_card import LOGO, PAD, SCENE_PANELS
        panel = SCENE_PANELS[artwork.FESTIVAL_ART["navratri_start_shaiva"]]
        positions = {"festival": (panel[0] + PAD + LOGO // 2, panel[1] + PAD + LOGO // 2)}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for kind, day in (("panchang", TODAY), ("kundli", date(2026, 10, 10)),
                              ("festival", TODAY)):
                with self.subTest(kind=kind):
                    daily, muhu = inputs()
                    on_day(daily, muhu, day)
                    if kind == "festival":
                        daily["today"]["festivals_today"] = [
                            {"id": "navratri_start_shaiva", "name_en": "Navratri (Start)",
                             "name_hi": "नवरात्रि"}]
                    branded = PromoStudio(root / kind / "branded").generate(
                        daily, muhu, expected_date=day)
                    with patch.object(artwork, "LOGO", "missing-logo.webp"):
                        unbranded = PromoStudio(root / kind / "unbranded").generate(
                            daily, muhu, expected_date=day)
                    self.assertEqual(branded["caption_input"], unbranded["caption_input"])
                    with Image.open(branded["path"]) as logo, Image.open(unbranded["path"]) as plain:
                        self.assertEqual(logo.size, (1080, 1350))
                        position = positions.get(kind, (124, 92))
                        self.assertNotEqual(logo.getpixel(position), plain.getpixel(position))
                        # No card still carries the old footer logo.
                        self.assertEqual(logo.getpixel((960, 1268)),
                                         plain.getpixel((960, 1268)))

    def test_corrupt_logo_fails_without_partial_image(self):
        import promo_studio.mock_art as artwork
        daily, muhu = inputs()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            logo = root / artwork.LOGO
            logo.parent.mkdir(parents=True)
            logo.write_bytes(b"not an image")
            with patch.object(artwork, "ROOT", root):
                with self.assertRaises(OSError):
                    PromoStudio(root / "output").generate(daily, muhu, expected_date=TODAY)
            self.assertFalse((root / "output").exists())

    def test_corrupt_festival_art_fails_without_partial_image(self):
        import promo_studio.mock_art as artwork
        daily, muhu = inputs()
        daily["today"]["festivals_today"] = [{"id": "navratri_start_shaiva",
                             "name_en": "Navratri (Start)",
                             "name_hi": "नवरात्रि"}]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            art_path = root / artwork.FESTIVAL_ART["navratri_start_shaiva"]
            art_path.parent.mkdir(parents=True)
            art_path.write_bytes(b"not an image")
            with patch.object(artwork, "ROOT", root):
                with self.assertRaises(OSError):
                    PromoStudio(root / "output").generate(daily, muhu, expected_date=TODAY)
            self.assertFalse((root / "output").exists())

    def test_corrupt_curated_artwork_fails_without_partial_image(self):
        import promo_studio.mock_art as artwork
        daily, muhu = inputs()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            template = root / artwork.TEMPLATES["panchang"]
            template.parent.mkdir(parents=True)
            template.write_bytes(b"not an image")
            with patch.object(artwork, "ROOT", root):
                with self.assertRaises(OSError):
                    PromoStudio(root / "output").generate(daily, muhu, expected_date=TODAY)
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
