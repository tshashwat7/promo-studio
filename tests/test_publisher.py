import threading
import time

from PIL import Image

from promo_studio.adapters.base import PlatformAdapter, PostPayload, PostResult
from promo_studio.core.image_host import ImageHost, ImageHostError
from promo_studio.core.image_service import ImageService
from promo_studio.core.publisher import Publisher
from promo_studio.data.db import Database


class FakeAdapter(PlatformAdapter):
    def __init__(self, name, results=None, needs_public_image=False, delay=0.0):
        self.name, self.results, self.delay = name, list(results or [PostResult(name, True, post_id="1", url=f"https://{name}/1")]), delay
        self.needs_public_image, self.payloads = needs_public_image, []

    def validate(self, payload):
        return ["too spicy"] if "spicy" in payload.text else []

    def post(self, payload):
        time.sleep(self.delay)
        self.payloads.append(payload)
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


class FakeHost(ImageHost):
    def __init__(self, error=None):
        self.uploads, self.error = [], error

    def upload(self, path):
        if self.error:
            raise self.error
        self.uploads.append(path)
        return "https://host/img.jpg"


def setup(tmp_path, adapters, host=None, **kw):
    db = Database(tmp_path / "t.db")
    pub = Publisher(db, adapters, ImageService(tmp_path / "tmp"), host, sleep=lambda s: None, **kw)
    return db, pub


def drafts(*platforms, text="Hello"):
    return [{"platform": p, "text": text, "hashtags": ["a"]} for p in platforms]


def image(tmp_path):
    path = tmp_path / "pic.png"
    Image.new("RGB", (900, 900), "blue").save(path)
    return str(path)


def test_posts_everywhere_and_records(tmp_path):
    fb, ig = FakeAdapter("facebook"), FakeAdapter("instagram")
    db, pub = setup(tmp_path, {"facebook": fb, "instagram": ig})
    pid = pub.create_post(None, "tip", "base", None, drafts("facebook", "instagram"))
    events = []
    results = pub.publish(pid, on_event=events.append)
    assert all(r.ok for r in results.values())
    assert db.get_post(pid)["status"] == "posted"
    assert fb.payloads[0].text == "Hello\n\n#a"                      # hashtags appended
    assert {t.status for t in db.list_targets(pid)} == {"posted"}
    assert events[-1] == {"type": "done", "post_status": "posted"}
    assert {e["status"] for e in events if e["type"] == "status"} == {"posting", "posted"}


def test_platforms_run_in_parallel(tmp_path):
    adapters = {n: FakeAdapter(n, delay=0.3) for n in ("facebook", "instagram", "x")}
    db, pub = setup(tmp_path, adapters)
    pid = pub.create_post(None, "tip", "", None, drafts("facebook", "instagram", "x"))
    start = time.time()
    pub.publish(pid)
    assert time.time() - start < 0.7  # sequential would be 0.9s+


def test_one_failure_does_not_block_others(tmp_path):
    bad = FakeAdapter("instagram", [PostResult("instagram", False, error_code="AUTH", error_message="expired")])
    db, pub = setup(tmp_path, {"facebook": FakeAdapter("facebook"), "instagram": bad})
    pid = pub.create_post(None, "tip", "", None, drafts("facebook", "instagram"))
    results = pub.publish(pid)
    assert results["facebook"].ok and not results["instagram"].ok
    assert db.get_post(pid)["status"] == "partial"
    assert bad.payloads and len(bad.payloads) == 1                     # AUTH is not retried


def test_retryable_errors_retry_then_succeed(tmp_path):
    flaky = FakeAdapter("facebook", [PostResult("facebook", False, error_code="NETWORK", retryable=True),
                                     PostResult("facebook", False, error_code="RATE_LIMIT", retryable=True),
                                     PostResult("facebook", True, post_id="9")])
    db, pub = setup(tmp_path, {"facebook": flaky}, retries=2)
    pid = pub.create_post(None, "tip", "", None, drafts("facebook"))
    assert pub.publish(pid)["facebook"].ok
    assert db.list_targets(pid)[0].attempts == 3


def test_retries_are_capped(tmp_path):
    always = FakeAdapter("facebook", [PostResult("facebook", False, error_code="NETWORK", retryable=True)])
    db, pub = setup(tmp_path, {"facebook": always}, retries=1)
    pid = pub.create_post(None, "tip", "", None, drafts("facebook"))
    assert not pub.publish(pid)["facebook"].ok
    assert len(always.payloads) == 2 and db.get_post(pid)["status"] == "failed"


def test_needs_check_is_never_retried(tmp_path):
    unsure = FakeAdapter("instagram", [PostResult("instagram", False, error_code="NETWORK", retryable=True, needs_check=True)])
    db, pub = setup(tmp_path, {"instagram": unsure}, retries=3)
    pid = pub.create_post(None, "tip", "", None, drafts("instagram"))
    pub.publish(pid)
    assert len(unsure.payloads) == 1 and db.list_targets(pid)[0].status == "needs_check"
    assert pub.publish(pid) == {}          # needs_check targets are left alone until the user decides


def test_posted_targets_are_not_posted_twice(tmp_path):
    fb = FakeAdapter("facebook")
    db, pub = setup(tmp_path, {"facebook": fb})
    pid = pub.create_post(None, "tip", "", None, drafts("facebook"))
    pub.publish(pid)
    pub.publish(pid)
    assert len(fb.payloads) == 1


def test_failed_targets_can_be_retried_alone(tmp_path):
    fb = FakeAdapter("facebook", [PostResult("facebook", False, error_code="PLATFORM"), PostResult("facebook", True, post_id="2")])
    ig = FakeAdapter("instagram")
    db, pub = setup(tmp_path, {"facebook": fb, "instagram": ig})
    pid = pub.create_post(None, "tip", "", None, drafts("facebook", "instagram"))
    pub.publish(pid)
    res = pub.publish(pid, only={"facebook"})
    assert res["facebook"].ok and len(ig.payloads) == 1
    assert db.get_post(pid)["status"] == "posted"


def test_blocked_by_validation_or_missing_adapter(tmp_path):
    db, pub = setup(tmp_path, {"facebook": FakeAdapter("facebook")})
    pid = pub.create_post(None, "tip", "", None,
                          [{"platform": "facebook", "text": "spicy take"}, {"platform": "x", "text": "hi"}])
    events = []
    res = pub.publish(pid, on_event=events.append)
    assert "too spicy" in res["facebook"].error_message and "Not configured" in res["x"].error_message
    assert [e["status"] for e in events if e["type"] == "status"] == ["blocked", "blocked"]
    assert db.get_post(pid)["status"] == "failed"


def test_public_image_flow_uses_host_and_cleans_up(tmp_path):
    ig, host = FakeAdapter("instagram", needs_public_image=True), FakeHost()
    db, pub = setup(tmp_path, {"instagram": ig}, host=host)
    pid = pub.create_post(None, "tip", "", image(tmp_path), drafts("instagram"))
    assert pub.publish(pid)["instagram"].ok
    sent = ig.payloads[0]
    assert sent.image_url == "https://host/img.jpg" and sent.image_path is None
    assert host.uploads[0].endswith(".jpg") and not __import__("os").path.exists(host.uploads[0])


def test_local_image_flow_for_facebook(tmp_path):
    fb = FakeAdapter("facebook")
    db, pub = setup(tmp_path, {"facebook": fb})
    pid = pub.create_post(None, "tip", "", image(tmp_path), drafts("facebook"))
    pub.publish(pid)
    assert fb.payloads[0].image_path.endswith(".jpg") and fb.payloads[0].image_url is None


def test_missing_image_host_blocks_instagram(tmp_path):
    db, pub = setup(tmp_path, {"instagram": FakeAdapter("instagram", needs_public_image=True)})
    pid = pub.create_post(None, "tip", "", image(tmp_path), drafts("instagram"))
    assert "Image host is not configured" in pub.publish(pid)["instagram"].error_message


def test_image_host_failure_is_retried_then_reported(tmp_path):
    ig = FakeAdapter("instagram", needs_public_image=True)
    db, pub = setup(tmp_path, {"instagram": ig}, host=FakeHost(ImageHostError("upload failed", retryable=True)), retries=2)
    pid = pub.create_post(None, "tip", "", image(tmp_path), drafts("instagram"))
    res = pub.publish(pid)["instagram"]
    assert not res.ok and res.error_code == "NETWORK" and ig.payloads == []
    assert db.list_targets(pid)[0].attempts == 3


def test_adapter_crash_becomes_unknown_error(tmp_path):
    class Boom(FakeAdapter):
        def post(self, payload):
            raise RuntimeError("kaboom with secret-token")

    db, pub = setup(tmp_path, {"facebook": Boom("facebook")})
    pid = pub.create_post(None, "tip", "", None, drafts("facebook"))
    res = pub.publish(pid)["facebook"]
    assert res.error_code == "UNKNOWN" and "secret-token" not in res.error_message


def test_stale_posting_targets_flagged_on_startup(tmp_path):
    db = Database(tmp_path / "t.db")
    pid = db.create_post(None, "tip", "", None)
    tid = db.add_target(pid, "facebook", "x", status="posting")
    assert db.mark_stale_posting() == 1
    assert db.get_target(tid).status == "needs_check"
