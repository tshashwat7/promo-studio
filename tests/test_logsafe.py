import io
import logging

from promo_studio.core.logsafe import RedactFilter, redact

KEY = "AIzaSyA1234567890abcdefghijklmnopqrstuv"


def test_redact_patterns():
    assert KEY not in redact(f"key is {KEY}")
    assert "s3cr3tvalue" not in redact("https://x/api?token=s3cr3tvalue&a=1")
    assert "abcdef123456" not in redact("Authorization: Bearer abcdef123456")
    assert redact("plain text") == "plain text"


def test_redact_known_secret_values():
    assert "hunter2hunter2" not in redact("password was hunter2hunter2", ["hunter2hunter2"])


def test_filter_redacts_messages_and_tracebacks(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "custom-secret-value-123")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactFilter())
    logger = logging.getLogger("logsafe-test")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("calling with %s", KEY)
    try:
        raise RuntimeError("failed for custom-secret-value-123")
    except RuntimeError:
        logger.exception("boom")
    out = stream.getvalue()
    assert KEY not in out and "custom-secret-value-123" not in out
    assert "[REDACTED]" in out and "boom" in out
