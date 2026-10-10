"""Organize assets into their canonical subdirectories per docs/panchang-design-guide.md.

Copies assets from both local folders and from the panchang_master_app repository:
    D:\\AI My Projects\\Production\\panchang_master_app\\assets

Run from repository root:
    python organize_assets.py
"""
import shutil
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent
LOCAL_ASSETS = REPO_ROOT / "assets"
EXTERNAL_ASSETS = Path(r"D:\AI My Projects\Production\panchang_master_app\assets")

TEMPLATES = [
    "Serene Ghat Mandala at Dusk.webp",
    "plan_day_template.webp",
    "transit_template.webp",
    "Panchang Temple Riverside Template.webp",
]

FESTIVAL_SCENES = [
    "navratri_festival.webp",
    "Shivratri Festive Diptych.webp",
    "Vishnu on Shesha Beneath a Cosmic Sky.webp",
    "saraswati_festival.webp",
    "Diwali Ghat Glow Template.webp",
    "Holi Festive Diptych.webp",
    "Hanuman Over Golden Temple Valley.webp",
    "Moonlit Krishna by the Yamuna.webp",
    "Generic festival.webp",
]

PLANETS = [
    "sun.webp", "moon.webp", "mars.webp", "mercury.webp",
    "jupiter.webp", "venus.webp", "saturn.webp", "rahu.webp", "ketu.webp"
]

ZODIAC = [
    "mesh.webp", "vrishbha.webp", "mithuna.webp", "karka.webp",
    "simha.webp", "kanya.webp", "tula.webp", "vrischika.webp",
    "dhanu.webp", "makar.webp", "kumbha.webp", "pisces.webp"
]

PROCEDURAL_FESTIVALS = [
    "navratri.webp", "vishnu.webp", "Kartik Purnima.webp",
    "Ganesh Chaturthi.webp", "Karwa Chauth.webp", "Rama Ekadashi.webp",
    "Ahoi Ashtami.webp"
]


def organize() -> None:
    print("=" * 60)
    print("Siddhanta Promo Studio - Asset Organizer")
    print("=" * 60)

    # 1. Templates -> assets/templates/active/
    active_dir = LOCAL_ASSETS / "templates" / "active"
    active_dir.mkdir(parents=True, exist_ok=True)
    for name in TEMPLATES:
        src = LOCAL_ASSETS / name
        dst = active_dir / name
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)
            print(f"[COPIED] Template: {name} -> templates/active/{name}")
        elif dst.is_file():
            print(f"[READY]  Template: templates/active/{name}")

    # 2. Festival Scenes -> assets/content/festivals/
    festivals_dir = LOCAL_ASSETS / "content" / "festivals"
    festivals_dir.mkdir(parents=True, exist_ok=True)
    for name in FESTIVAL_SCENES:
        src = LOCAL_ASSETS / name
        dst = festivals_dir / name
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)
            print(f"[COPIED] Festival scene: {name} -> content/festivals/{name}")
        elif dst.is_file():
            print(f"[READY]  Festival scene: content/festivals/{name}")

    # 3. Planets -> assets/icons/planets/
    planets_dir = LOCAL_ASSETS / "icons" / "planets"
    planets_dir.mkdir(parents=True, exist_ok=True)
    ext_planets = EXTERNAL_ASSETS / "illustrations" / "planets"
    for name in PLANETS:
        dst = planets_dir / name
        if not dst.is_file():
            src = ext_planets / name
            if src.is_file():
                shutil.copy2(src, dst)
                print(f"[COPIED] Planet: {name} -> icons/planets/{name}")
            else:
                print(f"[MISSING] Planet: {name}")
        else:
            print(f"[READY]  Planet: icons/planets/{name}")

    # 4. Zodiac Medallions -> assets/icons/festivals/
    zodiac_dir = LOCAL_ASSETS / "icons" / "festivals"
    zodiac_dir.mkdir(parents=True, exist_ok=True)
    ext_zodiac = EXTERNAL_ASSETS / "illustrations" / "festivals"
    for name in ZODIAC:
        dst = zodiac_dir / name
        if not dst.is_file():
            src = ext_zodiac / name
            if src.is_file():
                shutil.copy2(src, dst)
                print(f"[COPIED] Zodiac: {name} -> icons/festivals/{name}")
            else:
                print(f"[MISSING] Zodiac: {name}")
        else:
            print(f"[READY]  Zodiac: icons/festivals/{name}")

    # 5. Procedural Festival Fallbacks -> assets/illustrations/festivals/
    proc_dir = LOCAL_ASSETS / "illustrations" / "festivals"
    proc_dir.mkdir(parents=True, exist_ok=True)
    for name in PROCEDURAL_FESTIVALS:
        dst = proc_dir / name
        if not dst.is_file():
            src = ext_zodiac / name
            if src.is_file():
                shutil.copy2(src, dst)
                print(f"[COPIED] Procedural art: {name} -> illustrations/festivals/{name}")
        else:
            print(f"[READY]  Procedural art: illustrations/festivals/{name}")

    # 6. Fonts -> assets/fonts/
    fonts_dir = LOCAL_ASSETS / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    ext_fonts = EXTERNAL_ASSETS / "fonts"
    if ext_fonts.is_dir():
        for ttf in ext_fonts.glob("*.ttf"):
            dst = fonts_dir / ttf.name
            if not dst.is_file():
                shutil.copy2(ttf, dst)
                print(f"[COPIED] Font: {ttf.name} -> fonts/{ttf.name}")
            else:
                print(f"[READY]  Font: fonts/{ttf.name}")

    # 7. Branding Logo -> assets/branding/logo.webp
    branding_dir = LOCAL_ASSETS / "branding"
    branding_dir.mkdir(parents=True, exist_ok=True)
    logo_webp = branding_dir / "logo.webp"
    if not logo_webp.is_file():
        src_candidates = [
            EXTERNAL_ASSETS / "logo.png",
            LOCAL_ASSETS / "logo.webp",
            REPO_ROOT / "promo_studio" / "assets" / "logo.png",
        ]
        found = False
        for src in src_candidates:
            if src.is_file():
                if src.suffix.lower() == ".webp":
                    shutil.copy2(src, logo_webp)
                else:
                    with Image.open(src) as img:
                        img.save(logo_webp, "WEBP", quality=95)
                print(f"[CREATED] branding/logo.webp from {src.name}")
                found = True
                break
        if not found:
            print("[MISSING] Logo source")
    else:
        print("[READY]  branding/logo.webp")

    # 8. Generate Capricorn and Aquarius medallions if needed
    try:
        from graphics import generate_zodiac_medallions
        generate_zodiac_medallions.main()
        print("[GENERATED] Capricorn and Aquarius SVG & WebP medallions")
    except Exception as exc:
        print(f"[NOTICE] Zodiac generator: {exc}")

    print("=" * 60)
    print("Asset organization finished successfully!")
    print("=" * 60)


if __name__ == "__main__":
    organize()
