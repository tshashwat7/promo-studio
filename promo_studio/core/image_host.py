"""Temporary public hosting for images (Instagram fetches the image from a public URL)."""
from __future__ import annotations

import base64
from abc import ABC, abstractmethod

import requests


class ImageHostError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ImageHost(ABC):
    @abstractmethod
    def upload(self, path: str) -> str:
        """Upload the file and return a public https URL."""


class ImgBBHost(ImageHost):
    """ImgBB free API. Uploads auto-expire, so nothing has to be deleted afterwards."""

    ENDPOINT = "https://api.imgbb.com/1/upload"

    def __init__(self, api_key: str, expiration: int = 3600, http=requests, timeout: int = 60):
        self.api_key, self.expiration, self.http, self.timeout = api_key, expiration, http, timeout

    def upload(self, path: str) -> str:
        if not self.api_key:
            raise ImageHostError("Image host API key is missing. Add it in Settings.")
        try:
            with open(path, "rb") as fh:
                encoded = base64.b64encode(fh.read()).decode("ascii")
        except OSError as exc:
            raise ImageHostError("Could not read the image file.") from exc

        import time
        last_exc = None
        for attempt in range(1, 4):
            try:
                response = self.http.request("POST", self.ENDPOINT, params={"key": self.api_key},
                                             data={"image": encoded, "expiration": self.expiration},
                                             timeout=self.timeout)
                try:
                    body = response.json()
                except ValueError:
                    body = {}
                data = body.get("data") if isinstance(body, dict) else {}
                if not isinstance(data, dict):
                    data = {}
                url = data.get("display_url") or data.get("url") or (data.get("image") or {}).get("url")
                if response.status_code == 200 and url:
                    return url
                if response.status_code >= 500 and attempt < 3:
                    time.sleep(3 * attempt)
                    continue
                if response.status_code >= 400 or not url:
                    err_msg = ""
                    if isinstance(body, dict):
                        err_obj = body.get("error")
                        if isinstance(err_obj, dict):
                            err_msg = err_obj.get("message", "")
                        elif isinstance(err_obj, str):
                            err_msg = err_obj
                    detail = f": {err_msg}" if err_msg else ""
                    raise ImageHostError(f"Image host rejected the upload (HTTP {response.status_code}){detail}.",
                                         retryable=response.status_code >= 500)
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < 3:
                    time.sleep(3 * attempt)
                    continue
                raise ImageHostError(f"Image upload failed ({type(exc).__name__}).", retryable=True) from None
        if last_exc:
            raise ImageHostError(f"Image upload failed ({type(last_exc).__name__}).", retryable=True) from None
        return ""
