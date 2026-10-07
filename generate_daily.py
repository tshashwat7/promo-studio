"""Generate exactly one validated Siddhanta image and a JSON-safe caption contract."""
import argparse
import json
from datetime import date
from pathlib import Path

from promo_studio import DataError, PromoStudio


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data.json"))
    parser.add_argument("--muhurta", type=Path, default=Path("muhu.json"))
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--date", type=date.fromisoformat, help="Explicit archive date YYYY-MM-DD")
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--language", choices=("en", "hi"), default="en",
                        help="Card language; Hindi is available for Panchang, Muhurta and Transit")
    parser.add_argument("--card", choices=("auto", "panchang", "muhurta", "transit"),
                        default="auto", help="Override the weekday rotation for this date")
    args = parser.parse_args()
    try:
        daily = json.loads(args.data.read_text(encoding="utf-8"))
        muhurta = json.loads(args.muhurta.read_text(encoding="utf-8"))
        result = PromoStudio(args.out).generate(daily, muhurta, expected_date=args.date,
                                                 language=args.language,
                                                 card=None if args.card == "auto" else args.card,
                                                 overwrite=not args.no_overwrite)
    except (OSError, ValueError, DataError) as exc:
        parser.exit(1, f"REFUSING TO GENERATE: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
