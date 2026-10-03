"""Builds AI providers and services from stored settings (used by the UI)."""
from __future__ import annotations

import datetime as dt

from promo_studio.adapters.facebook import FacebookAdapter
from promo_studio.adapters.instagram import InstagramAdapter
from promo_studio.ai.base import AIError, AIProvider
from promo_studio.ai.gemini import GeminiProvider
from promo_studio.ai.ollama import OllamaProvider
from promo_studio.config.secrets import get_secret
from promo_studio.config.settings import Settings
from promo_studio.core.draft_service import DraftService
from promo_studio.core.image_host import ImageHost, ImgBBHost
from promo_studio.core.image_service import ImageService
from promo_studio.core.limiter import RateLimiter
from promo_studio.core.publisher import Publisher


class AppContext:
    def __init__(self, db):
        self.db = db
        self.settings = Settings(db)
        self._limiter: RateLimiter | None = None
        self._limiter_cpm = 0

    def make_provider(self) -> AIProvider:
        s = self.settings
        provider = s.get("ai.provider")
        if provider == "ollama":
            return OllamaProvider(s.get("ai.ollama_model"), s.get("ai.ollama_url"))
        if provider == "gemini":
            return GeminiProvider(get_secret("GEMINI_API_KEY") or "", s.get("ai.model"))
        raise AIError(f"Unknown AI provider: {provider}")

    def _get_limiter(self) -> RateLimiter:
        cpm = self.settings.get_int("ai.calls_per_minute", 10)
        if self._limiter is None or cpm != self._limiter_cpm:
            self._limiter, self._limiter_cpm = RateLimiter(cpm), cpm
        return self._limiter

    def make_draft_service(self) -> DraftService:
        return DraftService(self.make_provider(), self._get_limiter(), self.settings.hashtag_caps())

    # ---- publishing ------------------------------------------------------
    def make_image_service(self) -> ImageService:
        return ImageService()

    def make_image_host(self) -> ImageHost | None:
        key = get_secret("IMAGE_HOST_KEY")
        return ImgBBHost(key) if key else None

    def make_adapters(self) -> dict:
        s, version, adapters = self.settings, self.settings.get("meta.api_version"), {}
        ig_id, ig_token = s.get("ig.user_id").strip(), get_secret("IG_ACCESS_TOKEN")
        if ig_id and ig_token:
            adapters["instagram"] = InstagramAdapter(ig_id, ig_token, version)
        page_id, page_token = s.get("fb.page_id").strip(), get_secret("FB_PAGE_TOKEN")
        if page_id and page_token:
            adapters["facebook"] = FacebookAdapter(page_id, page_token, version)
        return adapters

    def make_publisher(self) -> Publisher:
        s = self.settings
        return Publisher(self.db, self.make_adapters(), self.make_image_service(), self.make_image_host(),
                         max_parallel=s.get_int("post.max_parallel", 4), retries=s.get_int("post.retries", 2))

    def token_warning(self) -> str | None:
        """A friendly warning when the Instagram token is close to expiring."""
        raw = self.settings.get("ig.token_expires")
        try:
            days = (dt.date.fromisoformat(raw) - dt.date.today()).days
        except ValueError:
            return None
        if days < 0:
            return "Your Instagram token has expired. Refresh or regenerate it in Settings."
        return f"Your Instagram token expires in {days} day(s). Refresh it in Settings." if days <= 7 else None
