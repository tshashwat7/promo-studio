from __future__ import annotations

import json
from dataclasses import dataclass, field


def _loads(value, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


@dataclass
class AppProfile:
    name: str
    id: int | None = None
    pitch: str = ""
    description: str = ""
    audience: str = ""
    features: list[str] = field(default_factory=list)
    tone: str = ""
    store_links: dict[str, str] = field(default_factory=dict)
    seed_keywords: list[str] = field(default_factory=list)
    banned_phrases: list[str] = field(default_factory=list)
    default_hashtags: list[str] = field(default_factory=list)
    default_image_path: str = ""

    @classmethod
    def from_row(cls, row) -> "AppProfile":
        return cls(
            id=row["id"], name=row["name"], pitch=row["pitch"], description=row["description"],
            audience=row["audience"], features=_loads(row["features"], []), tone=row["tone"],
            store_links=_loads(row["store_links"], {}), seed_keywords=_loads(row["seed_keywords"], []),
            banned_phrases=_loads(row["banned_phrases"], []),
            default_hashtags=_loads(row["default_hashtags"], []),
            default_image_path=row["default_image_path"],
        )


@dataclass
class Target:
    id: int
    post_id: int
    platform: str
    text: str
    hashtags: list[str]
    title: str | None
    extra: dict
    status: str
    attempts: int
    scheduled_at: str | None = None

    @classmethod
    def from_row(cls, row) -> "Target":
        return cls(id=row["id"], post_id=row["post_id"], platform=row["platform"], text=row["text"] or "",
                   hashtags=_loads(row["hashtags"], []), title=row["title"], extra=_loads(row["extra"], {}),
                   status=row["status"], attempts=row["attempts"], scheduled_at=row["scheduled_at"])
