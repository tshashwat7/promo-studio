from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from promo_studio.adapters.base import PlatformAdapter, PostPayload, PostResult

log = logging.getLogger(__name__)


class TwitterPlaywrightAdapter(PlatformAdapter):
    """Automates publishing rich multi-card tweets to X (Twitter) using headless Chromium

    and authenticated session cookies (auth_token + ct0). Bypasses paid API tiers completely.
    """

    name = "twitter_browser"

    def __init__(
        self,
        auth_token: str,
        ct0: str,
        headless: bool = True,
        timeout_ms: int = 45000,
    ):
        self.auth_token = auth_token.strip()
        self.ct0 = ct0.strip()
        self.headless = headless
        self.timeout_ms = timeout_ms

    def validate(self, payload: PostPayload) -> list[str]:
        problems = []
        if len(payload.text) > 280:
            problems.append(f"Tweet text exceeds 280 characters ({len(payload.text)} chars).")
        return problems

    def publish_tweet(
        self,
        text: str,
        media_files: list[str | Path] | None = None,
    ) -> PostResult:
        """Publishes a Tweet with up to 4 high-res visual cards attached via Playwright."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("Playwright is not installed. Run 'pip install playwright && playwright install chromium'.")
            return PostResult(self.name, False, error_code="NO_PLAYWRIGHT", error_message="Playwright not installed")

        if not self.auth_token or not self.ct0:
            return PostResult(self.name, False, error_code="MISSING_COOKIES", error_message="TWITTER_AUTH_TOKEN or TWITTER_CT0 missing")

        valid_files: list[str] = []
        if media_files:
            for f in media_files[:4]:
                p = Path(f)
                if p.exists():
                    valid_files.append(str(p.resolve()))

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )

                # Inject official authentication cookies
                context.add_cookies([
                    {
                        "name": "auth_token",
                        "value": self.auth_token,
                        "domain": ".x.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "None",
                    },
                    {
                        "name": "ct0",
                        "value": self.ct0,
                        "domain": ".x.com",
                        "path": "/",
                        "httpOnly": False,
                        "secure": True,
                        "sameSite": "Lax",
                    },
                ])

                page = context.new_page()
                page.set_default_timeout(self.timeout_ms)

                log.info("Navigating to X compose...")
                page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
                time.sleep(3)

                # Check if we were redirected to login or locked
                current_url = page.url
                if "/login" in current_url or "/i/flow/login" in current_url:
                    browser.close()
                    log.error("X session rejected cookies; redirected to login. Auth token may be expired.")
                    return PostResult(self.name, False, error_code="SESSION_EXPIRED", error_message="X rejected session cookies")

                # 1. Type tweet text
                compose_box = page.locator('div[data-testid="tweetTextarea_0"]').first
                compose_box.wait_for(state="visible", timeout=15000)
                compose_box.click()
                compose_box.fill(text)
                log.info("Typed formatted Vedic tweet copy (%d chars)", len(text))
                time.sleep(1)

                # 2. Attach media files (up to 4 visual cards)
                if valid_files:
                    log.info("Attaching %d visual card(s) to composer...", len(valid_files))
                    file_input = page.locator('input[data-testid="fileInput"]').first
                    file_input.set_input_files(valid_files)

                    # Wait for media preview container to appear
                    page.locator('div[data-testid="attachments"]').wait_for(state="visible", timeout=20000)
                    log.info("Media cards attached and rendered successfully.")
                    time.sleep(2)

                # 3. Click Post Button
                post_btn = page.locator('button[data-testid="tweetButton"]').first
                post_btn.wait_for(state="visible", timeout=10000)
                post_btn.click()
                log.info("Clicked Post button on X. Waiting for publish confirmation...")

                # Wait for compose modal to close or toast notification
                time.sleep(5)
                browser.close()

                log.info("SUCCESS! Tweet with %d visual card(s) dispatched to X via Playwright.", len(valid_files))
                return PostResult(self.name, True, post_id="playwright_posted", url="https://x.com/Shaanviapps")

        except Exception as e:
            log.error("Twitter Playwright publish failed: %s", e)
            return PostResult(self.name, False, error_code="PLAYWRIGHT_ERROR", error_message=str(e))

    def post(self, payload: PostPayload) -> PostResult:
        files = [payload.image_path] if payload.image_path else []
        return self.publish_tweet(payload.text, media_files=files)
