from PIL import Image
from pathlib import Path

dl = Path("C:/Users/91962/Downloads")
p = dl / "Siddhanta Kundli_ Birth Chart Explored.png"
if p.exists():
    im = Image.open(p)
    # The Lagna Kundli (D1) chart on the phone screen
    # Phone screen is roughly x in [450, 915], y in [240, 1420]
    # In this phone screen, Lagna Kundli (D1) chart is between y=420 and y=800
    chart = im.crop((510, 420, 890, 800))
    chart.save("output/real_siddhanta_chart.png")
    print("Saved real_siddhanta_chart.png")
