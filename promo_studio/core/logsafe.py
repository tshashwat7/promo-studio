"""Keep secrets out of log files: redact known keys, tokens and credential-looking values."""
from __future__ import annotations

import logging
import os
import re

SECRET_ENV_NAMES = (
    "GEMINI_API_KEY", "META_APP_SECRET", "FB_PAGE_TOKEN", "IG_ACCESS_TOKEN", "X_API_KEY", "X_API_SECRET",
    "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "REDDIT_CLIENT_SECRET", "REDDIT_PASSWORD", "IMAGE_HOST_KEY",
)
MASK = "[REDACTED]"
_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), MASK),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"), r"\1" + MASK),
    (re.compile(r"(?i)\b(access_token|refresh_token|token|api_key|apikey|key|password|secret|client_secret)=([^&\s\"']+)"),
     r"\1=" + MASK),
]


def redact(text: str, extra_secrets=()) -> str:
    for secret in extra_secrets:
        if secret and len(secret) >= 6:
            text = text.replace(secret, MASK)
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactFilter(logging.Filter):
    """Attach to a handler: rewrites the message and any traceback before they are written."""

    @staticmethod
    def _secrets() -> list[str]:
        return [os.environ.get(name, "") for name in SECRET_ENV_NAMES]

    def filter(self, record: logging.LogRecord) -> bool:
        secrets = self._secrets()
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        record.msg, record.args = redact(message, secrets), None
        if record.exc_info and not record.exc_text:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info), secrets)
        return True
