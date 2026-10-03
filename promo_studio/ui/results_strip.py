from __future__ import annotations

import webbrowser

import customtkinter as ctk

LABELS = {"facebook": "Facebook", "instagram": "Instagram", "x": "X", "reddit": "Reddit"}
TEXT = {"posting": "posting...", "posted": "posted", "failed": "failed", "blocked": "not sent",
        "needs_check": "unconfirmed"}
COLOR = {"posting": ("gray35", "gray70"), "posted": "#2e9e5b", "failed": "#d64545", "blocked": "#d98e04",
         "needs_check": "#d98e04"}


class ResultsStrip(ctk.CTkFrame):
    """One row per platform: live status, a link to the post, and Retry for failures."""

    def __init__(self, master, on_retry):
        super().__init__(master, fg_color="transparent")
        self.on_retry, self.rows = on_retry, {}
        self.columnconfigure(1, weight=1)

    def reset(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.rows.clear()

    def update_row(self, event: dict) -> None:
        platform, status = event["platform"], event["status"]
        if platform not in self.rows:
            r = len(self.rows)
            name = ctk.CTkLabel(self, text=LABELS.get(platform, platform), width=80, anchor="w",
                                font=ctk.CTkFont(weight="bold"))
            name.grid(row=r, column=0, sticky="w", padx=(4, 6))
            label = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=520)
            label.grid(row=r, column=1, sticky="w")
            holder = ctk.CTkFrame(self, fg_color="transparent")
            holder.grid(row=r, column=2, sticky="e", padx=4)
            self.rows[platform] = (label, holder)
        label, holder = self.rows[platform]
        for child in holder.winfo_children():
            child.destroy()
        text = TEXT.get(status, status)
        if event.get("message") and status != "posted":
            text += f": {event['message']}"
        label.configure(text=text, text_color=COLOR.get(status, ("gray35", "gray70")))
        if status == "posted" and event.get("url"):
            ctk.CTkButton(holder, text="Open", width=60,
                          command=lambda u=event["url"]: webbrowser.open(u)).pack(side="left", padx=2)
        if status == "failed":
            ctk.CTkButton(holder, text="Retry", width=60, fg_color="#b23b3b", hover_color="#8f2e2e",
                          command=lambda p=platform: self.on_retry(p)).pack(side="left", padx=2)
