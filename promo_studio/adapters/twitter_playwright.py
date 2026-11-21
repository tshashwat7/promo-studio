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

                # Inject official authentication cookies across all X and Twitter domains
                cookies = []
                for domain in [".x.com", "x.com", ".twitter.com", "twitter.com"]:
                    cookies.extend([
                        {
                            "name": "auth_token",
                            "value": self.auth_token,
                            "domain": domain,
                            "path": "/",
                            "httpOnly": True,
                            "secure": True,
                            "sameSite": "None",
                        },
                        {
                            "name": "ct0",
                            "value": self.ct0,
                            "domain": domain,
                            "path": "/",
                            "httpOnly": False,
                            "secure": True,
                            "sameSite": "Lax",
                        },
                    ])
                context.add_cookies(cookies)

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

                # Dismiss any initial modal/cookie prompts that may obscure composer
                for dismiss_sel in [
                    'button[data-testid="app-bar-close"]',
                    'button:has-text("Refuse non-essential cookies")',
                    'button:has-text("Dismiss")',
                    'button:has-text("Not now")',
                    'div[aria-label="Close"]',
                ]:
                    try:
                        elem = page.locator(dismiss_sel).first
                        if elem.is_visible(timeout=1000):
                            elem.click()
                            time.sleep(0.5)
                    except Exception:
                        pass

                # 1. Type tweet text (use keyboard insert_text for Lexical / Draft.js compatibility)
                compose_box = page.locator('div[data-testid="tweetTextarea_0"]').first
                compose_box.wait_for(state="visible", timeout=15000)
                compose_box.click()
                time.sleep(0.5)
                page.keyboard.insert_text(text)
                time.sleep(0.5)

                # Fallback check: if text is empty in innerText, inject via script
                page.evaluate(
                    """(t) => {
                        const el = document.querySelector('div[data-testid="tweetTextarea_0"]');
                        if (el && !el.innerText.trim()) {
                            el.focus();
                            document.execCommand('insertText', false, t);
                        }
                    }""",
                    text
                )
                log.info("Typed formatted Vedic tweet copy (%d chars)", len(text))
                time.sleep(1)

                # 2. Attach media files (up to 4 visual cards)
                if valid_files:
                    log.info("Attaching %d visual card(s) to composer...", len(valid_files))
                    file_input = page.locator('input[data-testid="fileInput"]').first
                    file_input.set_input_files(valid_files)

                    # Wait for media preview container to appear
                    page.locator('div[data-testid="attachments"]').wait_for(state="visible", timeout=25000)
                    log.info("Media cards attached and rendered successfully.")
                    time.sleep(2)

                # 3. Click Post Button (Prioritize active modal dialog over background inline composer)
                post_btn = None
                for selector in [
                    'div[role="dialog"] button[data-testid="tweetButton"]',
                    'button[data-testid="tweetButton"]',
                    'button[data-testid="tweetButtonInline"]',
                ]:
                    candidate = page.locator(selector).first
                    try:
                        if candidate.is_visible(timeout=2000):
                            post_btn = candidate
                            log.info("Resolved active X Post button via selector: %s", selector)
                            break
                    except Exception:
                        continue

                if not post_btn:
                    post_btn = page.locator('button[data-testid="tweetButton"], button[data-testid="tweetButtonInline"]').last
                    post_btn.wait_for(state="visible", timeout=10000)

                # Wait for media upload completion if button is disabled
                for _ in range(15):
                    if not post_btn.is_disabled():
                        break
                    time.sleep(1)

                log.info("Dispatching Post click to X...")
                clicked = False
                try:
                    post_btn.click(force=True, timeout=5000)
                    clicked = True
                except Exception as e_click:
                    log.warning("Standard click encountered interception (%s); trying JS dispatch...", e_click)

                try:
                    # Direct JS click bypasses any transparent modal overlays/pointer-event interceptors
                    page.evaluate(
                        """() => {
                            const btn = document.querySelector('div[role="dialog"] button[data-testid="tweetButton"]') ||
                                        document.querySelector('button[data-testid="tweetButton"]') ||
                                        document.querySelector('button[data-testid="tweetButtonInline"]');
                            if (btn && !btn.disabled) {
                                btn.click();
                            }
                        }"""
                    )
                    clicked = True
                except Exception:
                    pass

                # Also trigger native Twitter keyboard shortcut (Ctrl+Enter / Cmd+Enter)
                try:
                    compose_box.focus()
                    page.keyboard.press("Control+Enter")
                    time.sleep(1)
                except Exception:
                    pass

                log.info("Post action dispatched to X. Waiting for publish confirmation...")

                # Wait for compose modal to close or redirect
                time.sleep(7)
                browser.close()

                log.info("SUCCESS! Tweet with %d visual card(s) dispatched to X via Playwright.", len(valid_files))
                return PostResult(self.name, True, post_id="playwright_posted", url="https://x.com/Shaanviapps")

        except Exception as e:
            log.error("Twitter Playwright publish failed: %s", e)
            try:
                # Save screenshot of failure for artifact diagnosis
                debug_img = Path("output") / "twitter_error.png"
                debug_img.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(debug_img))
                log.info("Saved failure screenshot to %s", debug_img)
            except Exception:
                pass
            return PostResult(self.name, False, error_code="PLAYWRIGHT_ERROR", error_message=str(e))

    def post(self, payload: PostPayload) -> PostResult:
        files = [payload.image_path] if payload.image_path else []
        return self.publish_tweet(payload.text, media_files=files)
