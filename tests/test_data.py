from promo_studio.config.settings import Settings
from promo_studio.core.limiter import RateLimiter
from promo_studio.data.db import Database
from promo_studio.data.models import AppProfile


def test_profile_crud(tmp_path):
    db = Database(tmp_path / "t.db")
    p = AppProfile(name="Siddhanta", pitch="Vedic", features=["a", "b"],
                   store_links={"ios": "https://x"}, banned_phrases=["cure"])
    pid = db.save_profile(p)
    loaded = db.get_profile(pid)
    assert loaded.features == ["a", "b"] and loaded.store_links == {"ios": "https://x"}
    loaded.pitch = "Updated"
    db.save_profile(loaded)
    assert db.get_profile(pid).pitch == "Updated"
    assert [x.name for x in db.list_profiles()] == ["Siddhanta"]
    db.delete_profile(pid)
    assert db.list_profiles() == []


def test_settings_defaults_and_overrides(tmp_path):
    s = Settings(Database(tmp_path / "t.db"))
    assert s.get("ai.provider") == "gemini" and s.get_int("ai.variants") == 3
    s.set("ai.variants", "5")
    assert s.get_int("ai.variants") == 5
    assert s.hashtag_caps()["instagram"] == 5


def test_rate_limiter_blocks_after_capacity():
    now = [0.0]
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(2, clock=lambda: now[0], sleep=sleep)
    limiter.acquire()
    limiter.acquire()
    assert slept == []
    limiter.acquire()  # third call must wait for the window to clear
    assert slept and sum(slept) >= 59
