from __future__ import annotations

import requests

from promo_studio.ai.base import AIError, AIProvider


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 180):
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout

    def generate(self, system: str, user: str, temperature: float = 0.8) -> str:
        payload = {
            "model": self.model, "stream": False, "format": "json",
            "options": {"temperature": temperature},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "")
        except requests.RequestException as exc:
            raise AIError(f"Ollama request failed: {exc}") from exc
