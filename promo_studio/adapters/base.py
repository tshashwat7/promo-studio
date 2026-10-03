"""Common interface for platform adapters (implemented from phase 2)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PostPayload:
    text: str
    image_path: str | None = None
    image_url: str | None = None
    title: str | None = None
    link: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class PostResult:
    platform: str
    ok: bool
    post_id: str | None = None
    url: str | None = None
    error_code: str | None = None  # AUTH, RATE_LIMIT, VALIDATION, NETWORK, PLATFORM, UNKNOWN
    error_message: str | None = None
    retryable: bool = False
    needs_check: bool = False  # outcome unknown: the post may have gone through


class PlatformAdapter(ABC):
    name: str
    needs_public_image: bool = False  # True if the platform fetches the image from a public URL
    last_account: str | None = None
    last_error: str | None = None

    @abstractmethod
    def validate(self, payload: PostPayload) -> list[str]:
        """Return problems; empty list means the payload can be posted."""

    @abstractmethod
    def post(self, payload: PostPayload) -> PostResult: ...

    def prepare_image(self, path: str) -> str:
        return path

    def check_auth(self) -> bool:
        return False
