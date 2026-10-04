"""Production binding example for the real Siddhanta workflow outputs."""
import json
from pathlib import Path
from promo_studio import PromoStudio

root = Path(__file__).parent
with open(root / "daily_panchang.json", encoding="utf-8") as f:
    daily = json.load(f)
with open(root / "muhurta_data.json", encoding="utf-8") as f:
    muhurta = json.load(f)

result = PromoStudio(root / "output").generate(daily, muhurta_data=muhurta)
print(result)
