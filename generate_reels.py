"""Plan Reels or render review-only daily PNG scenes (no MP4 or publishing)."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from promo_studio.models import DataError
from promo_studio.reel_planner import KINDS, plan_reels
from promo_studio.reels.preview import write_preview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data.json"))
    parser.add_argument("--muhurta", type=Path, default=Path("muhu.json"))
    parser.add_argument("--date", type=date.fromisoformat, help="Explicit archive date YYYY-MM-DD")
    parser.add_argument("--language", choices=("en", "hi", "both"), default="both")
    parser.add_argument("--kind", choices=KINDS, default="auto")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print plan; write nothing")
    mode.add_argument("--preview", action="store_true",
                      help="Write daily review PNG scenes, cover and contact sheets only")
    parser.add_argument("--out", type=Path, default=Path("output/reels/previews"))
    args = parser.parse_args()
    if args.preview and args.kind not in ("daily", "auto"):
        parser.error("Only the daily Reel has a preview template; choose --kind daily or auto")
    try:
        daily = json.loads(args.data.read_text(encoding="utf-8"))
        muhurta = json.loads(args.muhurta.read_text(encoding="utf-8"))
        result = plan_reels(daily, muhurta, expected_date=args.date,
                            language=args.language, kind=args.kind)
        if args.preview:
            result = write_preview(result, args.out)
    except (OSError, ValueError, DataError) as exc:
        parser.exit(1, f"REFUSING TO PLAN: {exc}\n")
    # Windows redirected stdout can default to cp1252, which cannot encode Hindi.
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
