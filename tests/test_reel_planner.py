"""Planning-only Reel contracts; no media or approval can be produced here."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from promo_studio.models import DataError
from promo_studio.reel_planner import plan_reels
from test_daily import ROOT, TODAY, inputs, on_day


class ReelPlannerTests(unittest.TestCase):
    def test_same_facts_for_both_languages_without_mutating_source(self):
        daily, muhu = inputs()
        original = copy.deepcopy((daily, muhu))
        plan = plan_reels(daily, muhu, expected_date=TODAY)
        self.assertEqual(plan["status"], "planning_only")
        self.assertEqual([(d["kind"], d["language"]) for d in plan["deliverables"]],
                         [("daily", "en"), ("daily", "hi")])
        en, hi = plan["deliverables"]
        self.assertEqual(en["facts"], hi["facts"])
        self.assertEqual(en["facts"]["tithi_end_date"], "2026-10-06")
        # The fixture's Abhijit timing fails the adapter's solar-noon check.
        self.assertEqual(en["facts"]["auspicious_window"]["source"], "choghadiya")
        self.assertFalse(en["facts"]["rahu_kaal"]["is_auspicious"])
        self.assertEqual(en["timezone"], "Asia/Kolkata")
        self.assertEqual(en["media_status"], "not_rendered")
        self.assertEqual((daily, muhu), original)

    def test_day_rotation_is_independent_of_image_card_selector(self):
        for number, optional in ((6, None), (7, "chakra"), (8, None),
                                 (9, "transit"), (10, "kundli")):
            with self.subTest(day=number):
                daily, muhu = inputs()
                target = date(2026, 10, number)
                on_day(daily, muhu, target)
                plan = plan_reels(daily, muhu, expected_date=target, language="en")
                self.assertEqual([d["kind"] for d in plan["deliverables"]], ["daily"])
                self.assertEqual([h["kind"] for h in plan["held"]],
                                 [optional] if optional else [])

    def test_only_explicit_today_festivals_with_multiple_review_warning(self):
        daily, muhu = inputs()
        daily["upcoming_festivals"] = [{"name_en": "Not Today"}]
        with self.assertRaises(DataError):
            plan_reels(daily, muhu, expected_date=TODAY, kind="festival")
        daily["today"]["festivals_today"] = [
            {"name_en": "Observance One", "name_hi": "पर्व एक"},
            {"name_en": "Observance Two", "name_hi": "पर्व दो"}]
        plan = plan_reels(daily, muhu, expected_date=TODAY)
        self.assertEqual(len(plan["deliverables"]), 6)
        self.assertEqual(plan["deliverables"][2]["facts"]["festival_en"], "Observance One")
        self.assertTrue(any(h["kind"] == "festival" for h in plan["held"]))

    def test_rejects_stale_exports_and_missing_or_bad_windows(self):
        for change in (lambda d, m: m.update(date="2026-10-04"),
                       lambda d, m: d["today"]["english"].pop("sunrise"),
                       lambda d, m: m["muhurtas"].pop("rahu_kaal"),
                       lambda d, m: m["metadata"]["location"].update(timezone="UTC"),
                       lambda d, m: m["muhurtas"]["rahu_kaal"].update(is_auspicious=True)):
            with self.subTest(change=change):
                daily, muhu = inputs()
                change(daily, muhu)
                with self.assertRaises(DataError):
                    plan_reels(daily, muhu, expected_date=TODAY)

    def test_auspicious_fallback_requires_validated_choghadiya(self):
        daily, muhu = inputs()
        muhu["muhurtas"]["abhijit_muhurta"].update(start="11:51 AM", end="12:39 PM")
        plan = plan_reels(daily, muhu, expected_date=TODAY, language="en")
        self.assertEqual(plan["deliverables"][0]["facts"]["auspicious_window"]["source"],
                         "abhijit_muhurta")
        muhu["muhurtas"].pop("abhijit_muhurta")
        plan = plan_reels(daily, muhu, expected_date=TODAY, language="en")
        self.assertEqual(plan["deliverables"][0]["facts"]["auspicious_window"]["source"],
                         "choghadiya")
        muhu["choghadiya"]["day"][0]["name_en"] = "Rog"
        with self.assertRaises(DataError):
            plan_reels(daily, muhu, expected_date=TODAY)

    def test_transit_requires_ingress_on_requested_date(self):
        daily, muhu = inputs()
        target = date(2026, 10, 9)
        on_day(daily, muhu, target)
        with self.assertRaises(DataError):
            plan_reels(daily, muhu, expected_date=target, kind="transit")
        daily["transits"]["major_transits"]["mars"]["ingress_date"] = target.isoformat()
        plan = plan_reels(daily, muhu, expected_date=target, kind="transit", language="en")
        self.assertEqual(plan["deliverables"][0]["facts"]["ingress"], target.isoformat())
        self.assertEqual([d["kind"] for d in plan["deliverables"]], ["transit"])

    def test_unreviewed_explainers_are_held(self):
        daily, muhu = inputs()
        on_day(daily, muhu, date(2026, 10, 7))
        with self.assertRaisesRegex(DataError, "reviewed bilingual script"):
            plan_reels(daily, muhu, expected_date=date(2026, 10, 7), kind="chakra")

    def test_cli_requires_dry_run_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            command = [sys.executable, str(ROOT / "generate_reels.py"), "--data",
                       str(ROOT / "tests/fixtures/data-2026-10-05.json"), "--muhurta",
                       str(ROOT / "tests/fixtures/muhu-2026-10-05.json"), "--date",
                       TODAY.isoformat()]
            refused = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                     encoding="utf-8")
            self.assertNotEqual(refused.returncode, 0)
            success = subprocess.run(command + ["--dry-run"], cwd=root,
                                     capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertEqual(json.loads(success.stdout)["status"], "planning_only")
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
