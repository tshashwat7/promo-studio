"""Festival card: exact facts, both languages, every scene's panel, and no fast-breaking times."""
import json
import tempfile
import unittest
from datetime import date
from itertools import combinations
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageOps, ImageStat

from promo_studio import PromoStudio, card_kit as kit, mock_art
from promo_studio import festival_card as card
from promo_studio.adapter import adapt_siddhanta
from promo_studio.models import PostSpec
from promo_studio.selector import select
from test_panchang_card import luminance, overlaps

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OCT_6 = date(2026, 10, 6)
GOLDEN = ROOT / "tests" / "golden"
WORST = {"location": "Thiruvananthapuram, India", "tithi": "Krishna Chaturdashi",
         "tithi_hi": "कृष्ण पक्ष चतुर्दशी", "nakshatra": "Uttara Bhadrapada",
         "nakshatra_hi": "उत्तर भाद्रपद", "festival": "Pradosh Vrat (Krishna)",
         "festival_hi": "प्रदोष व्रत (कृष्ण)"}
UPCOMING = {"festival_id": "navratri_start_shaiva", "festival": "Navratri (Start)",
            "festival_hi": "नवरात्रि (आरंभ)",
            "location": "Ujjain, India", "upcoming": True, "days_away": 5}
HINDI_NAMES = {
    "Festival": "पर्व",
    "Navratri (Start)": "नवरात्रि (आरंभ)", "Durga Puja": "दुर्गा पूजा",
    "Durga Maha Ashtami": "दुर्गा महा अष्टमी", "Durga Maha Navami": "दुर्गा महा नवमी",
    "Durga Visarjan": "दुर्गा विसर्जन", "Masik Shivratri": "मासिक शिवरात्रि",
    "Pradosh Vrat (Krishna)": "प्रदोष व्रत (कृष्ण)", "Pradosh Vrat (Shukla)": "प्रदोष व्रत (शुक्ल)",
    "Indira Ekadashi": "इन्दिरा एकादशी", "Papankusha Ekadashi": "पापांकुशा एकादशी",
    "Rama Ekadashi": "रमा एकादशी", "Saraswati Puja": "सरस्वती पूजा", "Diwali": "दीपावली",
    "Holi": "होली", "Hanuman Jayanti": "हनुमान जयंती", "Janmashtami": "जन्माष्टमी",
    "Krishna Janmashtami": "कृष्ण जन्माष्टमी", "Janmastmi": "जन्माष्टमी",
    "Sankashti Chaturthi": "संकष्टी चतुर्थी"}


def names_by_scene():
    """Exercise each scene with short copy; the neutral scene gets an unmapped name."""
    scenes = {mock_art.GENERIC_FESTIVAL_ART: ["Sankashti Chaturthi"]}
    for art in mock_art.FESTIVAL_ART.values():
        if "Festival" not in scenes.setdefault(art, []):
            scenes[art].append("Festival")
    return scenes


def inputs():
    return (json.loads((FIXTURES / "data-2026-10-06.json").read_text(encoding="utf-8")),
            json.loads((FIXTURES / "muhu-2026-10-06.json").read_text(encoding="utf-8")))


def today_spec():
    return select(*adapt_siddhanta(*inputs(), OCT_6))


def upcoming_spec():
    return PostSpec("festival", "2026-10-11", UPCOMING)


class FestivalCardTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))

    def plan(self, spec, language="en", art=None):
        art = art or mock_art.festival_art(spec.facts.get("festival_id"))
        return card.plan(self.draw, spec.to_dict()["facts"], date.fromisoformat(spec.date), art,
                         language)

    def roles(self, items):
        return {i.role: i for i in items}

    def test_every_value_is_the_exact_source_fact(self):
        spec = today_spec()
        self.assertEqual(spec.kind, "festival")
        en, hi = (self.roles(self.plan(spec, lang)) for lang in ("en", "hi"))
        self.assertEqual(en["name:0"].value, "Indira Ekadashi")
        self.assertEqual(en["value:tithi"].value, "Krishna Ekadashi")
        self.assertEqual(en["value:nakshatra"].value, "Ashlesha")
        self.assertEqual(en["date"].value, "6 October 2026")
        self.assertEqual(en["place"].value, "Tuesday · Ujjain")
        self.assertEqual(hi["name:0"].value, "इन्दिरा एकादशी")
        self.assertEqual(hi["value:tithi"].value, "कृष्ण पक्ष एकादशी")
        self.assertEqual(hi["value:nakshatra"].value, "आश्लेषा")
        self.assertEqual(hi["date"].value, "6 अक्टूबर 2026")
        self.assertEqual(hi["place"].value, "मंगलवार · उज्जैन")
        self.assertEqual(hi["label:festival"].value, "आज का पर्व")

    def test_parana_window_on_the_fast_day_is_never_shown(self):
        daily, _ = inputs()
        self.assertEqual(daily["today"]["festivals_today"][0]["ritual_label"], "Parana Time")
        spec = today_spec()
        self.assertFalse({k for k in spec.facts if "ritual" in k or "parana" in k})
        for language in ("en", "hi"):
            text = " ".join(i.value for i in self.plan(spec, language) if i.value)
            for forbidden in ("Parana", "पारण", "6:20 AM", "8:41 AM"):
                self.assertNotIn(forbidden, text)

    def test_upcoming_shows_countdown_not_the_input_days_panchang(self):
        roles = self.roles(self.plan(upcoming_spec()))
        self.assertEqual((roles["label:festival"].value, roles["name:0"].value,
                          roles["countdown"].value),
                         ("UPCOMING FESTIVAL", "Navratri Begins", "In 5 days"))
        self.assertEqual(roles["button"].value, "Check Festival & Muhurat")
        self.assertEqual((roles["date"].value, roles["place"].value),
                         ("11 October 2026", "Sunday · Ujjain"))
        self.assertNotIn("value:tithi", roles)
        for days, en, hi in ((0, "Today", "आज"), (1, "Tomorrow", "कल"), (6, "In 6 days", "6 दिन बाद")):
            self.assertEqual(card._countdown(card.COPY["en"], days), en)
            self.assertEqual(card._countdown(card.COPY["hi"], days), hi)

    def test_every_mapped_scene_has_a_panel(self):
        arts = (set(mock_art.FESTIVAL_ART.values()) | set(mock_art.DEITY_ART.values())
            | {mock_art.GENERIC_FESTIVAL_ART})
        self.assertEqual(arts, set(card.SCENE_PANELS))

    def test_geometry_with_every_real_name_on_its_scene(self):
        widest = {"en": "2026-09-30", "hi": "2026-10-20"}
        for art, names in names_by_scene().items():
            left, top, right, lowest = card.SCENE_PANELS[art]
            for name in names:
                for extra in ({}, {"upcoming": True, "days_away": 6}):
                    facts = {**WORST, **extra, "festival": name,
                            "festival_hi": HINDI_NAMES.get(name, name), "location": "Ujjain, India"}
                    for language in ("en", "hi"):
                        with self.subTest(name=name, language=language, upcoming=bool(extra)):
                            items = self.plan(PostSpec("festival", widest[language], facts),
                                              language, art)
                            panel = items[0].box
                            self.assertEqual(panel[:3], (left, top, right))
                            self.assertLessEqual(panel[3], lowest)
                            for item in items[1:]:
                                box = item.box
                                self.assertTrue(left + card.PAD <= box[0]
                                                and box[2] <= right - card.PAD
                                                and top < box[1] and box[3] < panel[3],
                                                item.role)
                            for a, b in combinations(items[1:], 2):
                                self.assertFalse(overlaps(a.box, b.box),
                                                 f"{a.role} overlaps {b.role}")

    def test_vishnu_uses_one_band_above_the_serpent_hoods(self):
        spec = today_spec()
        roles = self.roles(self.plan(spec, art=mock_art.DEITY_ART["vishnu.webp"]))
        panel = roles["panel"].box
        self.assertLessEqual(panel[3], 416)
        self.assertEqual(roles["value:tithi"].origin[1], roles["value:nakshatra"].origin[1])
        self.assertLess(roles["value:tithi"].box[2], roles["value:nakshatra"].box[0])
        self.assertLess(roles["button"].box[3], roles["name:0"].box[1])

    def test_overflow_moves_to_the_neutral_scene_instead_of_covering_the_deity(self):
        facts = {**WORST, "location": "Ujjain, India", "festival_id": "shivratri_monthly",
             "festival": "Masik Shivratri",
                 "festival_hi": HINDI_NAMES["Masik Shivratri"]}
        spec = PostSpec("festival", "2026-10-11", facts)
        art = mock_art.festival_art("shivratri_monthly")
        cramped = {**card.SCENE_PANELS, art: card.SCENE_PANELS[art][:3] + (600,)}
        with patch.dict(card.SCENE_PANELS, cramped):
            with self.assertRaises(card.PanelOverflow):
                self.plan(spec, "en")
            fallback = mock_art.render(spec, "en")
        expected = card.render_festival(spec, mock_art.GENERIC_FESTIVAL_ART, "en")
        self.assertIsNone(ImageChops.difference(fallback, expected).getbbox())

    def test_contrast_fonts_and_glyph_coverage(self):
        fonts = (mock_art.ROOT / "fonts").resolve()
        for art, names in names_by_scene().items():
            scene = ImageOps.fit(mock_art._open(art), (1080, 1350))
            facts = {**WORST, "location": "Ujjain, India", "festival": names[0],
                     "festival_hi": HINDI_NAMES.get(names[0], names[0])}
            for language in ("en", "hi"):
                items = self.plan(PostSpec("festival", "2026-10-11", facts), language, art)
                background = kit.draw_items(scene.copy(), items[:1])
                for item in items:
                    if item.kind != "text":
                        continue
                    self.assertTrue(Path(item.font.path).resolve().is_relative_to(fonts))
                    if language == "hi":
                        self.assertTrue(item.font.covers(item.value), item.value)
                    fg = luminance(ImageColor.getrgb(item.fill))
                    bg = luminance(ImageStat.Stat(background.crop(item.box)).mean)
                    ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
                    self.assertGreaterEqual(ratio, 4.5, f"{art} {language} {item.role}")

    def test_name_too_long_for_two_lines_is_refused(self):
        spec = PostSpec("festival", "2026-10-11", {**WORST, "festival": " ".join(["Mahashivratri"] * 6)})
        with self.assertRaises(ValueError):
            self.plan(spec, "en", mock_art.GENERIC_FESTIVAL_ART)

    def test_pipeline_writes_a_hindi_file(self):
        with tempfile.TemporaryDirectory() as folder:
            result = PromoStudio(folder).generate(*inputs(), expected_date=OCT_6, language="hi")
            self.assertEqual(result["post_type"], "festival")
            self.assertEqual(Path(result["path"]).name, "2026-10-06_festival_hi_1080x1350.png")
            self.assertEqual(result["caption_input"]["facts"]["festival_hi"], "इन्दिरा एकादशी")

    def test_renders_match_approved_golden_images(self):
        for name, spec in (("2026-10-06", today_spec()), ("2026-10-11-upcoming", upcoming_spec())):
            for language in ("en", "hi"):
                with self.subTest(name=name, language=language):
                    image = mock_art.render(spec, language)
                    path = GOLDEN / f"festival-{name}{'' if language == 'en' else '-hi'}.png"
                    if not path.is_file():
                        continue
                    with Image.open(path) as golden:
                        diff = ImageChops.difference(image.convert("RGB"), golden.convert("RGB"))
                    self.assertLessEqual(max(ImageStat.Stat(diff).mean), 1.0)


if __name__ == "__main__":
    unittest.main()
