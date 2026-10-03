"""Turns a profile + angle into validated, per-platform draft variants."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from promo_studio.ai.base import AIError, AIProvider, RateLimitError
from promo_studio.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from promo_studio.core.validators import DEFAULT_CAPS, PLATFORMS, char_count, normalize_hashtags, validate_post


class DraftError(Exception):
    """Drafting failed; the message is safe to show to the user."""


@dataclass
class DraftResult:
    variants: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_json(text: str) -> dict:
    """Parse model output, tolerating markdown fences and stray text around the JSON."""
    cleaned = re.sub(r"```(?:json)?", "", text or "").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    data = json.loads(cleaned[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON is not an object")
    return data


class DraftService:
    def __init__(self, provider: AIProvider, limiter=None, hashtag_caps: dict | None = None,
                 retries: int = 3, sleep=time.sleep):
        self.provider, self.limiter = provider, limiter
        self.caps = {**DEFAULT_CAPS, **(hashtag_caps or {})}
        self.retries, self._sleep = retries, sleep

    # ---- public ---------------------------------------------------------
    def generate(self, profile, angle: str, base_text: str = "", note: str = "",
                 n: int = 3, platforms=PLATFORMS) -> DraftResult:
        platforms = tuple(platforms)
        user = build_user_prompt(profile, angle, base_text, note, n, platforms)
        data = None
        for attempt in range(2):  # one repair attempt for invalid JSON
            prompt = user if attempt == 0 else user + "\n\nYour last reply was not valid JSON. Return valid JSON only."
            raw = self._call(SYSTEM_PROMPT, prompt)
            try:
                data = parse_json(raw)
                break
            except ValueError:
                continue
        if data is None:
            raise DraftError("The AI did not return valid JSON twice. Try again or switch provider.")
        variants = self._clean(data, profile, angle, platforms)
        if not variants:
            raise DraftError("The AI reply had no usable variants. Try again.")
        result = DraftResult(variants=variants)
        if len(variants) < n:
            result.warnings.append(f"Asked for {n} variants, got {len(variants)}.")
        return result

    def shorten(self, platform: str, text: str, max_chars: int) -> str:
        """Ask the AI to rewrite `text` so it fits `max_chars`; verified in code before returning."""
        system = ("You shorten marketing copy. Keep the meaning, tone and any links. Never add claims "
                  'or facts. Return ONLY JSON: {"text": "..."}')
        user = f"Platform: {platform}. Rewrite to at most {max_chars} characters (hard limit).\n\nTEXT:\n{text}"
        for attempt in range(2):
            prompt = user if attempt == 0 else (
                user + f"\n\nYour last reply was invalid or longer than {max_chars} characters. Make it shorter.")
            try:
                candidate = str(parse_json(self._call(system, prompt)).get("text", "")).strip()
            except ValueError:
                continue
            if candidate and char_count(platform, candidate) <= max_chars:
                return candidate
        raise DraftError("Could not shorten it enough. Trim it by hand.")

    # ---- internals ------------------------------------------------------
    def _call(self, system: str, user: str) -> str:
        for attempt in range(self.retries):
            if self.limiter:
                self.limiter.acquire()
            try:
                return self.provider.generate(system, user)
            except RateLimitError:
                if attempt == self.retries - 1:
                    raise DraftError("AI rate limit reached. Wait a minute or switch to Ollama in Settings.")
                self._sleep(2 ** attempt)
            except AIError as exc:
                raise DraftError(f"AI provider error: {exc}") from exc
        raise DraftError("AI call failed.")

    def _clean(self, data: dict, profile, angle: str, platforms) -> list[dict]:
        cleaned = []
        for raw in data.get("variants") or []:
            if not isinstance(raw, dict):
                continue
            variant: dict = {"angle": str(raw.get("angle") or angle)}
            for platform in platforms:
                block = raw.get(platform)
                if not isinstance(block, dict):
                    continue
                variant[platform] = self._clean_platform(platform, block, profile)
            if any(p in variant for p in platforms):
                cleaned.append(variant)
        return cleaned

    def _clean_platform(self, platform: str, block: dict, profile) -> dict:
        tags = normalize_hashtags(block.get("hashtags"), self.caps.get(platform, 0))
        if platform == "reddit":
            title = str(block.get("title") or "").strip()
            text = str(block.get("body") or block.get("text") or "").strip()
            subs = [str(s).strip().removeprefix("r/") for s in block.get("suggested_subreddits") or []]
            item = {"title": title, "text": text, "hashtags": [], "subreddits": subs}
        else:
            text = str(block.get("caption") or block.get("text") or "").strip()
            item = {"text": text, "hashtags": tags}
            title = None
        item["problems"] = validate_post(
            platform, text, item["hashtags"], title=title, banned=profile.banned_phrases)
        return item
