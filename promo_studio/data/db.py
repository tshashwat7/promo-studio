"""SQLite storage. One short-lived connection per call keeps it thread-safe."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from promo_studio.data.models import AppProfile, Target

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
  pitch TEXT DEFAULT '', description TEXT DEFAULT '', audience TEXT DEFAULT '',
  features TEXT DEFAULT '[]', tone TEXT DEFAULT '', store_links TEXT DEFAULT '{}',
  seed_keywords TEXT DEFAULT '[]', banned_phrases TEXT DEFAULT '[]',
  default_hashtags TEXT DEFAULT '[]', default_image_path TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, angle TEXT, base_text TEXT,
  image_path TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'draft'
);
CREATE TABLE IF NOT EXISTS post_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL, platform TEXT NOT NULL,
  text TEXT, hashtags TEXT DEFAULT '[]', title TEXT, extra TEXT DEFAULT '{}',
  scheduled_at TEXT, status TEXT DEFAULT 'draft', attempts INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY AUTOINCREMENT, target_id INTEGER NOT NULL, ok INTEGER NOT NULL,
  remote_id TEXT, url TEXT, error_code TEXT, error_message TEXT,
  attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS aso_sets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, store TEXT, field TEXT,
  value TEXT, char_count INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, chosen INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS subreddit_rules (
  subreddit TEXT PRIMARY KEY, rules_note TEXT DEFAULT '', promo_allowed_days TEXT DEFAULT '',
  last_posted_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- settings -------------------------------------------------------
    def get_setting(self, key: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    # ---- profiles -------------------------------------------------------
    def list_profiles(self) -> list[AppProfile]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM app_profiles ORDER BY name COLLATE NOCASE").fetchall()
        return [AppProfile.from_row(r) for r in rows]

    def get_profile(self, profile_id: int) -> AppProfile | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM app_profiles WHERE id=?", (profile_id,)).fetchone()
        return AppProfile.from_row(row) if row else None

    def save_profile(self, p: AppProfile) -> int:
        values = (
            p.name, p.pitch, p.description, p.audience, json.dumps(p.features), p.tone,
            json.dumps(p.store_links), json.dumps(p.seed_keywords), json.dumps(p.banned_phrases),
            json.dumps(p.default_hashtags), p.default_image_path,
        )
        with self._conn() as c:
            if p.id is None:
                cur = c.execute(
                    "INSERT INTO app_profiles(name,pitch,description,audience,features,tone,"
                    "store_links,seed_keywords,banned_phrases,default_hashtags,default_image_path) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)", values)
                p.id = cur.lastrowid
            else:
                c.execute(
                    "UPDATE app_profiles SET name=?,pitch=?,description=?,audience=?,features=?,tone=?,"
                    "store_links=?,seed_keywords=?,banned_phrases=?,default_hashtags=?,default_image_path=? "
                    "WHERE id=?", values + (p.id,))
        return p.id

    def delete_profile(self, profile_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM app_profiles WHERE id=?", (profile_id,))

    # ---- posts, targets, results ---------------------------------------
    def create_post(self, profile_id, angle: str, base_text: str, image_path: str | None) -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO posts(profile_id, angle, base_text, image_path) VALUES(?,?,?,?)",
                            (profile_id, angle, base_text, image_path))
            return cur.lastrowid

    def get_post(self, post_id: int) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        return dict(row) if row else None

    def set_post_status(self, post_id: int, status: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE posts SET status=? WHERE id=?", (status, post_id))

    def add_target(self, post_id: int, platform: str, text: str, hashtags=(), title=None, extra=None,
                   scheduled_at=None, status: str = "draft") -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO post_targets(post_id, platform, text, hashtags, title, extra, scheduled_at, status) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (post_id, platform, text, json.dumps(list(hashtags)), title, json.dumps(extra or {}),
                 scheduled_at, status))
            return cur.lastrowid

    def get_target(self, target_id: int) -> Target | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM post_targets WHERE id=?", (target_id,)).fetchone()
        return Target.from_row(row) if row else None

    def list_targets(self, post_id: int, statuses=None) -> list[Target]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM post_targets WHERE post_id=? ORDER BY id", (post_id,)).fetchall()
        targets = [Target.from_row(r) for r in rows]
        return [t for t in targets if statuses is None or t.status in statuses]

    def set_target_status(self, target_id: int, status: str, attempts: int | None = None) -> None:
        with self._conn() as c:
            if attempts is None:
                c.execute("UPDATE post_targets SET status=? WHERE id=?", (status, target_id))
            else:
                c.execute("UPDATE post_targets SET status=?, attempts=? WHERE id=?", (status, attempts, target_id))

    def add_result(self, target_id: int, ok: bool, remote_id=None, url=None, error_code=None,
                   error_message=None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO results(target_id, ok, remote_id, url, error_code, error_message) VALUES(?,?,?,?,?,?)",
                (target_id, int(ok), remote_id, url, error_code, error_message))
            return cur.lastrowid

    def last_result(self, target_id: int) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM results WHERE target_id=? ORDER BY id DESC LIMIT 1",
                            (target_id,)).fetchone()
        return dict(row) if row else None

    def mark_stale_posting(self) -> int:
        """Targets still 'posting' at startup were interrupted: flag them instead of retrying blindly."""
        with self._conn() as c:
            cur = c.execute("UPDATE post_targets SET status='needs_check' WHERE status='posting'")
            return cur.rowcount
