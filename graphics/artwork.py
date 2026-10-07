"""Load curated local transparent artwork; never fetch arbitrary JSON URLs."""

from pathlib import Path

from PIL import Image


def festival_artwork(record: dict, root: Path, max_size: tuple[int, int]) -> Image.Image | None:
    name = record.get("image", {}).get("local_asset_path", "")
    if not isinstance(name, str) or not name:
        return None
    path = (root / name).resolve()
    if not path.is_relative_to((root / "assets").resolve()):
        return None
    if path.suffix.lower() not in {".png", ".webp"} or not path.is_file():
        return None
    with Image.open(path) as source:
        art = source.convert("RGBA")
    art.thumbnail(max_size, Image.Resampling.LANCZOS)
    return art
