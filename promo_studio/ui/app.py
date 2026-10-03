from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

import customtkinter as ctk

from promo_studio import __version__
from promo_studio.config.settings import app_home, load_env
from promo_studio.core.context import AppContext
from promo_studio.core.logsafe import RedactFilter
from promo_studio.data.db import Database
from promo_studio.ui.compose_tab import ComposeTab
from promo_studio.ui.profiles_tab import ProfilesTab
from promo_studio.ui.settings_tab import SettingsTab


class App(ctk.CTk):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        ctk.set_appearance_mode(ctx.settings.get("theme") or "system")
        self.title(f"Social Promo Studio {__version__}")
        self.geometry("1240x820")
        self.minsize(1000, 680)

        self.tabs = ctk.CTkTabview(self, command=self._on_tab)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
        for name in ("Compose", "Profiles", "ASO", "Queue", "Settings"):
            self.tabs.add(name)
        self.compose = ComposeTab(self.tabs.tab("Compose"), ctx)
        self.compose.pack(fill="both", expand=True)
        ProfilesTab(self.tabs.tab("Profiles"), ctx, on_change=self.compose.refresh_profiles).pack(fill="both", expand=True)
        for name, phase in (("ASO", "phase 4"), ("Queue", "phase 3")):
            ctk.CTkLabel(self.tabs.tab(name), text=f"{name} arrives in {phase} of the roadmap.",
                         text_color="gray50").pack(pady=40)
        SettingsTab(self.tabs.tab("Settings"), ctx).pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        stale = ctx.db.mark_stale_posting()
        notes = [m for m in (
            f"{stale} post(s) were interrupted last time and may or may not have gone out: check the platforms "
            "before posting again." if stale else None, ctx.token_warning()) if m]
        if notes:
            self.compose.status.configure(text=" ".join(notes))

    def _on_close(self) -> None:
        try:
            self.compose.save_draft(announce=False)
        finally:
            self.destroy()

    def _on_tab(self) -> None:
        if self.tabs.get() == "Compose":
            self.compose.refresh_profiles()


def _setup_logging() -> None:
    handler = RotatingFileHandler(app_home() / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.addFilter(RedactFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def run() -> None:
    load_env()
    _setup_logging()
    db = Database(app_home() / "promo_studio.db")
    App(AppContext(db)).mainloop()
