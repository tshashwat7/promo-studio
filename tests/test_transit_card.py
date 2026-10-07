"""Today's Sky transit carousel: validated data, exact facts, layout and both languages."""
import json
import tempfile
import unittest
from datetime import date
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageStat

from promo_studio import DataError, PromoStudio, card_kit as kit, mock_art, transit_card as card
from promo_studio.adapter import GRAHAS, ZODIAC, ZODIAC_HI, adapt_siddhanta
from promo_studio.card_kit import ENGLISH, LEFT
from promo_studio.selector import select
from test_daily import TODAY as OCT_5, inputs as oct_5_inputs, on_day
from test_panchang_card import luminance, overlaps

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OCT_6 = date(2026, 10, 6)
FRIDAY = date(2026, 10, 9)
GOLDEN = {(slide, lang): ROOT / "tests" / "golden" /
          f"transit-2026-10-06-{slide}{'' if lang == 'en' else '-hi'}.png"
          for slide in (1, 2) for lang in ("en", "hi")}
CLOSING_ROLES = ("panel", "hook:", "cta:")


def inputs():
    """The fixed-engine 6 Oct export (correct Moon-sign lists)."""
    return (json.loads((FIXTURES / "data-2026-10-06.json").read_text(encoding="utf-8")),
            json.loads((FIXTURES / "muhu-2026-10-06.json").read_text(encoding="utf-8")))


def transit_spec():
    return select(*adapt_siddhanta(*inputs(), OCT_6), "transit")


def place(position: dict, total: float) -> None:
    """Move a planet while keeping its rashi fields internally consistent."""
    index = int(total // 30)
    position.update(longitude_total=total, degree_in_rashi=round(total % 30, 2), rashi_index=index,
                    rashi_en=ZODIAC[index], rashi_hi=ZODIAC_HI[index])


IMPOSSIBLE = {
    "Ketu not opposite Rahu": lambda d: place(d["transits"]["positions"]["ketu"], 130.0),
    "retrograde Sun": lambda d: d["transits"]["positions"]["sun"].update(
        is_retrograde=True, motion_en="Retrograde"),
    "rashi name contradicts index": lambda d: d["transits"]["positions"]["mars"].update(
        rashi_en="Leo"),
    "Venus too far from the Sun": lambda d: place(d["transits"]["positions"]["venus"], 230.0),
    "Sun not sidereal for the date": lambda d: place(d["transits"]["positions"]["sun"], 173.55),
    "Sun rashi contradicts Panchang": lambda d: d["today"]["english"].update(sun_rashi="Libra"),
}


class TransitCarouselTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))
        self.spec = transit_spec()
        self.facts = self.spec.to_dict()["facts"]

    def slides(self, language="en", facts=None):
        return [plan(self.draw, facts or self.facts, OCT_6, language) for plan in card.SLIDES]

    def roles(self, items):
        return {item.role: item for item in items if item.role}

    def assert_geometry(self, items):
        content = [i for i in items if i.kind in ("text", "icon", "planet", "zodiac",
                                                   "rule", "dot", "ring")
                   and not i.role.startswith(CLOSING_ROLES)]
        for item in content:
            left, top, right, bottom = item.box
            self.assertGreaterEqual(left, LEFT, item.role)
            self.assertLessEqual(right, card.right_edge(top), item.role)
            self.assertLessEqual(bottom, card.FACT_BOTTOM, item.role)
        panel = self.roles(items)["panel"].box
        self.assertGreater(panel[1], card.FACT_BOTTOM)
        self.assertLessEqual(panel[3], 1350)
        for item in items:
            if item.role.startswith(("hook:", "cta:")):
                box = item.box
                self.assertTrue(panel[0] < box[0] and box[2] < panel[2] and panel[1] < box[1]
                                and box[3] < panel[3], f"{item.role} leaves the panel")
        texts = [i for i in items if i.kind != "panel"]
        for a, b in combinations(texts, 2):
            self.assertFalse(overlaps(a.box, b.box), f"{a.role} overlaps {b.role}")

    def test_fixed_engine_data_passes_every_check(self):
        _, windows = adapt_siddhanta(*inputs(), OCT_6)
        self.assertFalse([w for w in windows["warnings"] if "transit" in w.lower()
                          or "Planet positions" in w])
        self.assertEqual((self.facts["planet"], self.facts["rashi"]), ("Mars", "Cancer"))
        self.assertEqual([r["key"] for r in self.facts["positions"]], list(GRAHAS))
        good = [r["en"] for r in self.facts["rashis"] if r["favourable"]]
        self.assertEqual(good, ["Taurus", "Virgo", "Aquarius"])  # 3rd, 11th, 6th from Cancer.

    def test_wrong_moon_sign_lists_are_omitted_with_a_warning(self):
        data, windows = adapt_siddhanta(*oct_5_inputs(), OCT_5)
        self.assertIn("Major transit mars favourable/challenging rashis disagree",
                      " ".join(windows["warnings"]))
        spec = select(data, windows, "transit")
        self.assertNotIn("rashis", spec.facts)
        story = self.roles(card.plan_story(self.draw, spec.to_dict()["facts"], OCT_5))
        self.assertNotIn("label:rashis", story)
        self.assertIn("swipe", story)

    def test_hindi_lists_must_match_the_english(self):
        daily, muhu = inputs()
        daily["transits"]["major_transits"]["mars"]["benefited_rashis_hi"][0] = "मेष"
        _, windows = adapt_siddhanta(daily, muhu, OCT_6)
        self.assertIn("Hindi names that do not match", " ".join(windows["warnings"]))

    def test_every_value_is_the_exact_source_fact(self):
        source = inputs()[0]
        positions = source["transits"]["positions"]
        for language in ("en", "hi"):
            story, table = (self.roles(s) for s in self.slides(language))
            for key in GRAHAS:
                p = positions[key]
                self.assertEqual(table[f"planet:{key}"].value, p[f"name_{language}"])
                self.assertEqual(table[f"rashi:{key}"].value, p[f"rashi_{language}"])
                self.assertEqual(table[f"degree:{key}"].value, f"{int(p['degree_in_rashi'])}°")
                retrograde = p["is_retrograde"] or key in ("rahu", "ketu")
                self.assertEqual(f"motion:{key}" in table, retrograde, key)
            for i, english in enumerate(ZODIAC):
                self.assertEqual(story[f"rashi:{english}"].value,
                                 english if language == "en" else ZODIAC_HI[i])
                self.assertEqual((story[f"art:{english}"].kind,
                                  story[f"art:{english}"].value), ("zodiac", english))
                favourable = english in source["transits"]["major_transits"]["mars"][
                    "benefited_rashis_en"]
                self.assertEqual(story[f"mark:{english}"].kind, "dot" if favourable else "ring")
        en_story, en_table = (self.roles(s) for s in self.slides())
        self.assertEqual(en_story["value:transit"].value, "Mars in Cancer")
        self.assertEqual(en_story["detail:transit"].value, "18 Sep – 12 Nov 2026")
        self.assertEqual(en_table["value:transit"].value, "Moon in Cancer")
        self.assertEqual(en_table["detail:transit"].value, "Ashlesha Nakshatra")
        hi_story, hi_table = (self.roles(s) for s in self.slides("hi"))
        self.assertEqual(hi_story["value:transit"].value, "मंगल कर्क राशि में")
        self.assertEqual(hi_story["detail:transit"].value, "18 सितम्बर – 12 नवम्बर 2026")
        self.assertEqual(hi_table["detail:transit"].value, "आश्लेषा नक्षत्र")

    def test_ingress_day_is_announced(self):
        roles = self.roles(card.plan_story(self.draw, {**self.facts, "ingress": "2026-10-06"},
                                           OCT_6))
        self.assertEqual(roles["label:transit"].value, "ENTERS TODAY")
        self.assertEqual(self.roles(self.slides()[0])["label:transit"].value, "CURRENT TRANSIT")

    def test_span_shows_both_years_only_when_they_differ(self):
        self.assertEqual(card._span(ENGLISH, date(2025, 3, 29), date(2027, 6, 2)),
                         "29 Mar 2025 – 2 Jun 2027")

    def test_planet_art_is_cut_from_its_tile(self):
        story, table = (self.roles(s) for s in self.slides())
        self.assertEqual((story["icon:transit"].kind, story["icon:transit"].value), ("planet", "mars"))
        self.assertEqual(table["icon:transit"].value, "moon")
        for key in GRAHAS:
            self.assertEqual(table[f"art:{key}"].value, key)
            art = kit.planet_image(key, card.PLANET, card.PLANET)
            self.assertEqual(art.getpixel((0, 0))[3], 0, key)
            self.assertGreater(art.getchannel("A").getextrema()[1], 200, key)

    def test_all_twelve_medallions_have_no_square_background(self):
        for name in ZODIAC:
            with self.subTest(name=name):
                art = kit.zodiac_image(name, card.ZODIAC_SIZE)
                self.assertEqual(art.size, (card.ZODIAC_SIZE,) * 2)
                self.assertEqual(art.getpixel((0, 0))[3], 0)
                self.assertGreater(art.getchannel("A").getextrema()[1], 200)

    def test_one_closing_paragraph_and_no_button(self):
        for language in ("en", "hi"):
            labels = kit.LANGUAGES[language].labels
            for items in self.slides(language):
                roles = self.roles(items)
                self.assertNotIn("button", roles)
                hook = " ".join(i.value for i in items if i.role.startswith("hook:"))
                cta = " ".join(i.value for i in items if i.role.startswith("cta:"))
                self.assertEqual(hook, labels["transit_hook"])
                self.assertEqual(cta, labels["transit_cta"])

    def test_physically_impossible_positions_are_refused(self):
        for name, mutate in IMPOSSIBLE.items():
            with self.subTest(name):
                daily, muhu = inputs()
                mutate(daily)
                data, windows = adapt_siddhanta(daily, muhu, OCT_6)
                self.assertEqual(data["transits"]["positions"], {})
                self.assertTrue(any(w.startswith("Planet positions") for w in windows["warnings"]))
                with self.assertRaises(DataError):
                    select(data, windows, "transit")

    def test_friday_falls_back_to_panchang_when_positions_fail(self):
        daily, muhu = oct_5_inputs()
        on_day(daily, muhu, FRIDAY)
        self.assertEqual(select(*adapt_siddhanta(daily, muhu, FRIDAY)).kind, "transit")
        IMPOSSIBLE["Ketu not opposite Rahu"](daily)
        self.assertEqual(select(*adapt_siddhanta(daily, muhu, FRIDAY)).kind, "panchang")

    def test_major_transit_contradicting_its_position_is_dropped(self):
        daily, muhu = inputs()
        daily["transits"]["major_transits"]["mars"]["current_rashi_en"] = "Leo"
        data, windows = adapt_siddhanta(daily, muhu, OCT_6)
        self.assertIn("Major transit mars disagrees", " ".join(windows["warnings"]))
        self.assertEqual(select(data, windows, "transit").facts["planet"], "Jupiter")

    def test_geometry_in_both_languages_and_with_a_long_city(self):
        long_city = {**self.facts, "location": "Thiruvananthapuram, India"}
        for language in ("en", "hi"):
            for facts in (self.facts, long_city):
                for number, items in enumerate(self.slides(language, facts), 1):
                    with self.subTest(language=language, slide=number):
                        self.assert_geometry(items)

    def test_contrast_fonts_and_glyph_coverage(self):
        fonts = (mock_art.ROOT / "fonts").resolve()
        for language in ("en", "hi"):
            for items in self.slides(language):
                panels = [i for i in items if i.kind == "panel"]
                background = kit.draw_items(card.wash(mock_art._canvas("transit")), panels)
                for item in items:
                    if item.kind != "text":
                        continue
                    self.assertTrue(Path(item.font.path).resolve().is_relative_to(fonts), item.role)
                    if language == "hi":
                        self.assertTrue(item.font.covers(item.value), item.value)
                    mean = ImageStat.Stat(background.crop(item.box)).mean
                    fg, bg = luminance(ImageColor.getrgb(item.fill)), luminance(mean)
                    ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
                    self.assertGreaterEqual(ratio, 4.5, f"{language} {item.role} {ratio:.2f}")

    def test_pipeline_writes_two_numbered_slides_per_language(self):
        with tempfile.TemporaryDirectory() as folder:
            for language in ("en", "hi"):
                result = PromoStudio(folder).generate(*inputs(), expected_date=OCT_6,
                                                      language=language, card="transit")
                suffix = "" if language == "en" else "_hi"
                self.assertEqual([Path(p).name for p in result["paths"]],
                                 [f"2026-10-06_transit{suffix}_{n}_1080x1350.png" for n in (1, 2)])
                self.assertEqual(result["path"], result["paths"][0])
                for path in result["paths"]:
                    with Image.open(path) as image:
                        self.assertEqual(image.size, (1080, 1350))
                self.assertTrue(PromoStudio(folder).generate(
                    *inputs(), expected_date=OCT_6, language=language, card="transit",
                    overwrite=False)["skipped"])

    def test_renders_match_approved_golden_images(self):
        for language in ("en", "hi"):
            images = mock_art.slides(self.spec, language)
            self.assertEqual(len(images), 2)
            for number, image in enumerate(images, 1):
                if not GOLDEN[number, language].is_file():
                    continue
                with self.subTest(language=language, slide=number):
                    with Image.open(GOLDEN[number, language]) as golden:
                        diff = ImageChops.difference(image.convert("RGB"), golden.convert("RGB"))
                    self.assertLessEqual(max(ImageStat.Stat(diff).mean), 1.0)


if __name__ == "__main__":
    unittest.main()
