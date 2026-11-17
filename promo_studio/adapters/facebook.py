from __future__ import annotations

import datetime as dt
import logging
import os
import requests

from promo_studio.adapters.base import PlatformAdapter, PostPayload, PostResult
from promo_studio.adapters.graph import GraphError, call
from promo_studio.core.validators import validate_post

log = logging.getLogger(__name__)


class FacebookAdapter(PlatformAdapter):
    """Posts to a Facebook Page (photos, multi-image albums, and video reels)."""

    name = "facebook"
    HOST = "https://graph.facebook.com"

    def __init__(self, page_id: str, token: str, version: str = "v22.0", http=requests):
        self.page_id = page_id.strip()
        self.token = token.strip()
        self.version = version
        self.http = http

    def _url(self, path: str) -> str:
        return f"{self.HOST}/{self.version}/{path}"

    def validate(self, payload: PostPayload) -> list[str]:
        problems = validate_post("facebook", payload.text)
        if payload.image_path and not os.path.exists(payload.image_path):
            problems.append("Image file not found.")
        return problems

    def check_auth(self) -> bool:
        try:
            body = call(self.http, "GET", self._url(self.page_id),
                        params={"fields": "name", "access_token": self.token})
            self.last_account, self.last_error = body.get("name") or self.page_id, None
            return True
        except GraphError as exc:
            self.last_account, self.last_error = None, exc.message
            return False

    def has_posted_for_date(self, target_date: dt.date, post_type: str = "panchang") -> bool:
        """Idempotency guard: checks recent Page feed for machine slot IDs to avoid duplicate posts."""
        try:
            res = call(self.http, "GET", self._url(f"{self.page_id}/feed"),
                       params={"fields": "id,message,created_time", "limit": 25, "access_token": self.token})
            items = res.get("data", [])
            date_str = target_date.strftime("%Y%m%d")
            pt_lower = post_type.lower()
            canonical_slot = (
                "master" if pt_lower in ("master", "panchang", "master_panchang")
                else ("festival" if pt_lower == "festival"
                else ("reel" if pt_lower in ("reel", "reels")
                else ("muhurta" if pt_lower in ("plan_day", "muhurta")
                else ("transit" if pt_lower in ("jyotish", "transit")
                else pt_lower))))
            )
            target_slot_id = f"#siddhanta_slot_{canonical_slot}_{date_str}"
            for item in items:
                msg = (item.get("message") or "").lower()
                if target_slot_id in msg:
                    log.info("Facebook idempotency guard match [%s] (item %s)", target_slot_id, item.get("id"))
                    return True
        except Exception as e:
            log.warning("Facebook idempotency check query failed: %s; proceeding cautiously", e)
        return False

    def publish_single_url(self, image_url: str, caption: str) -> PostResult:
        """Publishes single photo from a public URL to Facebook Page."""
        try:
            body = call(self.http, "POST", self._url(f"{self.page_id}/photos"),
                        data={"url": image_url, "message": caption, "published": "true", "access_token": self.token},
                        timeout=60)
            post_id = str(body.get("post_id") or body.get("id") or "")
            return PostResult(self.name, True, post_id=post_id, url=f"https://www.facebook.com/{post_id}")
        except GraphError as exc:
            return exc.to_result(self.name)
        except Exception as exc:
            return PostResult(self.name, False, error_code="UNKNOWN", error_message=str(exc))

    def publish_multi_photo(self, image_urls: list[str], caption: str) -> PostResult:
        """Publishes multi-image album post to Facebook Page feed using unpublished photo containers."""
        if not image_urls:
            return PostResult(self.name, False, error_code="EMPTY", error_message="No images provided.")
        if len(image_urls) == 1:
            return self.publish_single_url(image_urls[0], caption)

        attached_media = []
        try:
            for url in image_urls:
                body = call(self.http, "POST", self._url(f"{self.page_id}/photos"),
                            data={"url": url, "published": "false", "access_token": self.token},
                            timeout=60)
                photo_id = body.get("id")
                if photo_id:
                    attached_media.append({"media_fbid": str(photo_id)})

            if not attached_media:
                return PostResult(self.name, False, error_code="UPLOAD_FAILED", error_message="Failed to upload photo items.")

            feed_body = call(self.http, "POST", self._url(f"{self.page_id}/feed"),
                             json={
                                 "message": caption,
                                 "attached_media": attached_media,
                                 "access_token": self.token,
                             },
                             timeout=60)
            post_id = str(feed_body.get("id") or "")
            return PostResult(self.name, True, post_id=post_id, url=f"https://www.facebook.com/{post_id}")
        except GraphError as exc:
            return exc.to_result(self.name)
        except Exception as exc:
            return PostResult(self.name, False, error_code="UNKNOWN", error_message=str(exc))

    def publish_video(self, video_url: str, caption: str, title: str | None = None) -> PostResult:
        """Publishes video/reel from a public MP4 URL to Facebook Page."""
        try:
            data = {
                "file_url": video_url,
                "description": caption,
                "access_token": self.token,
            }
            if title:
                data["title"] = title
            body = call(self.http, "POST", self._url(f"{self.page_id}/videos"), data=data, timeout=120)
            video_id = str(body.get("id") or "")
            return PostResult(self.name, True, post_id=video_id, url=f"https://www.facebook.com/{video_id}")
        except GraphError as exc:
            return exc.to_result(self.name)
        except Exception as exc:
            return PostResult(self.name, False, error_code="UNKNOWN", error_message=str(exc))

    def post(self, payload: PostPayload) -> PostResult:
        try:
            if payload.image_path:
                with open(payload.image_path, "rb") as fh:
                    body = call(self.http, "POST", self._url(f"{self.page_id}/photos"),
                                data={"message": payload.text, "published": "true", "access_token": self.token},
                                files={"source": fh}, timeout=90)
            else:
                data = {"message": payload.text, "access_token": self.token}
                if payload.link:
                    data["link"] = payload.link
                body = call(self.http, "POST", self._url(f"{self.page_id}/feed"), data=data)
        except GraphError as exc:
            return exc.to_result(self.name)
        except OSError:
            return PostResult(self.name, False, error_code="VALIDATION", error_message="Could not read the image file.")
        post_id = str(body.get("post_id") or body.get("id") or "")
        if not post_id:
            return PostResult(self.name, False, error_code="UNKNOWN", error_message="Facebook returned no post id.",
                              needs_check=True)
        return PostResult(self.name, True, post_id=post_id, url=f"https://www.facebook.com/{post_id}")

