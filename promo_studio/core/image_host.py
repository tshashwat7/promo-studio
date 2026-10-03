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
                encoded = base64.b64encode(fh.read())
        except OSError as exc:
            raise ImageHostError("Could not read the image file.") from exc
        try:
            response = self.http.request("POST", self.ENDPOINT, params={"key": self.api_key},
                                         data={"image": encoded, "expiration": self.expiration},
                                         timeout=self.timeout)
        except requests.RequestException as exc:  # message deliberately excludes the URL (it holds the key)
            raise ImageHostError(f"Image upload failed ({type(exc).__name__}).", retryable=True) from None
        try:
            body = response.json()
        except ValueError:
            body = {}
        url = (body.get("data") or {}).get("url") if isinstance(body, dict) else None
        if response.status_code >= 400 or not url:
            raise ImageHostError(f"Image host rejected the upload (HTTP {response.status_code}).",
                                 retryable=response.status_code >= 500)
        return url
