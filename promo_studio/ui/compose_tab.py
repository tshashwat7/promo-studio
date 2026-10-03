from __future__ import annotations

import json
import logging
import os
import queue
import threading
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from promo_studio.ai.base import AIError
from promo_studio.ai.prompts import ANGLES
from promo_studio.core.draft_service import DraftError
from promo_studio.ui.preview_dialog import PreviewDialog
from promo_studio.ui.results_strip import ResultsStrip
from promo_studio.core.validators import (
    PLATFORMS, char_count, compose_text, counter_state, limit_for, normalize_hashtags, validate_post)

log = logging.getLogger(__name__)
POSTABLE = ('facebook', 'instagram')  # X arrives in phase 3; Reddit stays copy-only
LABELS = {"facebook": "Facebook", "instagram": "Instagram", "x": "X", "reddit": "Reddit"}
COLORS = {"ok": ("gray35", "gray70"), "warn": "#d98e04", "over": "#d64545"}


class PlatformCard(ctk.CTkFrame):
    """One editable draft per platform, with variant switcher, live counter and checks."""

    def __init__(self, master, platform: str, on_shorten=None):
        super().__init__(master)
        self.platform, self.blocks, self.index = platform, [], 0
        self.on_shorten = on_shorten
        self.banned: list[str] = []
        self.has_image: bool | None = None
        self.columnconfigure(0, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))
        self.enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(head, text=LABELS[platform], variable=self.enabled,
                        font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.next_btn = ctk.CTkButton(head, text=">", width=28, command=lambda: self._step(1))
        self.next_btn.pack(side="right")
        self.pos_label = ctk.CTkLabel(head, text="0 / 0", width=48)
        self.pos_label.pack(side="right")
        self.prev_btn = ctk.CTkButton(head, text="<", width=28, command=lambda: self._step(-1))
        self.prev_btn.pack(side="right")

        row = 1
        self.title_entry = None
        if platform == "reddit":
            self.title_entry = ctk.CTkEntry(self, placeholder_text="Title")
            self.title_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            self.title_entry.bind("<KeyRelease>", self.refresh)
            row += 1
        self.textbox = ctk.CTkTextbox(self, height=110, wrap="word")
        self.textbox.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
        self.textbox.bind("<KeyRelease>", self.refresh)
        row += 1
        self.tags_entry = None
        if platform != "reddit":
            self.tags_entry = ctk.CTkEntry(self, placeholder_text="hashtags, comma separated (no #)")
            self.tags_entry.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            self.tags_entry.bind("<KeyRelease>", self.refresh)
            row += 1
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=row, column=0, sticky="ew", padx=10, pady=(2, 2))
        self.counter = ctk.CTkLabel(foot, text="")
        self.counter.pack(side="left")
        ctk.CTkButton(foot, text="Copy", width=60, command=self.copy).pack(side="right")
        ctk.CTkButton(foot, text="Shorten", width=70, fg_color="gray40",
                      command=lambda: self.on_shorten and self.on_shorten(self)).pack(side="right", padx=6)
        self.problems = ctk.CTkLabel(self, text="", justify="left", anchor="w", wraplength=420,
                                     text_color=COLORS["over"])
        self.problems.grid(row=row + 1, column=0, sticky="ew", padx=10, pady=(0, 8))
        self._update_nav()
        self.refresh()

    # ---- data -----------------------------------------------------------
    def load_variants(self, variants: list[dict]) -> None:
        self.blocks = [v[self.platform] for v in variants if self.platform in v]
        self.index = 0
        self._show()

    def set_context(self, banned: list[str], has_image: bool | None) -> None:
        self.banned, self.has_image = banned, has_image
        self.refresh()

    def parts(self) -> tuple[str, str, list[str]]:
        title = self.title_entry.get().strip() if self.title_entry else ""
        text = self.textbox.get("1.0", "end").strip()
        raw = self.tags_entry.get().replace("#", "") if self.tags_entry else ""
        tags = normalize_hashtags(raw.split(","), 30) if raw.strip() else []
        return title, text, tags

    def final_text(self) -> str:
        title, text, tags = self.parts()
        body = compose_text(self.platform, text, tags)
        return f"{title}\n\n{body}" if title else body

    # ---- ui -------------------------------------------------------------
    def _step(self, delta: int) -> None:
        if self.blocks:
            self.index = (self.index + delta) % len(self.blocks)
            self._show()

    def _show(self) -> None:
        block = self.blocks[self.index] if self.blocks else None
        self.textbox.delete("1.0", "end")
        if block:
            self.textbox.insert("1.0", block["text"])
            if self.title_entry:
                self.title_entry.delete(0, "end")
                self.title_entry.insert(0, block.get("title", ""))
            if self.tags_entry:
                self.tags_entry.delete(0, "end")
                self.tags_entry.insert(0, ", ".join(block["hashtags"]))
        self._update_nav()
        self.refresh()

    def _update_nav(self) -> None:
        total = len(self.blocks)
        self.pos_label.configure(text=f"{self.index + 1 if total else 0} / {total}")
        state = "normal" if total > 1 else "disabled"
        self.prev_btn.configure(state=state)
        self.next_btn.configure(state=state)

    def refresh(self, _event=None) -> None:
        title, text, tags = self.parts()
        used, limit = char_count(self.platform, text, tags), limit_for(self.platform)
        label = f"{used} characters" if limit > 5000 else f"{used} / {limit}"
        self.counter.configure(text=label, text_color=COLORS[counter_state(used, limit)])
        problems = validate_post(self.platform, text, tags, title=title, banned=self.banned,
                                 has_image=self.has_image) if text or title else []
        self.problems.configure(text="\n".join(problems))

    def copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.final_text())

    def set_text(self, text: str) -> None:
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self.refresh()

    def state(self) -> dict:
        title = self.title_entry.get() if self.title_entry else ""
        tags = self.tags_entry.get() if self.tags_entry else ""
        return {"enabled": self.enabled.get(), "title": title, "tags": tags,
                "text": self.textbox.get("1.0", "end").strip()}

    def apply_state(self, data: dict) -> None:
        self.enabled.set(bool(data.get("enabled", True)))
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", data.get("text", ""))
        if self.title_entry:
            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, data.get("title", ""))
        if self.tags_entry:
            self.tags_entry.delete(0, "end")
            self.tags_entry.insert(0, data.get("tags", ""))
        self.refresh()

    def clear(self) -> None:
        self.blocks, self.index = [], 0
        self.apply_state({})
        self._update_nav()


DRAFT_KEY = "draft.compose"


class ComposeTab(ctk.CTkFrame):
    def __init__(self, master, ctx):
        super().__init__(master, fg_color="transparent")
        self.ctx, self.profiles, self.image_path = ctx, [], None
        self.results: queue.Queue = queue.Queue()
        self._gen_id, self._busy, self._last_saved = 0, False, ""
        self._posting, self.current_post_id = False, None
        self.columnconfigure(0, weight=2, uniform="c")
        self.columnconfigure(1, weight=3, uniform="c")
        self.rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(self)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(bar, text="App").pack(side="left", padx=(10, 4))
        self.profile_menu = ctk.CTkOptionMenu(bar, values=["(no profiles)"], command=self._on_profile, width=170)
        self.profile_menu.pack(side="left", padx=4)
        ctk.CTkLabel(bar, text="Angle").pack(side="left", padx=(14, 4))
        self.angle_menu = ctk.CTkOptionMenu(bar, values=[a.replace("_", " ") for a in ANGLES], width=170)
        self.angle_menu.pack(side="left", padx=4)
        ctk.CTkLabel(bar, text="Variants").pack(side="left", padx=(14, 4))
        self.variants_menu = ctk.CTkOptionMenu(bar, values=["1", "2", "3", "4", "5"], width=60)
        self.variants_menu.pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Clear all", width=80, fg_color="gray40", command=self.clear_all).pack(side="right", padx=8)
        ctk.CTkButton(bar, text="Save draft", width=90, fg_color="gray40", command=self.save_draft).pack(side="right")

        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="Base idea (optional)", anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.base_text = ctk.CTkTextbox(left, wrap="word")
        self.base_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        ctk.CTkLabel(left, text="Note to the AI (optional)", anchor="w").grid(row=2, column=0, sticky="ew", padx=10)
        self.note = ctk.CTkEntry(left, placeholder_text="e.g. mention the new sleep sounds")
        self.note.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        img_row = ctk.CTkFrame(left, fg_color="transparent")
        img_row.grid(row=4, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(img_row, text="Choose image", width=110, command=self._choose_image).pack(side="left")
        ctk.CTkButton(img_row, text="Clear", width=60, command=self._clear_image,
                      fg_color="gray40").pack(side="left", padx=6)
        self.image_label = ctk.CTkLabel(left, text="No image", height=110)
        self.image_label.grid(row=5, column=0, padx=10, pady=4)
        self.generate_btn = ctk.CTkButton(left, text="Generate with AI", command=self.generate, height=36)
        self.generate_btn.grid(row=6, column=0, sticky="ew", padx=10, pady=(4, 4))
        self.status = ctk.CTkLabel(left, text="", wraplength=380, justify="left", anchor="w")
        self.status.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 10))

        right = ctk.CTkScrollableFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 6))
        right.columnconfigure(0, weight=1)
        self.cards = {}
        for i, platform in enumerate(PLATFORMS):
            card = PlatformCard(right, platform, on_shorten=self._shorten)
            card.grid(row=i, column=0, sticky="ew", pady=4)
            self.cards[platform] = card
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))
        bottom.columnconfigure(1, weight=1)
        btns = ctk.CTkFrame(bottom, fg_color="transparent")
        btns.grid(row=0, column=0, sticky="n", padx=8, pady=8)
        ctk.CTkButton(btns, text="Preview all", width=120, fg_color="gray40", command=self.preview).pack(pady=2)
        self.post_btn = ctk.CTkButton(btns, text="Post now", width=120, command=self.post_now)
        self.post_btn.pack(pady=2)
        self.strip = ResultsStrip(bottom, on_retry=self._retry)
        self.strip.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        top = self.winfo_toplevel()
        top.bind("<Control-Return>", lambda e: self.generate())
        top.bind("<Control-s>", lambda e: self.save_draft())
        top.bind("<Control-Shift-Return>", lambda e: self.post_now())
        self.variants_menu.set(str(self.ctx.settings.get_int("ai.variants", 3)))
        self.refresh_profiles()
        self._restore_draft()
        self.after(100, self._poll)
        self.after(30_000, self._autosave_tick)

    # ---- profiles / image -----------------------------------------------
    def refresh_profiles(self) -> None:
        current = self.profile_menu.get()
        self.profiles = self.ctx.db.list_profiles()
        names = [p.name for p in self.profiles] or ["(no profiles)"]
        self.profile_menu.configure(values=names)
        self.profile_menu.set(current if current in names else names[0])
        self._on_profile()

    def current_profile(self):
        name = self.profile_menu.get()
        return next((p for p in self.profiles if p.name == name), None)

    def _on_profile(self, _value=None) -> None:
        profile = self.current_profile()
        if profile and profile.default_image_path and not self.image_path:
            self._set_image(profile.default_image_path)
        self._sync_cards()

    def _sync_cards(self) -> None:
        profile = self.current_profile()
        banned = profile.banned_phrases if profile else []
        for card in self.cards.values():
            card.set_context(banned, bool(self.image_path))

    def _choose_image(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            self._set_image(path)

    def _set_image(self, path: str) -> bool:
        try:
            img = Image.open(path)
            img.load()
        except Exception:
            log.warning("Could not open image %s", path, exc_info=True)
            self.status.configure(text="That file could not be opened as an image. Try a PNG or JPG.")
            return False
        self.image_path = path
        w, h = img.size
        scale = min(150 / w, 110 / h)
        self._thumb = ctk.CTkImage(light_image=img, dark_image=img, size=(int(w * scale), int(h * scale)))
        self.image_label.configure(image=self._thumb, text="")
        self._sync_cards()
        return True

    def _clear_image(self) -> None:
        self.image_path = None
        self.image_label.configure(image=None, text="No image")
        self._sync_cards()

    # ---- background work ---------------------------------------------------
    def generate(self) -> None:
        if self._busy:  # the button doubles as Cancel while a request is running
            self.cancel()
            return
        profile = self.current_profile()
        if not profile:
            self.status.configure(text="Create an app profile first (Profiles tab).")
            return
        angle = self.angle_menu.get().replace(" ", "_")
        base = self.base_text.get("1.0", "end").strip()
        note, n = self.note.get(), int(self.variants_menu.get())
        self._gen_id += 1
        gid = self._gen_id
        self._set_busy(True)
        self.status.configure(text="Asking the AI for drafts... (click Cancel to stop waiting)")

        def work():
            try:
                svc = self.ctx.make_draft_service()
                self.results.put(("draft", gid, "ok", svc.generate(profile, angle, base, note, n)))
            except (DraftError, AIError) as exc:
                self.results.put(("draft", gid, "err", str(exc)))
            except Exception:
                log.exception("Unexpected error while drafting")
                self.results.put(("draft", gid, "err", "Unexpected error. Details are in the log file."))

        threading.Thread(target=work, daemon=True).start()

    def cancel(self) -> None:
        self._gen_id += 1  # any late reply carries an old id and is ignored
        self._set_busy(False)
        self.status.configure(text="Cancelled. Your current cards were not changed.")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.generate_btn.configure(text="Cancel" if busy else "Generate with AI",
                                    fg_color=("#b23b3b" if busy else ("#3a7ebf", "#1f538d")))

    def _shorten(self, card: PlatformCard) -> None:
        title, text, tags = card.parts()
        if not text:
            return
        used, limit = char_count(card.platform, text, tags), limit_for(card.platform)
        if used <= limit and limit > 5000:
            self.status.configure(text=f"{LABELS[card.platform]} has no practical length problem.")
            return
        if used <= limit:
            self.status.configure(text=f"{LABELS[card.platform]} already fits ({used}/{limit}).")
            return
        overhead = used - char_count(card.platform, text, ())
        self.status.configure(text=f"Shortening the {LABELS[card.platform]} text...")

        def work():
            try:
                svc = self.ctx.make_draft_service()
                self.results.put(("shorten", card, "ok", svc.shorten(card.platform, text, limit - overhead)))
            except (DraftError, AIError) as exc:
                self.results.put(("shorten", card, "err", str(exc)))
            except Exception:
                log.exception("Unexpected error while shortening")
                self.results.put(("shorten", card, "err", "Unexpected error. Details are in the log file."))

        threading.Thread(target=work, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, ref, status, payload = self.results.get_nowait()
                if kind == "draft":
                    if ref != self._gen_id:
                        continue  # cancelled or superseded
                    self._set_busy(False)
                    if status == "ok":
                        for card in self.cards.values():
                            card.load_variants(payload.variants)
                        msg = f"Got {len(payload.variants)} variant(s). Use < > on each card to browse."
                        self.status.configure(text=" ".join([msg] + payload.warnings))
                    else:
                        self.status.configure(text=payload)
                elif kind == "publish":
                    self._on_publish_event(payload)
                elif status == "ok":  # shorten
                    ref.set_text(payload)
                    self.status.configure(text=f"{LABELS[ref.platform]} text shortened. Please re-read it.")
                else:
                    self.status.configure(text=payload)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    # ---- preview and posting -----------------------------------------------
    def _drafts(self) -> tuple[list[dict], list[dict]]:
        """Returns (drafts to publish, preview entries) for the enabled, non-empty cards."""
        profile = self.current_profile()
        banned = profile.banned_phrases if profile else []
        drafts, entries = [], []
        for platform, card in self.cards.items():
            if not card.enabled.get():
                continue
            title, text, tags = card.parts()
            if not text and not title:
                continue
            problems = validate_post(platform, text, tags, title=title, banned=banned,
                                     has_image=bool(self.image_path))
            if platform in POSTABLE:
                drafts.append({"platform": platform, "text": text, "hashtags": tags, "title": title or None})
            else:
                problems = problems + ["Copy-only for now: use the Copy button and post it yourself."]
            entries.append({"label": LABELS[platform], "text": card.final_text(), "problems": problems})
        return drafts, entries

    def _instagram_preview_image(self, drafts: list[dict]) -> str | None:
        if not self.image_path or not any(d["platform"] == "instagram" for d in drafts):
            return None
        try:
            return self.ctx.make_image_service().prepare("instagram", self.image_path)
        except Exception:
            return None

    def preview(self) -> None:
        drafts, entries = self._drafts()
        if not entries:
            self.status.configure(text="Nothing to preview yet.")
            return
        PreviewDialog(self.winfo_toplevel(), entries, self._instagram_preview_image(drafts))

    def post_now(self) -> None:
        if self._posting:
            return
        profile = self.current_profile()
        if not profile:
            self.status.configure(text="Create an app profile first (Profiles tab).")
            return
        drafts, entries = self._drafts()
        if not drafts:
            self.status.configure(text="Nothing to post: enable Facebook or Instagram and add some text.")
            return
        PreviewDialog(self.winfo_toplevel(), entries, self._instagram_preview_image(drafts),
                      on_confirm=lambda: self._start_publish(profile, drafts))

    def _start_publish(self, profile, drafts: list[dict]) -> None:
        angle = self.angle_menu.get().replace(" ", "_")
        base = self.base_text.get("1.0", "end").strip()
        publisher = self.ctx.make_publisher()
        self.current_post_id = publisher.create_post(profile.id, angle, base, self.image_path, drafts)
        self.strip.reset()
        self._run_publish(publisher, None)

    def _retry(self, platform: str) -> None:
        if self.current_post_id and not self._posting:
            self._run_publish(self.ctx.make_publisher(), {platform})

    def _run_publish(self, publisher, only) -> None:
        self._posting = True
        self.post_btn.configure(state="disabled", text="Posting...")
        post_id = self.current_post_id

        def work():
            try:
                publisher.publish(post_id, only=only,
                                  on_event=lambda e: self.results.put(("publish", None, "event", e)))
            except Exception:
                log.exception("Publishing crashed")
                self.results.put(("publish", None, "event", {
                    "type": "done", "post_status": "failed",
                    "error": "Unexpected error. Details are in the log file."}))

        threading.Thread(target=work, daemon=True).start()

    def _on_publish_event(self, event: dict) -> None:
        if event["type"] == "status":
            self.strip.update_row(event)
            return
        self._posting = False
        self.post_btn.configure(state="normal", text="Post now")
        names = {"posted": "Everything was posted.",
                 "partial": "Some platforms did not post: see the list, use Retry.",
                 "failed": "Nothing was posted: see the list for the reason."}
        self.status.configure(text=event.get("error") or names.get(event["post_status"], ""))

    # ---- draft auto-save ---------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "profile": self.profile_menu.get(), "angle": self.angle_menu.get(),
            "variants": self.variants_menu.get(), "base": self.base_text.get("1.0", "end").strip(),
            "note": self.note.get(), "image": self.image_path or "",
            "cards": {p: c.state() for p, c in self.cards.items()},
        }

    @staticmethod
    def _is_blank(snap: dict) -> bool:
        return not (snap["base"] or snap["note"] or snap["image"]
                    or any(c["text"] or c["title"] for c in snap["cards"].values()))

    def save_draft(self, announce: bool = True) -> None:
        snap = self.snapshot()
        if self._is_blank(snap):
            if announce:
                self.status.configure(text="Nothing to save yet.")
            return
        raw = json.dumps(snap, ensure_ascii=False)
        if raw != self._last_saved:
            self.ctx.settings.set(DRAFT_KEY, raw)
            self._last_saved = raw
        if announce:
            self.status.configure(text="Draft saved.")

    def _autosave_tick(self) -> None:
        try:
            self.save_draft(announce=False)
        except Exception:
            log.exception("Auto-save failed")
        self.after(30_000, self._autosave_tick)

    def _restore_draft(self) -> None:
        raw = self.ctx.settings.get(DRAFT_KEY)
        if not raw:
            return
        try:
            snap = json.loads(raw)
            names = [p.name for p in self.profiles]
            if snap.get("profile") in names:
                self.profile_menu.set(snap["profile"])
            if snap.get("angle") in [a.replace("_", " ") for a in ANGLES]:
                self.angle_menu.set(snap["angle"])
            if snap.get("variants") in ("1", "2", "3", "4", "5"):
                self.variants_menu.set(snap["variants"])
            self.base_text.insert("1.0", snap.get("base", ""))
            self.note.insert(0, snap.get("note", ""))
            if snap.get("image") and os.path.exists(snap["image"]):
                self._set_image(snap["image"])
            for platform, data in (snap.get("cards") or {}).items():
                if platform in self.cards:
                    self.cards[platform].apply_state(data)
            self._last_saved = raw
            self.status.configure(text="Restored your last draft.")
        except (ValueError, TypeError, AttributeError):
            log.warning("Stored draft could not be restored", exc_info=True)
        self._sync_cards()

    def clear_all(self) -> None:
        self.base_text.delete("1.0", "end")
        self.note.delete(0, "end")
        self._clear_image()
        for card in self.cards.values():
            card.clear()
        self.ctx.settings.set(DRAFT_KEY, "")
        self._last_saved = ""
        self.status.configure(text="Cleared.")
