"""Small parsing helpers for form fields."""
from __future__ import annotations


def parse_csv(text: str) -> list[str]:
    return [p.strip() for p in (text or "").replace("\n", ",").split(",") if p.strip()]


def parse_lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def parse_links(text: str) -> dict[str, str]:
    """'ios=https://...' per line -> {'ios': 'https://...'}."""
    links = {}
    for line in parse_lines(text):
        key, sep, value = line.partition("=")
        if sep and key.strip() and value.strip():
            links[key.strip()] = value.strip()
    return links


def format_links(links: dict[str, str]) -> str:
    return "\n".join(f"{k}={v}" for k, v in (links or {}).items())
