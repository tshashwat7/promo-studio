import argparse, json, sys
from promo_studio import PromoStudio, DataError

ap = argparse.ArgumentParser(); ap.add_argument("payload"); ap.add_argument("--out", default="output")
ap.add_argument("--no-overwrite", action="store_true"); a = ap.parse_args()
try:
    with open(a.payload, encoding="utf-8") as f: payload = json.load(f)
    print(json.dumps(PromoStudio(a.out).generate(payload, overwrite=not a.no_overwrite), ensure_ascii=False, indent=2))
except json.JSONDecodeError as e: sys.exit(f"malformed JSON: {e}")
except DataError as e:            sys.exit(f"REFUSING TO POST - bad upstream data: {e}")   # exit code != 0 stops the scheduler
