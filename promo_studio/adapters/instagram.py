from __future__ import annotations

import time

import requests

from promo_studio.adapters.base import PlatformAdapter, PostPayload, PostResult
from promo_studio.adapters.graph import GraphError, call
from promo_studio.core.validators import validate_post


class InstagramAdapter(PlatformAdapter):
    """Instagram API with Instagram Login (no Facebook Page needed). Business/Creator accounts only.

    Flow: create a media container from a public image URL, wait until it is FINISHED, publish it.
    """

    name = "instagram"
    needs_public_image = True
    HOST = "https://graph.instagram.com"

    def __init__(self, ig_user_id: str, token: str, version: str = "v25.0", http=requests,
                 sleep=time.sleep, poll_attempts: int = 5, poll_interval: float = 3.0):
        self.ig_user_id, self.token, self.version, self.http = ig_user_id, token, version, http
        self._sleep, self.poll_attempts, self.poll_interval = sleep, poll_attempts, poll_interval

    def _url(self, path: str) -> str:
        return f"{self.HOST}/{self.version}/{path}"

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def validate(self, payload: PostPayload) -> list[str]:
        return validate_post("instagram", payload.text, has_image=bool(payload.image_path or payload.image_url))

    def check_auth(self) -> bool:
        try:
            body = call(self.http, "GET", self._url(self.ig_user_id), headers=self._headers,
                        params={"fields": "username"})
            name = body.get("username")
            self.last_account, self.last_error = f"@{name}" if name else self.ig_user_id, None
            return True
        except GraphError as exc:
            self.last_account, self.last_error = None, exc.message
            return False

    def refresh_token(self) -> tuple[str, int]:
        """Extend a long-lived token (about 60 days). Returns (new_token, seconds_valid)."""
        body = call(self.http, "GET", f"{self.HOST}/refresh_access_token",
                    params={"grant_type": "ig_refresh_token", "access_token": self.token})
        return str(body["access_token"]), int(body.get("expires_in", 0))

    def post(self, payload: PostPayload) -> PostResult:
        if not payload.image_url:
            return PostResult(self.name, False, error_code="VALIDATION",
                              error_message="The image must be uploaded to a public URL first.")
        try:
            container = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"), headers=self._headers,
                             json={"image_url": payload.image_url, "caption": payload.text})["id"]
        except GraphError as exc:
            return exc.to_result(self.name)
        except KeyError:
            return PostResult(self.name, False, error_code="UNKNOWN", error_message="Instagram returned no container id.")

        not_ready = self._wait_until_ready(container)
        if not_ready:
            return not_ready
        try:
            media_id = call(self.http, "POST", self._url(f"{self.ig_user_id}/media_publish"),
                            headers=self._headers, json={"creation_id": container})["id"]
        except GraphError as exc:
            if exc.retryable:  # the request may have reached Instagram: never auto-retry a publish
                return PostResult(self.name, False, error_code=exc.error_code, needs_check=True,
                                  error_message="Could not confirm whether Instagram published it. "
                                                "Check the profile before posting again.")
            return exc.to_result(self.name)
        except KeyError:
            return PostResult(self.name, False, error_code="UNKNOWN", needs_check=True,
                              error_message="Instagram gave no media id. Check the profile before posting again.")
        return PostResult(self.name, True, post_id=str(media_id), url=self._permalink(str(media_id)))

    def _wait_until_ready(self, container: str) -> PostResult | None:
        for attempt in range(self.poll_attempts):
            try:
                status = call(self.http, "GET", self._url(container), headers=self._headers,
                              params={"fields": "status_code"}).get("status_code")
            except GraphError:
                return None  # cannot read the status: try publishing anyway
            if status == "FINISHED":
                return None
            if status in ("ERROR", "EXPIRED"):
                return PostResult(self.name, False, error_code="PLATFORM",
                                  error_message=f"Instagram could not process the image ({status}). Check that the "
                                                "image URL is reachable and the file is a JPEG.")
            if attempt < self.poll_attempts - 1:
                self._sleep(self.poll_interval)
        return PostResult(self.name, False, error_code="PLATFORM", retryable=True,
                          error_message="Instagram is still processing the image.")

    def _permalink(self, media_id: str) -> str:
        try:
            body = call(self.http, "GET", self._url(media_id), headers=self._headers, params={"fields": "permalink"})
            return body.get("permalink") or "https://www.instagram.com/"
        except GraphError:
            return "https://www.instagram.com/"
