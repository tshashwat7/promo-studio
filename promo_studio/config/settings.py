"""App home folder, default settings and typed access to stored settings."""
from __future__ import annotations

import os
from pathlib import Path


def app_home() -> Path:
    override = os.environ.get("PROMO_STUDIO_HOME")
    if override:
        home = Path(override)
    elif os.name == "nt":
        home = Path(os.environ.get("APPDATA", str(Path.home()))) / "PromoStudio"
    else:
        home = Path.home() / ".promo_studio"
    home.mkdir(parents=True, exist_ok=True)
    return home


def load_env() -> None:
    """Load .env files if python-dotenv is installed (app home first, then cwd)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(app_home() / ".env")
    load_dotenv()


# Model names change often: keep them in settings, never hard-coded in logic.
DEFAULTS: dict[str, str] = {
    "ai.provider": "gemini",
    "ai.model": "gemini-2.5-flash",
    "ai.ollama_model": "llama3.1:8b",
    "ai.ollama_url": "http://localhost:11434",
    "ai.variants": "3",
    "ai.calls_per_minute": "10",
    "hashtags.max.x": "2",
    "hashtags.max.instagram": "5",
    "hashtags.max.facebook": "3",
    "hashtags.max.reddit": "0",
    "theme": "system",
    "meta.api_version": "v25.0",
    "post.max_parallel": "4",
    "post.retries": "2",
    "ig.user_id": "siddhanta.app",
    "fb.page_id": "",
    "ig.token_expires": "",
}


class Settings:
    """Thin wrapper over the settings table with defaults."""

    def __init__(self, db):
        self.db = db

    def get(self, key: str) -> str:
        value = self.db.get_setting(key)
        return value if value is not None else DEFAULTS.get(key, "")

    def get_int(self, key: str, fallback: int = 0) -> int:
        try:
            return int(self.get(key))
        except (TypeError, ValueError):
            return fallback

    def set(self, key: str, value: str) -> None:
        self.db.set_setting(key, str(value))

    def hashtag_caps(self) -> dict[str, int]:
        return {p: self.get_int(f"hashtags.max.{p}") for p in ("x", "instagram", "facebook", "reddit")}
