"""Daily Reel stills: factual labels, shaped glyphs, safe areas, atomic previews."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree
from pathlib import Path

from PIL import Image, ImageColor

from promo_studio.models import DataError
from promo_studio.reel_planner import plan_reels
from promo_studio.reels.preview import write_preview
from promo_studio.reels.scenes import (BACKGROUND, CONTENT, DURATIONS, GOLD, HEIGHT, MUTED,
                                      SAFE, WHITE, WIDTH, _vector_background, render_daily)
from test_daily import ROOT, TODAY, inputs


def plan():
    return plan_reels(*inputs(), expected_date=TODAY)


class ReelSceneTests(unittest.TestCase):
    def test_original_vector_is_self_contained_and_video_safe(self):
        source = ROOT / "assets" / BACKGROUND
        tree = ElementTree.parse(source)
        self.assertEqual(tree.getroot().get("viewBox"), "0 0 1080 1920")
        self.assertFalse([node for node in tree.iter()
                          if node.tag.split("}")[-1] in {"image", "text", "script", "foreignObject"}])
        self.assertFalse([value for node in tree.iter() for key, value in node.attrib.items()
                          if key.split("}")[-1] == "href"])
        background = _vector_background()
        self.assertEqual(background.size, (WIDTH, HEIGHT))
        self.assertEqual(background.mode, "RGB")
        # Two-panel samples remain opaque and readable with all three text colours.
        def luminance(rgb):
            channels = [part / 255 for part in rgb[:3]]
            linear = [part / 12.92 if part <= .04045 else ((part + .055) / 1.055) ** 2.4
                      for part in channels]
            return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))

        for xy in ((CONTENT[0] + 180, CONTENT[1] + 240),
                   (CONTENT[2] - 180, CONTENT[3] - 160)):
            panel = luminance(background.getpixel(xy))
            for ink in (GOLD, WHITE, MUTED):
                ratio = (luminance(ImageColor.getrgb(ink)) + .05) / (panel + .05)
                self.assertGreaterEqual(ratio, 4.5, (xy, ink, ratio))

    def test_bilingual_storyboard_is_9_by_16_and_text_safe(self):
        for spec in plan()["deliverables"]:
            with self.subTest(language=spec["language"]):
                scenes = render_daily(spec)
                self.assertEqual([scene.duration for scene in scenes], list(DURATIONS))
                self.assertEqual(sum(scene.duration for scene in scenes), 23)
                self.assertTrue(all(scene.image.size == (WIDTH, HEIGHT) for scene in scenes))
                lines = [text for scene in scenes for text, _ in scene.text_boxes]
                facts = spec["facts"]
                for value in (facts[f"tithi_{spec['language']}"],
                              facts[f"nakshatra_{spec['language']}"],
                              facts["sunrise"], facts["sunset"],
                              facts["rahu_kaal"]["start"],
                              facts["auspicious_window"]["start"], spec["location"]):
                    self.assertTrue(any(value in line for line in lines), value)
                self.assertTrue(any("6 Oct" in text or "6 अक्टूबर" in text for text in lines))
                for scene in scenes:
                    boxes = scene.text_boxes
                    for _, (x0, y0, x1, y1) in boxes:
                        self.assertGreaterEqual(x0, SAFE[0])
                        self.assertGreaterEqual(y0, SAFE[1])
                        self.assertLessEqual(x1, SAFE[2])
                        self.assertLessEqual(y1, SAFE[3])
                    for index, (_, box) in enumerate(boxes):
                        for _, other in boxes[index + 1:]:
                            overlap = (min(box[2], other[2]) - max(box[0], other[0]) > 0 and
                                       min(box[3], other[3]) - max(box[1], other[1]) > 0)
                            self.assertFalse(overlap, (box, other))

    def test_overlong_values_fail_instead_of_truncating(self):
        spec = copy.deepcopy(plan()["deliverables"][1])
        spec["facts"]["nakshatra_hi"] = "अत्यंतलंबानक्षत्र" * 45
        with self.assertRaises(DataError):
            render_daily(spec)
        spec = copy.deepcopy(plan()["deliverables"][0])
        spec["location"] = "Unreasonably Long Location " * 24
        with self.assertRaises(DataError):
            render_daily(spec)

    def test_heading_never_assumes_the_source_city(self):
        spec = copy.deepcopy(plan()["deliverables"][0])
        spec["location"] = "Delhi, India"
        lines = [text for scene in render_daily(spec) for text, _ in scene.text_boxes]
        self.assertIn("Delhi, India", lines)
        self.assertFalse(any("UJJAIN" in text for text in lines))

    def test_missing_devanagari_glyph_refused(self):
        spec = copy.deepcopy(plan()["deliverables"][1])
        spec["facts"]["tithi_hi"] = "तिथि 😀"
        with self.assertRaisesRegex(DataError, "lacks glyphs"):
            render_daily(spec)

    def test_preview_is_complete_traceable_and_not_publishable(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "Review folder with spaces"
            result = write_preview(plan(), output)
            target = Path(result["path"])
            saved = json.loads((target / "preview.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "preview_only")
            self.assertFalse(saved["publication_ready"])
            self.assertEqual(saved["review_state"], "not_reviewed")
            self.assertEqual(len(saved["artifacts"]), 14)
            self.assertEqual(sorted(target.glob("*.png")),
                             sorted(target / item["file"] for item in saved["artifacts"]))
            for item in saved["artifacts"]:
                path = target / item["file"]
                self.assertEqual(item["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                with Image.open(path) as image:
                    self.assertEqual(image.size, (1080, 384) if "contact_sheet" in path.name
                                     else (WIDTH, HEIGHT))
            with self.assertRaises(DataError):
                write_preview(plan(), output)
            self.assertFalse(list(output.glob(".reel-preview-*")))

    def test_failed_language_render_leaves_no_partial_date(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "previews"
            broken = plan()
            broken["deliverables"][1]["facts"] = {**broken["deliverables"][1]["facts"],
                                                        "nakshatra_hi": "ह" * 300}
            with self.assertRaises(DataError):
                write_preview(broken, output)
            self.assertFalse(output.exists())

    def test_cli_preview_accepts_windows_style_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "review assets"
            command = [sys.executable, str(ROOT / "generate_reels.py"), "--preview",
                       "--kind", "daily", "--language", "hi", "--date", TODAY.isoformat(),
                       "--data", str(ROOT / "tests/fixtures/data-2026-10-05.json"),
                       "--muhurta", str(ROOT / "tests/fixtures/muhu-2026-10-05.json"),
                       "--out", str(output)]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                    encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "preview_only")
            self.assertEqual(len(list((output / TODAY.isoformat()).glob("*.png"))), 7)


if __name__ == "__main__":
    unittest.main()
