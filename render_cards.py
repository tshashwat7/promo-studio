"""One-click runner to generate the refined Siddhanta 6-Card Universe.

Executes all 6 card renderers with the approved brand refinements:
- Standardized header, typography, and bottom CTA
- Distinct cream-first atmospheres (no repetitive ghat scenes)
- Authentic North Indian D1 Lagna Kundli chart
- Sized & positioned Durga on lion and meditating Yogi
- Factual Jupiter Transit in Gemini with matching II Roman badge
"""
import datetime as dt
from pathlib import Path
from promo_studio.automation.panchang_engine import calculate_daily_panchang
from promo_studio.automation.card_universe import (
    render_card_1_panchang,
    render_card_2_plan_day,
    render_card_3_festival,
    render_card_4_kundli,
    render_card_5_chakra,
    render_card_6_jyotish,
)

def main():
    p = calculate_daily_panchang(dt.date(2026, 10, 4))
    
    # 1. Output to project directory
    out_dir = Path("output/refined_cards")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Output to agent artifact directory for instant viewing
    art_dir = Path(r"C:\Users\91962\.gemini\antigravity\brain\7b3a37ce-f1fd-479c-8121-d7b871608cd2")
    
    targets = [
        ("1_daily_panchang.png", render_card_1_panchang, (p,)),
        ("2_plan_your_day.png", render_card_2_plan_day, (p,)),
        ("3_festival.png", render_card_3_festival, (p,)),
        ("4_kundli.png", render_card_4_kundli, (p,)),
        ("5_chakra.png", render_card_5_chakra, (p,)),
        ("6_jyotish_insight.png", render_card_6_jyotish, (p,)),
    ]
    
    print("🎨 Rendering Refined Siddhanta 6-Card Universe...")
    for filename, fn, extra_args in targets:
        local_path = out_dir / filename
        fn(*extra_args, output_path=local_path)
        print(f"  ✓ Rendered {local_path}")
        
        if art_dir.exists():
            art_path = art_dir / filename
            fn(*extra_args, output_path=art_path)
            print(f"  ✓ Updated artifact: {art_path}")

    print("\n✨ All 6 cards generated successfully with brand consistency rules!")

if __name__ == "__main__":
    main()
