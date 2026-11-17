from __future__ import annotations

import logging
import os
from pathlib import Path
import requests
from requests_oauthlib import OAuth1Session

from promo_studio.adapters.base import PlatformAdapter, PostPayload, PostResult

log = logging.getLogger(__name__)


class TwitterAdapter(PlatformAdapter):
    """Publishes tweets and media cards to X (Twitter) using OAuth 1.0a User Context."""

    name = "twitter"
    UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
    TWEET_URL = "https://api.twitter.com/2/tweets"
    VERIFY_URL = "https://api.twitter.com/1.1/account/verify_credentials.json"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        screen_name: str | None = None,
    ):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.access_token = access_token.strip()
        self.access_token_secret = access_token_secret.strip()
        self.screen_name = screen_name
        self._session = OAuth1Session(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

    def validate(self, payload: PostPayload) -> list[str]:
        problems = []
        if len(payload.text) > 280:
            problems.append(f"Tweet exceeds 280 characters ({len(payload.text)} chars).")
        if payload.image_path and not Path(payload.image_path).exists():
            problems.append("Image file not found.")
        return problems

    def check_auth(self) -> bool:
        """Verifies credentials against Twitter API."""
        try:
            res = self._session.get(self.VERIFY_URL, timeout=15)
            if res.status_code == 200:
                data = res.json()
                self.screen_name = data.get("screen_name") or self.screen_name
                self.last_account = self.screen_name
                return True
            log.warning("Twitter auth verification failed (%s): %s", res.status_code, res.text)
            return False
        except Exception as e:
            log.warning("Twitter auth check error: %s", e)
            return False

    def upload_media_file(self, file_path: str | Path) -> str | None:
        """Uploads a local image file and returns Twitter media_id_string."""
        p = Path(file_path)
        if not p.exists():
            log.warning("Media file not found: %s", file_path)
            return None
        try:
            with open(p, "rb") as f:
                res = self._session.post(self.UPLOAD_URL, files={"media": f}, timeout=60)
            if res.status_code in (200, 201, 202):
                return str(res.json().get("media_id_string"))
            log.warning("Twitter media upload failed (%s): %s", res.status_code, res.text)
            return None
        except Exception as e:
            log.warning("Twitter media upload exception: %s", e)
            return None

    def upload_media_from_url(self, image_url: str) -> str | None:
        """Downloads image bytes from a public CDN URL and uploads to Twitter."""
        try:
            resp = requests.get(image_url, timeout=30)
            if resp.status_code != 200:
                log.warning("Failed to fetch image from URL: %s", image_url)
                return None
            res = self._session.post(self.UPLOAD_URL, files={"media": resp.content}, timeout=60)
            if res.status_code in (200, 201, 202):
                return str(res.json().get("media_id_string"))
            log.warning("Twitter media upload from URL failed (%s): %s", res.status_code, res.text)
            return None
        except Exception as e:
            log.warning("Twitter media upload exception for %s: %s", image_url, e)
            return None

    def publish_tweet(
        self,
        text: str,
        media_urls: list[str] | None = None,
        media_files: list[str | Path] | None = None,
    ) -> PostResult:
        """Publishes a Tweet with up to 4 image cards attached."""
        media_ids: list[str] = []

        # 1. Upload media files if provided (up to 4 images max on Twitter)
        if media_files:
            for f in media_files[:4]:
                m_id = self.upload_media_file(f)
                if m_id:
                    media_ids.append(m_id)

        # 2. Or upload from public CDN URLs (up to 4 images max on Twitter)
        elif media_urls:
            for u in media_urls[:4]:
                m_id = self.upload_media_from_url(u)
                if m_id:
                    media_ids.append(m_id)

        # 3. Construct Twitter API v2 payload
        payload: dict = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        try:
            res = self._session.post(self.TWEET_URL, json=payload, timeout=30)
            if res.status_code in (200, 201):
                tweet_data = res.json().get("data", {})
                tweet_id = str(tweet_data.get("id") or "")
                sn = self.screen_name or "i"
                tweet_url = f"https://x.com/{sn}/status/{tweet_id}"
                log.info("Tweet published successfully: %s", tweet_url)
                return PostResult(self.name, True, post_id=tweet_id, url=tweet_url)
            log.error("Failed to post tweet (%s): %s", res.status_code, res.text)
            return PostResult(self.name, False, error_code=str(res.status_code), error_message=res.text)
        except Exception as e:
            log.error("Twitter publish exception: %s", e)
            return PostResult(self.name, False, error_code="EXCEPTION", error_message=str(e))

    def post(self, payload: PostPayload) -> PostResult:
        """Base PlatformAdapter post implementation."""
        media_files = [payload.image_path] if payload.image_path else None
        text = payload.text
        if payload.link and payload.link not in text:
            text = f"{text}\n{payload.link}"
        return self.publish_tweet(text, media_files=media_files)
