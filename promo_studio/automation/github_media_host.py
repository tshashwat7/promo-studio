"""Upload MP4 Reels to a public GitHub repository's Releases for Instagram Graph API."""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)

DEFAULT_REELS_REPO = "tshashwat7/siddhanta-reels-media"


class GitHubReleaseMediaHost:
    """Uploads video assets to GitHub Releases and returns a public download URL."""

    API_ROOT = "https://api.github.com"

    def __init__(self, token: str, repo: str = DEFAULT_REELS_REPO, http=requests):
        self.token = token.strip()
        self.repo = repo.strip().strip("/")
        self.http = http

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get_or_create_release(self, tag: str, name: str) -> dict:
        tag_url = f"{self.API_ROOT}/repos/{self.repo}/releases/tags/{tag}"
        res = self.http.get(tag_url, headers=self._headers, timeout=30)
        if res.status_code == 200:
            return res.json()
        if res.status_code != 404:
            res.raise_for_status()

        create_url = f"{self.API_ROOT}/repos/{self.repo}/releases"
        res = self.http.post(
            create_url,
            headers=self._headers,
            json={
                "tag_name": tag,
                "name": name,
                "body": f"Automated daily Siddhanta Reel media for {tag}.",
                "draft": False,
                "prerelease": False,
            },
            timeout=30,
        )
        res.raise_for_status()
        return res.json()

    def _delete_existing_asset(self, release: dict, asset_name: str) -> None:
        for asset in release.get("assets", []):
            if asset.get("name") == asset_name:
                del_url = f"{self.API_ROOT}/repos/{self.repo}/releases/assets/{asset['id']}"
                res = self.http.delete(del_url, headers=self._headers, timeout=30)
                if res.status_code not in (200, 204, 404):
                    res.raise_for_status()

    def cleanup_old_releases(self, keep_days: int = 14) -> int:
        """Delete automated reel-* releases older than `keep_days` to keep storage tidy."""
        if keep_days <= 0:
            return 0
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=keep_days)
        url = f"{self.API_ROOT}/repos/{self.repo}/releases"
        res = self.http.get(url, headers=self._headers, params={"per_page": 50}, timeout=30)
        if res.status_code != 200:
            return 0
        deleted = 0
        for rel in res.json():
            tag = rel.get("tag_name", "")
            if not tag.startswith("reel-"):
                continue
            created = rel.get("created_at", "")
            try:
                created_dt = dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                continue
            if created_dt < cutoff:
                del_res = self.http.delete(
                    f"{self.API_ROOT}/repos/{self.repo}/releases/{rel['id']}",
                    headers=self._headers,
                    timeout=30,
                )
                if del_res.status_code in (200, 204):
                    deleted += 1
                    self.http.delete(
                        f"{self.API_ROOT}/repos/{self.repo}/git/refs/tags/{tag}",
                        headers=self._headers,
                        timeout=30,
                    )
        return deleted

    def upload_video(
        self,
        file_path: str | Path,
        tag: str,
        asset_name: str | None = None,
        cleanup_days: int = 14,
    ) -> str:
        """Upload an MP4 file to a GitHub Release and return its public download URL."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

        name = asset_name or path.name
        release = self._get_or_create_release(tag=tag, name=f"Siddhanta Reel {tag}")
        self._delete_existing_asset(release, name)

        upload_template = release["upload_url"]
        upload_url = upload_template.split("{", 1)[0]

        upload_headers = {
            **self._headers,
            "Content-Type": "video/mp4",
        }
        with path.open("rb") as fh:
            res = self.http.post(
                upload_url,
                headers=upload_headers,
                params={"name": name},
                data=fh.read(),
                timeout=180,
            )
        res.raise_for_status()
        download_url = res.json()["browser_download_url"]

        # Verify public reachability before handing URL to Instagram Graph API.
        check = self.http.head(download_url, allow_redirects=True, timeout=30)
        if check.status_code >= 400:
            raise RuntimeError(f"Uploaded Reel URL not publicly reachable ({check.status_code}): {download_url}")

        try:
            removed = self.cleanup_old_releases(keep_days=cleanup_days)
            if removed:
                log.info("Cleaned up %d old Reel release(s) from %s", removed, self.repo)
        except Exception as exc:
            log.warning("Old Reel release cleanup skipped: %s", exc)

        return download_url
