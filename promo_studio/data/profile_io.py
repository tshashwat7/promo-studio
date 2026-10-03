"""Export and import app profiles as JSON (merge by name)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from promo_studio.data.models import AppProfile

VERSION = 1


def export_profiles(db, path) -> int:
    profiles = []
    for p in db.list_profiles():
        item = asdict(p)
        item.pop("id")
        profiles.append(item)
    Path(path).write_text(json.dumps({"version": VERSION, "profiles": profiles}, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    return len(profiles)


def _strs(value) -> list[str]:
    return [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []


def _profile_from_dict(item: dict) -> AppProfile:
    name = str(item.get("name", "")).strip()
    if not name:
        raise ValueError("a profile in the file has no name")
    links = item.get("store_links")
    return AppProfile(
        name=name, pitch=str(item.get("pitch", "")), description=str(item.get("description", "")),
        audience=str(item.get("audience", "")), features=_strs(item.get("features")),
        tone=str(item.get("tone", "")),
        store_links={str(k): str(v) for k, v in links.items()} if isinstance(links, dict) else {},
        seed_keywords=_strs(item.get("seed_keywords")), banned_phrases=_strs(item.get("banned_phrases")),
        default_hashtags=_strs(item.get("default_hashtags")),
        default_image_path=str(item.get("default_image_path", "")))


def import_profiles(db, path) -> tuple[int, int]:
    """Returns (created, updated). Raises ValueError with a friendly message for bad files."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not read the file as JSON ({exc}).") from exc
    items = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError("This file does not look like a Promo Studio profile export.")
    existing = {p.name.lower(): p for p in db.list_profiles()}
    parsed = [_profile_from_dict(i) for i in items if isinstance(i, dict)]  # validate all before writing
    created = updated = 0
    for profile in parsed:
        match = existing.get(profile.name.lower())
        if match:
            profile.id = match.id
            updated += 1
        else:
            created += 1
        db.save_profile(profile)
    return created, updated
