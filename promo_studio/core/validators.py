"""Code-side checks. The AI suggests; these functions decide what is valid."""
from __future__ import annotations

import re

PLATFORMS = ("facebook", "instagram", "x", "reddit")

# Working defaults from the wiki: verify against each platform's current rules.
LIMITS = {"x": 280, "instagram": 2200, "facebook": 63206, "reddit": 40000}
REDDIT_TITLE_LIMIT = 300
INSTAGRAM_MAX_HASHTAGS = 30
X_URL_LENGTH = 23  # X counts every link as a fixed length
DEFAULT_CAPS = {"x": 2, "instagram": 5, "facebook": 3, "reddit": 0}

_URL_RE = re.compile(r"https?://\S+")


def normalize_hashtags(tags, cap: int) -> list[str]:
    """Strip '#', spaces and symbols, lowercase, de-duplicate (order kept), cap the count."""
    if cap <= 0:
        return []
    out: list[str] = []
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        clean = re.sub(r"[^\w]", "", tag.lstrip("#").replace(" ", "")).lower()
        if clean and clean not in out:
            out.append(clean)
    return out[:cap]


def compose_text(platform: str, text: str, hashtags) -> str:
    """The text as it will be published: body plus hashtags."""
    body = (text or "").strip()
    tags = " ".join(f"#{t}" for t in hashtags or [])
    if not tags:
        return body
    return f"{body}{' ' if platform == 'x' else chr(10) * 2}{tags}"


def char_count(platform: str, text: str, hashtags=()) -> int:
    full = compose_text(platform, text, hashtags)
    if platform == "x":
        full = _URL_RE.sub("x" * X_URL_LENGTH, full)
    return len(full)


def limit_for(platform: str) -> int:
    return LIMITS[platform]


def counter_state(used: int, limit: int) -> str:
    """'ok', 'warn' (>= 90% of the limit) or 'over'."""
    if used > limit:
        return "over"
    return "warn" if used >= 0.9 * limit else "ok"


def find_banned(text: str, phrases) -> list[str]:
    lower = (text or "").lower()
    return [p for p in phrases or [] if p.strip() and p.strip().lower() in lower]


def validate_post(platform: str, text: str, hashtags=(), *, title: str | None = None,
                  banned=(), has_image: bool | None = None) -> list[str]:
    """Return human-readable problems; an empty list means the post is valid.

    has_image=None means "unknown" and skips image rules.
    """
    problems: list[str] = []
    if not (text or "").strip():
        problems.append("Text is empty.")
    used, limit = char_count(platform, text, hashtags), LIMITS[platform]
    if used > limit:
        problems.append(f"Over the limit by {used - limit} characters ({used}/{limit}).")
    if platform == "instagram":
        if has_image is False:
            problems.append("Instagram needs an image.")
        if len(list(hashtags or [])) > INSTAGRAM_MAX_HASHTAGS:
            problems.append(f"More than {INSTAGRAM_MAX_HASHTAGS} hashtags.")
    if platform == "reddit":
        if not (title or "").strip():
            problems.append("Reddit needs a title.")
        elif len(title) > REDDIT_TITLE_LIMIT:
            problems.append(f"Title is over {REDDIT_TITLE_LIMIT} characters.")
    combined = f"{title or ''} {compose_text(platform, text, hashtags)}"
    for phrase in find_banned(combined, banned):
        problems.append(f'Contains banned phrase: "{phrase}".')
    return problems
