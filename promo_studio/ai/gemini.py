from __future__ import annotations

from promo_studio.ai.base import AIError, AIProvider, RateLimitError


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise AIError("Gemini API key is missing. Add it in Settings.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIError("Package 'google-genai' is not installed (pip install google-genai).") from exc
        self._types = types
        self._client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, system: str, user: str, temperature: float = 0.8) -> str:
        config = self._types.GenerateContentConfig(
            system_instruction=system, temperature=temperature,
            response_mime_type="application/json")
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=user, config=config)
        except Exception as exc:  # SDK raises several exception types
            text = str(exc)
            if "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
                raise RateLimitError(text) from exc
            raise AIError(text) from exc
        return response.text or ""
