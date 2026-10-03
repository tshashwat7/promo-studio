"""Secrets: environment first, then OS keyring; falls back to a .env file on save."""
from __future__ import annotations

import os

from promo_studio.config.settings import app_home

SERVICE = "promo_studio"


def get_secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        import keyring

        return keyring.get_password(SERVICE, name)
    except Exception:
        return None


def set_secret(name: str, value: str) -> str:
    """Store a secret. Returns where it went: 'keyring' or '.env'."""
    os.environ[name] = value
    try:
        import keyring

        keyring.set_password(SERVICE, name, value)
        return "keyring"
    except Exception:
        pass
    env_file = app_home() / ".env"
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{name}=")]
    lines.append(f"{name}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ".env"


def mask(value: str | None) -> str:
    if not value:
        return "(not set)"
    return "*" * max(len(value) - 4, 0) + value[-4:]
