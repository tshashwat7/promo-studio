from __future__ import annotations

from tkinter import filedialog, messagebox

import logging
import sqlite3

import customtkinter as ctk

from promo_studio.core.textutil import format_links, parse_csv, parse_lines, parse_links
from promo_studio.data.models import AppProfile
from promo_studio.data.profile_io import export_profiles, import_profiles

log = logging.getLogger(__name__)


class ProfilesTab(ctk.CTkFrame):
    def __init__(self, master, ctx, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.ctx, self.on_change, self.current_id = ctx, on_change, None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, width=230)
        left.grid(row=0, column=0, sticky="ns", padx=6, pady=6)
        ctk.CTkButton(left, text="+ New profile", command=self.new_profile).pack(fill="x", padx=8, pady=8)
        self.list_frame = ctk.CTkScrollableFrame(left, width=200)
        self.list_frame.pack(fill="both", expand=True, padx=4, pady=4)
        io_row = ctk.CTkFrame(left, fg_color="transparent")
        io_row.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(io_row, text="Import", width=90, fg_color="gray40", command=self.import_json).pack(side="left", padx=2)
        ctk.CTkButton(io_row, text="Export", width=90, fg_color="gray40", command=self.export_json).pack(side="left", padx=2)

        form = ctk.CTkScrollableFrame(self)
        form.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        form.columnconfigure(1, weight=1)
        self.entries: dict[str, ctk.CTkEntry | ctk.CTkTextbox] = {}
        fields = [
            ("name", "App name", "entry"), ("pitch", "One-line pitch", "entry"),
            ("description", "Description", "text"), ("audience", "Target audience", "entry"),
            ("features", "Key features (one per line)", "text"), ("tone", "Tone (e.g. warm, concise)", "entry"),
            ("store_links", "Store links (name=url per line)", "text"),
            ("seed_keywords", "Seed keywords (comma separated)", "entry"),
            ("banned_phrases", "Banned phrases (comma separated)", "entry"),
            ("default_hashtags", "Default hashtags (comma separated)", "entry"),
            ("default_image_path", "Default image path", "entry"),
        ]
        for row, (key, label, kind) in enumerate(fields):
            ctk.CTkLabel(form, text=label, anchor="nw").grid(row=row, column=0, sticky="nw", padx=8, pady=6)
            widget = ctk.CTkEntry(form) if kind == "entry" else ctk.CTkTextbox(form, height=80, wrap="word")
            widget.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
            self.entries[key] = widget
        ctk.CTkButton(form, text="Browse...", width=80, command=self._browse).grid(
            row=len(fields) - 1, column=2, padx=(0, 8))
        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=len(fields), column=1, sticky="w", padx=8, pady=12)
        ctk.CTkButton(buttons, text="Save", width=90, command=self.save).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Duplicate", width=90, command=self.duplicate).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Delete", width=90, fg_color="#b23b3b", hover_color="#8f2e2e",
                      command=self.delete).pack(side="left", padx=4)
        self.status = ctk.CTkLabel(form, text="", anchor="w")
        self.status.grid(row=len(fields) + 1, column=1, sticky="w", padx=8)
        self.reload_list()

    # ---- list ------------------------------------------------------------
    def reload_list(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        for profile in self.ctx.db.list_profiles():
            ctk.CTkButton(self.list_frame, text=profile.name, anchor="w", fg_color="transparent",
                          text_color=("gray10", "gray90"), hover_color=("gray75", "gray30"),
                          command=lambda p=profile: self.load(p)).pack(fill="x", pady=1)

    def new_profile(self) -> None:
        self.load(AppProfile(name=""))

    def load(self, p: AppProfile) -> None:
        self.current_id = p.id
        values = {
            "name": p.name, "pitch": p.pitch, "description": p.description, "audience": p.audience,
            "features": "\n".join(p.features), "tone": p.tone, "store_links": format_links(p.store_links),
            "seed_keywords": ", ".join(p.seed_keywords), "banned_phrases": ", ".join(p.banned_phrases),
            "default_hashtags": ", ".join(p.default_hashtags), "default_image_path": p.default_image_path,
        }
        for key, widget in self.entries.items():
            self._set(widget, values[key])
        self.status.configure(text="")

    @staticmethod
    def _set(widget, value: str) -> None:
        if isinstance(widget, ctk.CTkTextbox):
            widget.delete("1.0", "end")
            widget.insert("1.0", value)
        else:
            widget.delete(0, "end")
            widget.insert(0, value)

    @staticmethod
    def _get(widget) -> str:
        return widget.get("1.0", "end").strip() if isinstance(widget, ctk.CTkTextbox) else widget.get().strip()

    def _read(self) -> AppProfile:
        g = {k: self._get(w) for k, w in self.entries.items()}
        return AppProfile(
            id=self.current_id, name=g["name"], pitch=g["pitch"], description=g["description"],
            audience=g["audience"], features=parse_lines(g["features"]), tone=g["tone"],
            store_links=parse_links(g["store_links"]), seed_keywords=parse_csv(g["seed_keywords"]),
            banned_phrases=parse_csv(g["banned_phrases"]), default_hashtags=parse_csv(g["default_hashtags"]),
            default_image_path=g["default_image_path"])

    # ---- actions ---------------------------------------------------------
    def save(self) -> None:
        profile = self._read()
        if not profile.name:
            self.status.configure(text="Give the profile a name.")
            return
        try:
            self.current_id = self.ctx.db.save_profile(profile)
        except sqlite3.IntegrityError:
            self.status.configure(text=f'A profile named "{profile.name}" already exists. Pick another name.')
            return
        except Exception:
            log.exception("Could not save profile")
            self.status.configure(text="Could not save the profile. Details are in the log file.")
            return
        self.status.configure(text="Saved.")
        self.reload_list()
        if self.on_change:
            self.on_change()

    def duplicate(self) -> None:
        profile = self._read()
        profile.id, profile.name = None, (profile.name or "Profile") + " copy"
        self.current_id = None
        self._set(self.entries["name"], profile.name)
        self.status.configure(text="Edit the name and click Save to create the copy.")

    def delete(self) -> None:
        if self.current_id is None:
            return
        if messagebox.askyesno("Delete profile", "Delete this profile? This cannot be undone."):
            self.ctx.db.delete_profile(self.current_id)
            self.new_profile()
            self.reload_list()
            if self.on_change:
                self.on_change()

    def _browse(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self._set(self.entries["default_image_path"], path)

    def export_json(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="promo_profiles.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            count = export_profiles(self.ctx.db, path)
            self.status.configure(text=f"Exported {count} profile(s).")
        except OSError:
            log.exception("Export failed")
            self.status.configure(text="Could not write that file. Choose another location.")

    def import_json(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            created, updated = import_profiles(self.ctx.db, path)
        except ValueError as exc:
            self.status.configure(text=str(exc))
            return
        self.status.configure(text=f"Imported: {created} new, {updated} updated (matched by name).")
        self.reload_list()
        if self.on_change:
            self.on_change()
