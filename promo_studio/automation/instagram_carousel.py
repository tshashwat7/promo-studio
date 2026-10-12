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
                       params={"fields": "id,caption,timestamp", "limit": 10})
            items = res.get("data", [])
            ist_tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
            for item in items:
                ts = item.get("timestamp", "")
                cap = item.get("caption", "")
                if ts:
                    try:
                        post_dt = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        post_date = post_dt.astimezone(ist_tz).date()
                    except Exception:
                        post_date = None
                    if post_date == target_date:
                        pt_lower = post_type.lower()
                        # Match post type keywords or date strings
                        if pt_lower in cap.lower() or (pt_lower == "panchang" and ("पंचांग" in cap or "panchang" in cap.lower())):
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

    def _wait_ready(self, container_id: str) -> bool:
        for attempt in range(self.poll_attempts):
            try:
                res = call(self.http, "GET", self._url(container_id), headers=self._headers,
                           params={"fields": "status_code,status"})
                status = res.get("status_code")
                if status == "FINISHED":
                    return True
                if status in ("ERROR", "EXPIRED"):
                    log.warning("Container %s failed with status_code: %s (detail: %s)",
                                container_id, status, res.get("status"))
                    return False
            except GraphError:
                pass
            time.sleep(self.poll_interval)
        return False

    def _create_child_container(self, url: str) -> str | None:
        """Creates a single carousel item container and waits until it is FINISHED."""
        for attempt in range(1, 3):
            try:
                item_res = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"),
                                headers=self._headers,
                                json={"image_url": url, "is_carousel_item": True, "media_type": "IMAGE"})
                item_id = item_res.get("id")
                if item_id and self._wait_ready(item_id):
                    return item_id
                log.warning("Child container %s not ready on attempt %d; retrying in 4s...", item_id, attempt)
                time.sleep(4)
            except Exception as e:
                log.warning("Child container creation failed on attempt %d: %s", attempt, e)
                time.sleep(4)
        return None

    def publish_single(self, image_url: str, caption: str) -> PostResult:
        """Publishes single image post to Instagram."""
        container = None
        for attempt in range(1, 3):
            try:
                container = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"),
                                 headers=self._headers,
                                 json={"image_url": image_url, "caption": caption, "media_type": "IMAGE"})["id"]
                if self._wait_ready(container):
                    break
                log.warning("Single container %s not ready on attempt %d; retrying in 4s...", container, attempt)
                time.sleep(4)
                container = None
            except GraphError as exc:
                if attempt == 2:
                    return exc.to_result("instagram")
                time.sleep(4)

        if not container:
            return PostResult("instagram", False, error_code="PLATFORM",
                              error_message="Instagram container could not be processed. Image URL was not reachable.")

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
            for idx, url in enumerate(image_urls):
                log.info("Preparing carousel item container %d/%d...", idx + 1, len(image_urls))
                item_id = self._create_child_container(url)
                if not item_id:
                    raise GraphError("PLATFORM", f"Child container {idx+1} could not be processed by Instagram.")
                item_containers.append(item_id)

            carousel_res = call(self.http, "POST", self._url(f"{self.ig_user_id}/media"),
                                headers=self._headers,
                                json={
                                    "media_type": "CAROUSEL",
                                    "children": item_containers,
                                    "caption": caption
                                })
            carousel_container_id = carousel_res["id"]
            if not self._wait_ready(carousel_container_id):
                raise GraphError("PLATFORM", "Instagram carousel parent container could not be processed.")

            media_id = call(self.http, "POST", self._url(f"{self.ig_user_id}/media_publish"),
                            headers=self._headers,
                            json={"creation_id": carousel_container_id})["id"]
            permalink = self._get_permalink(str(media_id))
            return PostResult("instagram", True, post_id=str(media_id), url=permalink)

        except Exception as exc:
            log.warning("Carousel publish error: %s. Falling back to single image.", exc)
            return self.publish_single(image_urls[0], caption)

    def _get_permalink(self, media_id: str) -> str:
        try:
            body = call(self.http, "GET", self._url(media_id), headers=self._headers, params={"fields": "permalink"})
            return body.get("permalink") or "https://www.instagram.com/"
        except Exception:
            return "https://www.instagram.com/"
