"""Instagram Carousel and Single-Image publisher via Graph API.

Supports:
- 2-Slide Carousels (Slide 1 Hook + Slide 2 Actionable Windows)
- Single 4:5 Portrait Card (Combined Daily Cosmic Blueprint)
- Automatic fallback to single card if carousel creation is rejected.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
import requests

from promo_studio.adapters.base import PostResult
from promo_studio.adapters.graph import GraphError, call

log = logging.getLogger(__name__)


class InstagramCarouselPublisher:
    def __init__(self, ig_user_id: str, token: str, version: str = "v25.0",
                 http=requests, poll_attempts: int = 6, poll_interval: float = 3.0):
        self.ig_user_id = ig_user_id.strip()
        self.token = token.strip()
        self.version = version
        self.http = http
        self.poll_attempts = poll_attempts
        self.poll_interval = poll_interval
        self.host = "https://graph.instagram.com"

    def has_posted_for_date(self, target_date: dt.date, post_type: str = "panchang") -> bool:
        """Idempotency guard: checks recent Instagram media to determine if target post was already published."""
        try:
            res = call(self.http, "GET", self._url(f"{self.ig_user_id}/media"),
                       headers=self._headers,
                       params={"fields": "id,caption,timestamp,media_type", "limit": 15})
            items = res.get("data", [])
            ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
            for item in items:
                ts = item.get("timestamp", "")
                cap = item.get("caption", "")
                media_type = (item.get("media_type") or "").upper()
                if ts:
                    try:
                        post_dt = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        post_date = post_dt.astimezone(ist_tz).date()
                    except Exception:
                        post_date = None
                    if post_date == target_date:
                        pt_lower = post_type.lower()
                        cap_lower = cap.lower()

                        matched = False
                        if pt_lower in ("reel", "reels"):
                            matched = media_type in ("REELS", "VIDEO")
                        elif pt_lower in ("master", "panchang", "master_panchang"):
                            matched = (
                                "#siddhanta_dailyguide" in cap_lower
                                or "daily panchang" in cap_lower
                                or "panchang overview" in cap_lower
                                or "दैनिक पंचांग" in cap_lower
                                or "पंचांग" in cap
                            )
                        elif pt_lower == "festival":
                            matched = (
                                "#siddhanta_festival" in cap_lower
                                or "festival alert" in cap_lower
                                or "पर्व" in cap
                                or "त्योहार" in cap
                                or "vrat" in cap_lower
                            )
                        elif pt_lower in ("plan_day", "muhurta"):
                            matched = "plan your day" in cap_lower or "choghadiya" in cap_lower or "चौघड़िया" in cap_lower or "शुभ मुहूर्त" in cap
                        elif pt_lower == "jyotish":
                            matched = "planetary transit" in cap_lower or "sky & planetary" in cap_lower or "गोचर" in cap
                        elif pt_lower in ("chakra", "kundli"):
                            matched = pt_lower in cap_lower

                        if matched:
                            log.info("Found existing Instagram post %s for %s (%s)", item.get("id"), target_date, post_type)
                            return True
        except Exception as e:
            log.warning("Idempotency check query failed: %s; proceeding cautiously", e)
        return False

    def _url(self, path: str) -> str:
        return f"{self.host}/{self.version}/{path}"

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _wait_ready(self, container_id: str, poll_attempts: int | None = None,
                    poll_interval: float | None = None) -> bool:
        attempts = poll_attempts if poll_attempts is not None else self.poll_attempts
        interval = poll_interval if poll_interval is not None else self.poll_interval
        for attempt in range(attempts):
            try:
                res = call(self.http, "GET", self._url(container_id), headers=self._headers,
                           params={"fields": "status_code"})
                status = res.get("status_code")
                if status == "FINISHED":
                    return True
                if status in ("ERROR", "EXPIRED"):
                    log.warning("Container %s failed with status %s", container_id, status)
                    return False
            except GraphError:
                pass
            time.sleep(interval)
        return True  # Try publishing anyway if poll timed out

    def publish_single(self, image_url: str, caption: str) -> PostResult:
        """Publishes single image post to Instagram."""
        try:
            container = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"),
                             headers=self._headers,
                             json={"image_url": image_url, "caption": caption})["id"]
        except GraphError as exc:
            return exc.to_result("instagram")

        self._wait_ready(container)

        try:
            media_id = call(self.http, "POST", self._url(f"{self.ig_user_id}/media_publish"),
                            headers=self._headers, json={"creation_id": container})["id"]
            permalink = self._get_permalink(str(media_id))
            return PostResult("instagram", True, post_id=str(media_id), url=permalink)
        except GraphError as exc:
            return exc.to_result("instagram")

    def publish_carousel(self, image_urls: list[str], caption: str) -> PostResult:
        """Publishes 2-slide carousel to Instagram, with fallback to first image on error."""
        if len(image_urls) < 2:
            return self.publish_single(image_urls[0], caption)

        item_containers = []
        try:
            for url in image_urls:
                item_res = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"),
                                headers=self._headers,
                                json={"image_url": url, "is_carousel_item": True})
                item_id = item_res["id"]
                self._wait_ready(item_id)
                item_containers.append(item_id)

            carousel_res = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"),
                                headers=self._headers,
                                json={
                                    "media_type": "CAROUSEL",
                                    "children": item_containers,
                                    "caption": caption
                                })
            carousel_container_id = carousel_res["id"]
            self._wait_ready(carousel_container_id)

            media_id = call(self.http, "POST", self._url(f"{self.ig_user_id}/media_publish"),
                            headers=self._headers,
                            json={"creation_id": carousel_container_id})["id"]
            permalink = self._get_permalink(str(media_id))
            return PostResult("instagram", True, post_id=str(media_id), url=permalink)

        except Exception as exc:
            log.warning("Carousel publish error: %s. Falling back to single image.", exc)
            return self.publish_single(image_urls[0], caption)

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        share_to_feed: bool = True,
        poll_attempts: int = 20,
        poll_interval: float = 5.0,
    ) -> PostResult:
        """Publishes a Reel from a public MP4 URL via Instagram Graph API."""
        try:
            container = call(
                self.http,
                "POST",
                self._url(f"{self.ig_user_id}/media"),
                headers=self._headers,
                json={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "share_to_feed": share_to_feed,
                },
            )["id"]
        except GraphError as exc:
            return exc.to_result("instagram")

        if not self._wait_ready(container, poll_attempts=poll_attempts, poll_interval=poll_interval):
            return PostResult("instagram", False, error_code="PLATFORM",
                              error_message="Instagram could not process the Reel video.")

        try:
            media_id = call(
                self.http,
                "POST",
                self._url(f"{self.ig_user_id}/media_publish"),
                headers=self._headers,
                json={"creation_id": container},
            )["id"]
            permalink = self._get_permalink(str(media_id))
            return PostResult("instagram", True, post_id=str(media_id), url=permalink)
        except GraphError as exc:
            return exc.to_result("instagram")

    def _get_permalink(self, media_id: str) -> str:
        try:
            body = call(self.http, "GET", self._url(media_id), headers=self._headers, params={"fields": "permalink"})
            return body.get("permalink") or "https://www.instagram.com/"
        except Exception:
            return "https://www.instagram.com/"
