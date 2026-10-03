"""Fans one approved post out to every platform adapter in parallel and records each outcome."""
from __future__ import annotations

import dataclasses
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from promo_studio.adapters.base import PostPayload, PostResult
from promo_studio.core.image_host import ImageHostError
from promo_studio.core.validators import compose_text

log = logging.getLogger(__name__)
OPEN_STATUSES = ("draft", "scheduled", "failed")  # statuses the Publisher will (re)try


class Publisher:
    def __init__(self, db, adapters: dict, image_service, image_host=None, max_parallel: int = 4,
                 retries: int = 2, sleep=time.sleep):
        self.db, self.adapters = db, adapters
        self.image_service, self.image_host = image_service, image_host
        self.max_parallel, self.retries, self._sleep = max(1, max_parallel), max(0, retries), sleep

    # ---- creating a post ---------------------------------------------------
    def create_post(self, profile_id, angle: str, base_text: str, image_path: str | None, drafts: list[dict]) -> int:
        """drafts: [{"platform", "text", "hashtags", "title"?, "extra"?}] with text WITHOUT hashtags."""
        post_id = self.db.create_post(profile_id, angle, base_text, image_path)
        for d in drafts:
            self.db.add_target(post_id, d["platform"], d["text"], d.get("hashtags", []), d.get("title"), d.get("extra"))
        return post_id

    # ---- publishing --------------------------------------------------------
    def publish(self, post_id: int, only=None, on_event=None) -> dict[str, PostResult]:
        emit = on_event or (lambda event: None)
        post = self.db.get_post(post_id)
        image = (post or {}).get("image_path") or None
        targets = [t for t in self.db.list_targets(post_id, OPEN_STATUSES) if not only or t.platform in only]
        results: dict[str, PostResult] = {}
        ready = []
        for target in targets:
            adapter = self.adapters.get(target.platform)
            payload = PostPayload(text=self._final_text(target), image_path=image, title=target.title,
                                  extra=dict(target.extra))
            problems = self._problems(target, adapter, payload, image)
            if problems:
                results[target.platform] = self._blocked(target, problems, emit)
            else:
                ready.append((target, adapter, payload))

        if ready:
            with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
                futures = {pool.submit(self._run_target, t, a, p, emit): t for t, a, p in ready}
                for future in as_completed(futures):
                    results[futures[future].platform] = future.result()

        status = self._update_post_status(post_id)
        emit({"type": "done", "post_status": status})
        return results

    # ---- internals ---------------------------------------------------------
    @staticmethod
    def _final_text(target) -> str:
        return target.text if target.platform == "reddit" else compose_text(target.platform, target.text, target.hashtags)

    def _problems(self, target, adapter, payload, image) -> list[str]:
        if adapter is None:
            return ["Not configured. Add this account's credentials in Settings."]
        problems = list(adapter.validate(payload))
        if image:
            problems += self.image_service.check(target.platform, image)
            if adapter.needs_public_image and self.image_host is None:
                problems.append("Image host is not configured. Add its API key in Settings.")
        return problems

    def _blocked(self, target, problems: list[str], emit) -> PostResult:
        message = " ".join(problems)
        self.db.add_result(target.id, False, error_code="VALIDATION", error_message=message)
        self.db.set_target_status(target.id, "failed")
        emit({"type": "status", "platform": target.platform, "status": "blocked", "message": message})
        return PostResult(target.platform, False, error_code="VALIDATION", error_message=message)

    def _run_target(self, target, adapter, payload: PostPayload, emit) -> PostResult:
        fresh = self.db.get_target(target.id)
        if fresh and fresh.status == "posted":  # idempotency: never post the same target twice
            last = self.db.last_result(target.id) or {}
            return PostResult(target.platform, True, post_id=last.get("remote_id"), url=last.get("url"))
        self.db.set_target_status(target.id, "posting")
        emit({"type": "status", "platform": target.platform, "status": "posting"})

        result, attempts = None, 0
        for attempt in range(1 + self.retries):
            attempts += 1
            result = self._attempt(target.platform, adapter, payload)
            if result.ok or not result.retryable or result.needs_check:
                break
            if attempt < self.retries:
                self._sleep(min(2 ** (attempt + 1), 60))

        status = "posted" if result.ok else ("needs_check" if result.needs_check else "failed")
        self.db.add_result(target.id, result.ok, result.post_id, result.url, result.error_code, result.error_message)
        self.db.set_target_status(target.id, status, attempts)
        emit({"type": "status", "platform": target.platform, "status": status, "url": result.url,
              "message": result.error_message, "attempts": attempts})
        return result

    def _attempt(self, platform: str, adapter, base: PostPayload) -> PostResult:
        payload = dataclasses.replace(base)
        prepared = None
        try:
            if base.image_path:
                prepared = self.image_service.prepare(platform, base.image_path)
                if adapter.needs_public_image:
                    payload.image_url = self.image_host.upload(prepared)
                    payload.image_path = None
                else:
                    payload.image_path = prepared
            return adapter.post(payload)
        except ImageHostError as exc:
            return PostResult(platform, False, error_code="NETWORK" if exc.retryable else "VALIDATION",
                              error_message=str(exc), retryable=exc.retryable)
        except (ValueError, OSError) as exc:
            log.warning("Image handling failed for %s: %s", platform, exc)
            return PostResult(platform, False, error_code="VALIDATION", error_message="The image could not be prepared.")
        except Exception:
            log.exception("Unexpected error posting to %s", platform)
            return PostResult(platform, False, error_code="UNKNOWN",
                              error_message="Unexpected error. Details are in the log file.")
        finally:
            self.image_service.discard(prepared)

    def _update_post_status(self, post_id: int) -> str:
        statuses = [t.status for t in self.db.list_targets(post_id)]
        if statuses and all(s == "posted" for s in statuses):
            status = "posted"
        elif "posted" in statuses:
            status = "partial"
        else:
            status = "failed"
        self.db.set_post_status(post_id, status)
        return status
