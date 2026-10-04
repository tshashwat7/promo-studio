"""Allowlisted local festival artwork resolver.

Upstream file names/URLs are never trusted. Add approved local files under
assets/festivals/ or configure SIDDHANTA_FESTIVAL_ASSET_DIR.
"""
from __future__ import annotations
import os
from pathlib import Path

ALLOWLIST = {
    "Indira Ekadashi": "vishnu.webp",
    "Papankusha Ekadashi": "vishnu.webp",
    "Masik Shivratri": "masik_shivratri.webp",
    "Pradosh Vrat (Krishna)": "pradosh_krishna.webp",
    "Pradosh Vrat (Shukla)": "pradosh_shukla.webp",
    "Ashwin Amavasya": "amavasya.webp",
    "Navratri (Start)": "navratri.webp",
    "Durga Puja": "durga_puja.webp",
    "Durga Maha Ashtami": "durga.webp",
    "Durga Maha Navami": "durga.webp",
    "Vijay dashami": "vijayadashmi.webp",
    "Durga Visarjan": "durga.webp",
    "Sharad Purnima": "sharad_purnima.webp",
    "Karwa Chauth": "karwa_chauth.webp",
    "Ahoi Ashtami": "ahoi_ashtami.webp",
}


def resolve(name: str):
    filename = ALLOWLIST.get(name)
    if not filename:
        return None
    root = Path(os.environ.get("SIDDHANTA_FESTIVAL_ASSET_DIR", Path(__file__).parent / "assets" / "festivals"))
    path = (root / filename).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None
