from __future__ import annotations

import os

import requests

from promo_studio.adapters.base import PlatformAdapter, PostPayload, PostResult
from promo_studio.adapters.graph import GraphError, call
from promo_studio.core.validators import validate_post


class FacebookAdapter(PlatformAdapter):
    """Posts to a Facebook Page (personal profiles are not supported by the API)."""

    name = "facebook"
    HOST = "https://graph.facebook.com"

    def __init__(self, page_id: str, token: str, version: str = "v25.0", http=requests):
        self.page_id, self.token, self.version, self.http = page_id, token, version, http

    def _url(self, path: str) -> str:
        return f"{self.HOST}/{self.version}/{path}"

    def validate(self, payload: PostPayload) -> list[str]:
        problems = validate_post("facebook", payload.text)
        if payload.image_path and not os.path.exists(payload.image_path):
            problems.append("Image file not found.")
        return problems

    def check_auth(self) -> bool:
        try:
            body = call(self.http, "GET", self._url(self.page_id),
                        params={"fields": "name", "access_token": self.token})
            self.last_account, self.last_error = body.get("name") or self.page_id, None
            return True
        except GraphError as exc:
            self.last_account, self.last_error = None, exc.message
            return False

    def post(self, payload: PostPayload) -> PostResult:
        try:
            if payload.image_path:
                with open(payload.image_path, "rb") as fh:
                    body = call(self.http, "POST", self._url(f"{self.page_id}/photos"),
                                data={"message": payload.text, "published": "true", "access_token": self.token},
                                files={"source": fh}, timeout=90)
            else:
                data = {"message": payload.text, "access_token": self.token}
                if payload.link:
                    data["link"] = payload.link
                body = call(self.http, "POST", self._url(f"{self.page_id}/feed"), data=data)
        except GraphError as exc:
            return exc.to_result(self.name)
        except OSError:
            return PostResult(self.name, False, error_code="VALIDATION", error_message="Could not read the image file.")
        post_id = str(body.get("post_id") or body.get("id") or "")
        if not post_id:
            return PostResult(self.name, False, error_code="UNKNOWN", error_message="Facebook returned no post id.",
                              needs_check=True)
        return PostResult(self.name, True, post_id=post_id, url=f"https://www.facebook.com/{post_id}")
