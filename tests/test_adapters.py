import pytest
import requests

from promo_studio.adapters.base import PostPayload
from promo_studio.adapters.facebook import FacebookAdapter
from promo_studio.adapters.graph import classify
from promo_studio.adapters.instagram import InstagramAdapter
from tests.fakes import FakeHttp, FakeResponse


def err(code, status=400, message="boom"):
    return FakeResponse(status, {"error": {"code": code, "message": message}})


# ---- error classification -------------------------------------------------
@pytest.mark.parametrize("status,body,code,retry", [
    (400, {"error": {"code": 190, "message": "expired"}}, "AUTH", False),
    (400, {"error": {"code": 4, "message": "limit"}}, "RATE_LIMIT", True),
    (403, {"error": {"code": 200, "message": "perm"}}, "AUTH", False),
    (400, {"error": {"code": 100, "message": "bad"}}, "VALIDATION", False),
    (500, {"error": {"code": 2, "message": "temp"}}, "PLATFORM", True),
    (503, {}, "PLATFORM", True),
    (429, {}, "RATE_LIMIT", True),
    (401, {}, "AUTH", False),
])
def test_classify(status, body, code, retry):
    e = classify(status, body)
    assert (e.error_code, e.retryable) == (code, retry)


# ---- Facebook -------------------------------------------------------------
def test_facebook_text_post_uses_feed():
    http = FakeHttp({"id": "123_456"})
    res = FacebookAdapter("123", "tok", http=http).post(PostPayload(text="hello", link="https://x.app"))
    assert res.ok and res.post_id == "123_456" and res.url.endswith("/123_456")
    method, url, kw = http.calls[0]
    assert url.endswith("/v25.0/123/feed") and kw["data"]["link"] == "https://x.app"


def test_facebook_photo_post(tmp_path):
    img = tmp_path / "a.jpg"
    img.write_bytes(b"jpegdata")
    http = FakeHttp({"id": "p1", "post_id": "123_789"})
    res = FacebookAdapter("123", "tok", http=http).post(PostPayload(text="hi", image_path=str(img)))
    assert res.ok and res.post_id == "123_789"
    assert http.calls[0][1].endswith("/123/photos") and "source" in http.calls[0][2]["files"]


def test_facebook_errors_are_mapped_without_leaking_token():
    res = FacebookAdapter("1", "SECRET", http=FakeHttp(err(190))).post(PostPayload(text="x"))
    assert not res.ok and res.error_code == "AUTH" and "SECRET" not in res.error_message
    res = FacebookAdapter("1", "t", http=FakeHttp(requests.ConnectionError("https://x?access_token=SECRET"))).post(
        PostPayload(text="x"))
    assert res.error_code == "NETWORK" and res.retryable and "SECRET" not in res.error_message


def test_facebook_check_auth():
    a = FacebookAdapter("1", "t", http=FakeHttp({"name": "Siddhanta"}))
    assert a.check_auth() and a.last_account == "Siddhanta"
    b = FacebookAdapter("1", "t", http=FakeHttp(err(190)))
    assert not b.check_auth() and "expired" in b.last_error


# ---- Instagram ------------------------------------------------------------
def ig(http, **kw):
    return InstagramAdapter("999", "tok", http=http, sleep=lambda s: None, **kw)


def test_instagram_happy_path():
    http = FakeHttp({"id": "C1"}, {"status_code": "FINISHED"}, {"id": "M1"}, {"permalink": "https://instagram.com/p/abc/"})
    res = ig(http).post(PostPayload(text="cap", image_url="https://img/x.jpg"))
    assert res.ok and res.post_id == "M1" and res.url == "https://instagram.com/p/abc/"
    create, status, publish, _ = http.calls
    assert create[1].endswith("/999/media") and create[2]["json"] == {"image_url": "https://img/x.jpg", "caption": "cap"}
    assert create[2]["headers"]["Authorization"] == "Bearer tok"
    assert publish[1].endswith("/999/media_publish") and publish[2]["json"] == {"creation_id": "C1"}


def test_instagram_waits_for_processing():
    http = FakeHttp({"id": "C1"}, {"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}, {"id": "M1"}, {})
    assert ig(http).post(PostPayload(text="c", image_url="u")).ok


def test_instagram_container_error_is_reported():
    http = FakeHttp({"id": "C1"}, {"status_code": "ERROR"})
    res = ig(http).post(PostPayload(text="c", image_url="u"))
    assert not res.ok and "could not process" in res.error_message and not res.retryable


def test_instagram_still_processing_is_retryable():
    http = FakeHttp({"id": "C1"}, *[{"status_code": "IN_PROGRESS"}] * 3)
    res = ig(http, poll_attempts=3).post(PostPayload(text="c", image_url="u"))
    assert not res.ok and res.retryable


def test_instagram_ambiguous_publish_is_never_retried():
    http = FakeHttp({"id": "C1"}, {"status_code": "FINISHED"}, requests.Timeout("slow"))
    res = ig(http).post(PostPayload(text="c", image_url="u"))
    assert not res.ok and res.needs_check and not res.retryable


def test_instagram_definite_publish_failure_is_plain_error():
    http = FakeHttp({"id": "C1"}, {"status_code": "FINISHED"}, err(190))
    res = ig(http).post(PostPayload(text="c", image_url="u"))
    assert res.error_code == "AUTH" and not res.needs_check


def test_instagram_needs_public_url_and_validates_image():
    a = ig(FakeHttp())
    assert a.post(PostPayload(text="c")).error_code == "VALIDATION"
    assert "Instagram needs an image." in a.validate(PostPayload(text="hello"))
    assert a.validate(PostPayload(text="hello", image_path="x.jpg")) == []


def test_instagram_check_auth_and_refresh():
    a = ig(FakeHttp({"username": "siddhanta.app"}))
    assert a.check_auth() and a.last_account == "@siddhanta.app"
    b = ig(FakeHttp({"access_token": "NEW", "expires_in": 5184000}))
    assert b.refresh_token() == ("NEW", 5184000)
