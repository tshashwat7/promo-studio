import json

import pytest

from promo_studio.ai.base import AIError, AIProvider, RateLimitError
from promo_studio.core.draft_service import DraftError, DraftService, parse_json
from promo_studio.data.models import AppProfile

GOOD = {"variants": [{
    "angle": "tip",
    "x": {"text": "Wind down early tonight.", "hashtags": ["#Sleep", "sleep", "rest", "night"]},
    "facebook": {"text": "A longer note about winding down.", "hashtags": ["sleeprise"]},
    "instagram": {"caption": "Start with the first line.", "hashtags": ["a", "b", "c", "d", "e", "f"]},
    "reddit": {"title": "I built a sleep app", "body": "I am the developer.", "suggested_subreddits": ["r/SideProject"]},
}]}


class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def generate(self, system, user, temperature=0.8):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


def profile(**kw):
    return AppProfile(name="SleepRise", pitch="Wake up gently", **kw)


def service(replies, **kw):
    return DraftService(FakeProvider(replies), sleep=lambda s: None, **kw)


def test_parse_json_handles_fences_and_noise():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! {"a": 1} hope that helps') == {"a": 1}
    with pytest.raises(ValueError):
        parse_json("nothing here")


def test_generate_cleans_and_caps_hashtags():
    result = service([GOOD]).generate(profile(), "tip", n=1)
    v = result.variants[0]
    assert v["x"]["hashtags"] == ["sleep", "rest"]          # cap 2, de-duplicated
    assert len(v["instagram"]["hashtags"]) == 5             # cap 5
    assert v["reddit"]["hashtags"] == []
    assert v["reddit"]["subreddits"] == ["SideProject"]
    assert v["instagram"]["text"] == "Start with the first line."
    assert v["x"]["problems"] == []


def test_flags_over_limit_and_banned_phrases():
    data = {"variants": [{"x": {"text": "guaranteed " + "a" * 300, "hashtags": []}}]}
    result = service([data]).generate(profile(banned_phrases=["guaranteed"]), "tip", platforms=["x"], n=1)
    problems = result.variants[0]["x"]["problems"]
    assert any("Over the limit" in p for p in problems)
    assert any("banned" in p for p in problems)


def test_repairs_invalid_json_once():
    svc = service(["not json at all", GOOD])
    assert svc.generate(profile(), "tip", n=1).variants
    assert svc.provider.calls == 2


def test_two_bad_replies_raise():
    with pytest.raises(DraftError):
        service(["nope", "still nope"]).generate(profile(), "tip")


def test_retries_rate_limit_then_succeeds():
    svc = service([RateLimitError("429"), GOOD])
    assert svc.generate(profile(), "tip", n=1).variants
    assert svc.provider.calls == 2


def test_rate_limit_exhausted_gives_friendly_error():
    svc = service([RateLimitError("429")] * 3)
    with pytest.raises(DraftError, match="rate limit"):
        svc.generate(profile(), "tip")


def test_provider_error_is_wrapped():
    with pytest.raises(DraftError, match="provider error"):
        service([AIError("boom")]).generate(profile(), "tip")


def test_warns_when_fewer_variants_than_asked():
    result = service([GOOD]).generate(profile(), "tip", n=3)
    assert result.warnings and "got 1" in result.warnings[0]


def test_shorten_returns_verified_text():
    svc = service([{"text": "Short and sweet."}])
    assert svc.shorten("x", "a" * 400, 100) == "Short and sweet."


def test_shorten_retries_when_still_too_long_then_fails():
    svc = service([{"text": "b" * 300}, {"text": "c" * 300}])
    with pytest.raises(DraftError, match="Trim it by hand"):
        svc.shorten("x", "a" * 400, 100)
    assert svc.provider.calls == 2


def test_shorten_recovers_on_second_try():
    svc = service([{"text": "b" * 300}, {"text": "ok now"}])
    assert svc.shorten("x", "a" * 400, 100) == "ok now"
