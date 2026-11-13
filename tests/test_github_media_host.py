"""Unit tests for GitHubReleaseMediaHost and Instagram Reel publishing."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock

from promo_studio.automation.github_media_host import GitHubReleaseMediaHost
from promo_studio.automation.instagram_carousel import InstagramCarouselPublisher


def _resp(status_code: int, payload=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload or {}
    r.raise_for_status = MagicMock()
    return r


def test_github_release_upload_creates_release_and_returns_url(tmp_path: Path):
    mp4 = tmp_path / "reel.mp4"
    mp4.write_bytes(b"fake-mp4-bytes")

    http = MagicMock()
    http.get.side_effect = [
        _resp(404),  # release tag lookup
        _resp(200, []),  # cleanup list
    ]
    http.post.side_effect = [
        _resp(201, {
            "id": 10,
            "upload_url": "https://uploads.github.com/repos/tshashwat7/siddhanta-reels-media/releases/10/assets{?name,label}",
            "assets": [],
        }),
        _resp(201, {
            "browser_download_url": "https://github.com/tshashwat7/siddhanta-reels-media/releases/download/reel-2026-11-12/reel.mp4",
        }),
    ]
    http.head.return_value = _resp(200)

    host = GitHubReleaseMediaHost(token="ghp_test", http=http)
    url = host.upload_video(mp4, tag="reel-2026-11-12")

    assert url.endswith("/reel-2026-11-12/reel.mp4")
    assert http.head.called


def test_publish_reel_posts_reels_container_and_publishes():
    http = MagicMock()
    http.request.side_effect = [
        _resp(200, {"id": "container_1"}),
        _resp(200, {"status_code": "FINISHED"}),
        _resp(200, {"id": "media_99"}),
        _resp(200, {"permalink": "https://www.instagram.com/reel/abc123/"}),
    ]

    pub = InstagramCarouselPublisher("12345", "ig_tok", http=http, poll_interval=0.0)
    res = pub.publish_reel("https://example.com/reel.mp4", "Daily Panchang")

    assert res.ok is True
    assert res.post_id == "media_99"
    assert res.url == "https://www.instagram.com/reel/abc123/"

    first_call_json = http.request.call_args_list[0].kwargs["json"]
    assert first_call_json["media_type"] == "REELS"
    assert first_call_json["video_url"] == "https://example.com/reel.mp4"


def test_has_posted_for_date_detects_reel_by_media_type():
    ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
    ts = dt.datetime(2026, 11, 12, 6, 0, tzinfo=ist_tz).isoformat()

    http = MagicMock()
    http.request.return_value = _resp(200, {
        "data": [
            {"id": "1", "media_type": "REELS", "timestamp": ts, "caption": "Daily Panchang"},
        ]
    })

    pub = InstagramCarouselPublisher("12345", "ig_tok", http=http)
    assert pub.has_posted_for_date(dt.date(2026, 11, 12), "reel") is True
