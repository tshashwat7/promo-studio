from __future__ import annotations

from abc import ABC, abstractmethod


class AIError(Exception):
    """Any failure talking to an AI provider."""


class RateLimitError(AIError):
    """Quota or rate limit reached: worth retrying after a wait."""


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, system: str, user: str, temperature: float = 0.8) -> str:
        """Return the model's raw text (expected to be JSON)."""

    def health_check(self) -> bool:
        try:
            return bool(self.generate("Reply with the JSON {\"ok\": true} only.", "ping", 0))
        except AIError:
            return False
