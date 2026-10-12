"""Text-first daily layouts over explicitly named local artwork; no network or JSON paths."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .models import PostSpec

ROOT = Path(__file__).resolve().parent.parent / "assets"
TEMPLATES = {
    "panchang": "templates/active/Serene Ghat Mandala at Dusk.webp",
    "muhurta": "templates/active/plan_day_template.webp",
    "transit": "templates/active/transit_template.webp",
    "chakra": "templates/active/Panchang Temple Riverside Template.webp",
    "kundli": "templates/active/Panchang Temple Riverside Template.webp",
}
FESTIVAL_ART = {
    # Stable Siddhanta event IDs avoid duplicate keys for localized/name variants.
    "navratri_start_shaiva": "content/festivals/navratri_festival.webp",
    "durga_puja": "content/festivals/navratri_festival.webp",
    "durga_ashtami": "content/festivals/navratri_festival.webp",
    "durga_navami": "content/festivals/navratri_festival.webp",
    "durga_visarjan": "content/festivals/navratri_festival.webp",
    "shivratri_monthly": "content/festivals/Shivratri Festive Diptych.webp",
    "maha_shivratri": "content/festivals/Shiva Beneath the Himalayan Moon.png",
    "pradosh_krishna": "content/festivals/Shiva Beneath the Himalayan Moon.png",
    "pradosh_shukla": "content/festivals/Shiva Beneath the Himalayan Moon.png",
    "shattila_ekadashi": "content/festivals/Lord Vishnu by the Lotus Lake.webp",
    "jaya_ekadashi": "content/festivals/Serene Vishnu on Sheshnag at Sunrise.webp",
    "vijaya_ekadashi": "content/festivals/Lord Vishnu at Sunrise by the Lotus Lake.webp",
    "amalaki_ekadashi": "content/festivals/Vishnu by the Lotus Lake at Dawn.webp",
    "papmochani_ekadashi": "content/festivals/Divine Dawn by the Sacred River.webp",
    "kamada_ekadashi": "content/festivals/Krishna and Radha by the Sacred Sunrise.webp",
    "varuthini_ekadashi": "content/festivals/Lord Vishnu by the Lotus Lake.webp",
    "mohini_ekadashi": "content/festivals/Serene Vishnu on Sheshnag at Sunrise.webp",
    "apara_ekadashi": "content/festivals/Lord Vishnu at Sunrise by the Lotus Lake.webp",
    "padmini_ekadashi": "content/festivals/Divine Dawn by the Sacred River.webp",
    "param_ekadashi": "content/festivals/Krishna and Radha by the Sacred Sunrise.webp",
    "nirjala_ekadashi": "content/festivals/Vishnu by the Lotus Lake at Dawn.webp",
    "yogini_ekadashi": "content/festivals/Divine Dawn by the Sacred River.webp",
    "devshayani_ekadashi": "content/festivals/Krishna and Radha by the Sacred Sunrise.webp",
    "kamika_ekadashi": "content/festivals/Lord Vishnu by the Lotus Lake.webp",
    "putrada_ekadashi": "content/festivals/Serene Vishnu on Sheshnag at Sunrise.webp",
    "aja_ekadashi": "content/festivals/Lord Vishnu at Sunrise by the Lotus Lake.webp",
    "parsva_ekadashi": "content/festivals/Vishnu by the Lotus Lake at Dawn.webp",
    "indira_ekadashi": "content/festivals/Serene Vishnu on Sheshnag at Sunrise.webp",
    "papankusha_ekadashi": "content/festivals/Lord Vishnu at Sunrise by the Lotus Lake.webp",
    "rama_ekadashi": "content/festivals/Vishnu by the Lotus Lake at Dawn.webp",
    "devutthana_ekadashi": "content/festivals/Divine Dawn by the Sacred River.webp",
    "utpanna_ekadashi": "content/festivals/Krishna and Radha by the Sacred Sunrise.webp",
    "mokshada_ekadashi": "content/festivals/Lord Vishnu by the Lotus Lake.webp",
    "vaikuntha_ekadashi": "content/festivals/Vishnu by the Lotus Lake at Dawn.webp",
    "basant_panchami": "content/festivals/saraswati_festival.webp",
    "diwali": "content/festivals/Diwali Ghat Glow Template.webp",
    "holi": "content/festivals/Holi Festive Diptych.webp",
    "rangwali_holi": "content/festivals/Holi Festive Diptych.webp",
    "hanuman_jayanti_v": "content/festivals/Hanuman Over Golden Temple Valley.webp",
    "janmashtami": "content/festivals/Moonlit Krishna by the Yamuna.webp",
}
# Rule-engine deity and festival image mapping (from Siddhanta rule catalog)
DEITY_ART = {
    "shiva.webp": "content/festivals/Shivratri Festive Diptych.webp",
    "shivratri.webp": "content/festivals/Shivratri Festive Diptych.webp",
    "masik shivratri.webp": "content/festivals/Shivratri Festive Diptych.webp",
    "vishnu.webp": "content/festivals/Vishnu on Shesha Beneath a Cosmic Sky.webp",
    "durga.webp": "content/festivals/navratri_festival.webp",
    "navratri.webp": "content/festivals/navratri_festival.webp",
    "krishna.webp": "content/festivals/Moonlit Krishna by the Yamuna.webp",
    "hanuman.webp": "content/festivals/Hanuman Over Golden Temple Valley.webp",
    "saraswati.webp": "content/festivals/saraswati_festival.webp",
    "lakshmi.webp": "content/festivals/Diwali Ghat Glow Template.webp",
    "diwali.webp": "content/festivals/Diwali Ghat Glow Template.webp",
    "holi.webp": "content/festivals/Holi Festive Diptych.webp",
    "holikadahan.webp": "content/festivals/Holi Festive Diptych.webp",
}
GENERIC_FESTIVAL_ART = "content/festivals/Generic festival.webp"
# Cards built on card_kit: bilingual, with the header medallion instead of a footer logo.
CARD_KIT_KINDS = ("panchang", "muhurta", "transit", "kundli", "festival", "chakra")
LOGO = "branding/logo.webp"
W, H = 1080, 1350


def _resolve_path(rel_path: str) -> Path:
    target = (ROOT / rel_path).resolve()
    if target.is_file():
        return target
    for ext in (".webp", ".png"):
        alt = target.with_suffix(ext)
        if alt.is_file():
            return alt
    flat = (ROOT / Path(rel_path).name).resolve()
    if flat.is_file():
        return flat
    for ext in (".webp", ".png"):
        flat_alt = flat.with_suffix(ext)
        if flat_alt.is_file():
            return flat_alt
    return target


def _open(name: str) -> Image.Image:
    path = _resolve_path(name)
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("local artwork must stay inside the assets directory")
    if path.stat().st_size > 15_000_000:
        raise ValueError("local artwork exceeds 15 MB")
    with Image.open(path) as source:
        if source.width * source.height > 40_000_000:
            raise ValueError("local artwork exceeds 40 million pixels")
        return source.convert("RGB")


def _canvas(kind: str) -> Image.Image:
    return ImageOps.fit(_open(TEMPLATES[kind]), (W, H), method=Image.Resampling.LANCZOS)


def _promo_canvas() -> Image.Image:
    """Muted temple scenery provides depth without overpowering the promo."""
    scene = _canvas("kundli")
    return Image.blend(scene, Image.new("RGB", (W, H), "#FAEDD9"), .79)


def brand(image: Image.Image, kind: str | None = None) -> Image.Image:
    """Use the top Panchang mark or the footer mark on other cards."""
    if kind in CARD_KIT_KINDS:
        return image
    if not _resolve_path(LOGO).is_file():
        return image
    logo = ImageOps.fit(_open(LOGO), (62, 62), method=Image.Resampling.LANCZOS)
    image.paste(logo, (930, 1238))
    return image


def _panchang(spec: PostSpec, image: Image.Image, language: str = "en") -> Image.Image:
    from .panchang_card import render_panchang

    return render_panchang(spec, image, language)


def festival_art(festival_id: str | None, image_file: str | None = None) -> str | None:
    """Resolve by Siddhanta event ID, then approved deity alias, else neutral local artwork."""
    art = FESTIVAL_ART.get(festival_id) if festival_id else None
    if art is None and image_file:
        art = DEITY_ART.get(Path(image_file).name.lower())
    if art is None:
        art = GENERIC_FESTIVAL_ART

    if (ROOT / art).is_file():
        return art
    if (ROOT / Path(art).name).is_file():
        return art
    if (ROOT / GENERIC_FESTIVAL_ART).is_file():
        return GENERIC_FESTIVAL_ART
    if (ROOT / Path(GENERIC_FESTIVAL_ART).name).is_file():
        return GENERIC_FESTIVAL_ART
    return None


def render(spec: PostSpec, language: str = "en") -> Image.Image | None:
    """Return None when a curated image is missing, letting the legacy renderer work."""
    kind = spec.kind
    if language not in ("en", "hi"):
        raise ValueError(f"No {language!r} layout; choose en or hi")
    if kind == "festival":
        from .festival_card import PanelOverflow, render_festival

        img_obj = spec.facts.get("festival_image")
        img_file = img_obj.get("file_name") if isinstance(img_obj, dict) else (img_obj if isinstance(img_obj, str) else None)
        art = festival_art(spec.facts.get("festival_id"), img_file)
        if art is None:
            return None
        try:
            return render_festival(spec, art, language)
        except PanelOverflow:
            # Never cover the deity: long copy moves to the neutral scene's taller panel.
            generic_resolved = (ROOT / GENERIC_FESTIVAL_ART).is_file() or (ROOT / Path(GENERIC_FESTIVAL_ART).name).is_file()
            if art == GENERIC_FESTIVAL_ART or not generic_resolved:
                raise
            return render_festival(spec, GENERIC_FESTIVAL_ART, language)
    if kind not in TEMPLATES or not _resolve_path(TEMPLATES[kind]).is_file():
        return None
    if kind == "chakra":
        from .chakra_card import render_chakra

        return render_chakra(_promo_canvas(), language)

    if kind == "kundli":
        from .kundli_card import render_kundli

        return render_kundli(_promo_canvas(), language)

    image = _canvas(kind)
    if kind == "panchang":
        return _panchang(spec, image, language)
    if kind == "muhurta":
        from .muhurta_card import render_muhurta

        return render_muhurta(spec, image, language)
    from .transit_card import render_transit

    return render_transit(spec, image, language)[0]


def slides(spec: PostSpec, language: str = "en") -> list[Image.Image] | None:
    """Every image of the post in order: one for most cards, a carousel for transit."""
    if spec.kind == "transit" and _resolve_path(TEMPLATES["transit"]).is_file():
        from .transit_card import render_transit

        return render_transit(spec, _canvas("transit"), language)
    image = render(spec, language)
    return None if image is None else [image]
