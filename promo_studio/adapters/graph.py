"""Shared HTTP + error handling for Meta Graph API calls (Facebook and Instagram)."""
from __future__ import annotations

import requests

from promo_studio.adapters.base import PostResult

_RATE_CODES = {4, 17, 32, 613, 80001, 80002, 80003, 80004, 80005, 80006, 80008}


class GraphError(Exception):
    def __init__(self, error_code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.error_code, self.message, self.retryable = error_code, message, retryable

    def to_result(self, platform: str) -> PostResult:
        return PostResult(platform, False, error_code=self.error_code, error_message=self.message,
                          retryable=self.retryable)


def classify(status: int, body) -> GraphError:
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, dict):
        code, text = err.get("code"), str(err.get("message", "Unknown error"))[:240]
        if code in (102, 190):
            return GraphError("AUTH", "Access token expired or invalid. Reconnect or refresh it in Settings.")
        if code in _RATE_CODES:
            return GraphError("RATE_LIMIT", f"Rate limit reached: {text}", retryable=True)
        if code == 10 or (isinstance(code, int) and 200 <= code <= 299):
            return GraphError("AUTH", f"Missing permission: {text}")
        if code in (1, 2, 9007):
            return GraphError("PLATFORM", f"Temporary platform problem: {text}", retryable=True)
        if code == 100:
            return GraphError("VALIDATION", f"Rejected by the platform: {text}")
        return GraphError("PLATFORM", text, retryable=status >= 500)
    if status == 429:
        return GraphError("RATE_LIMIT", "Too many requests.", retryable=True)
    if status in (401, 403):
        return GraphError("AUTH", "Not authorized. Check the token in Settings.")
    if status >= 500:
        return GraphError("PLATFORM", f"Platform error (HTTP {status}).", retryable=True)
    return GraphError("UNKNOWN", f"Unexpected response (HTTP {status}).")


def call(http, method: str, url: str, *, timeout: int = 30, **kwargs) -> dict:
    """Make a request and return the JSON body, or raise GraphError. Never leaks the URL in messages."""
    try:
        response = http.request(method, url, timeout=timeout, **kwargs)
    except requests.Timeout:
        raise GraphError("NETWORK", "The request timed out.", retryable=True) from None
    except requests.RequestException as exc:
        raise GraphError("NETWORK", f"Network problem ({type(exc).__name__}).", retryable=True) from None
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400 or (isinstance(body, dict) and "error" in body):
        raise classify(response.status_code, body)
    return body if isinstance(body, dict) else {}
