from __future__ import annotations

import datetime as dt
import logging
import threading

import customtkinter as ctk

from promo_studio.adapters.graph import GraphError
from promo_studio.ai.base import AIError
from promo_studio.config.secrets import get_secret, mask, set_secret

log = logging.getLogger(__name__)


class SettingsTab(ctk.CTkScrollableFrame):
    def __init__(self, master, ctx):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.columnconfigure(1, weight=1)
        self.vars: dict[str, ctk.StringVar] = {}
        self.secret_vars: dict[str, ctk.StringVar] = {}
        self.secret_labels: dict[str, ctk.CTkLabel] = {}
        self._r = 0
        s = ctx.settings

        self._section("AI drafting")
        self._option("Provider", "ai.provider", ["gemini", "ollama"])
        self._field("Gemini model name", "ai.model")
        self._secret("Gemini API key", "GEMINI_API_KEY")
        self._field("Ollama model", "ai.ollama_model")
        self._field("Ollama URL", "ai.ollama_url")
        self._field("AI calls per minute", "ai.calls_per_minute", width=80)
        self._field("Default variants (1-5)", "ai.variants", width=80)

        self._section("Hashtag limits per post")
        self._field("X", "hashtags.max.x", width=80)
        self._field("Instagram", "hashtags.max.instagram", width=80)
        self._field("Facebook", "hashtags.max.facebook", width=80)

        self._section("Publishing accounts")
        self._field("Instagram user ID", "ig.user_id")
        self._secret("Instagram access token", "IG_ACCESS_TOKEN")
        self.expiry_label = ctk.CTkLabel(self, text="", anchor="w")
        self.expiry_label.grid(row=self._r, column=1, sticky="w", padx=10)
        self._r += 1
        self._field("Facebook Page ID", "fb.page_id")
        self._secret("Facebook Page access token", "FB_PAGE_TOKEN")
        self._secret("Image host API key (ImgBB)", "IMAGE_HOST_KEY")
        self._field("Meta API version", "meta.api_version", width=100)
        self._field("Max parallel posts", "post.max_parallel", width=80)
        self._field("Auto-retries per platform", "post.retries", width=80)
        self._refresh_expiry()

        self._section("Appearance")
        self._option("Theme", "theme", ["system", "light", "dark"])

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=self._r, column=0, columnspan=2, sticky="w", padx=10, pady=(16, 4))
        ctk.CTkButton(row, text="Save settings", command=self.save).pack(side="left", padx=4)
        self.buttons = []
        for text, action in (("Test AI", self._test_ai), ("Test Instagram", lambda: self._test("instagram")),
                             ("Test Facebook", lambda: self._test("facebook")),
                             ("Refresh Instagram token", self._refresh_token)):
            b = ctk.CTkButton(row, text=text, fg_color="gray40", command=action)
            b.pack(side="left", padx=4)
            self.buttons.append(b)
        self._r += 1
        self.status = ctk.CTkLabel(self, text="", anchor="w", wraplength=620, justify="left")
        self.status.grid(row=self._r, column=0, columnspan=2, sticky="w", padx=10, pady=4)

    # ---- layout helpers ------------------------------------------------------
    def _section(self, text: str) -> None:
        ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(
            row=self._r, column=0, columnspan=2, sticky="w", padx=10, pady=(16, 4))
        self._r += 1

    def _field(self, label: str, key: str, width: int = 300) -> None:
        ctk.CTkLabel(self, text=label, anchor="w").grid(row=self._r, column=0, sticky="w", padx=10, pady=4)
        self.vars[key] = ctk.StringVar(value=self.ctx.settings.get(key))
        ctk.CTkEntry(self, textvariable=self.vars[key], width=width).grid(row=self._r, column=1, sticky="w", padx=10)
        self._r += 1

    def _option(self, label: str, key: str, values: list[str]) -> None:
        ctk.CTkLabel(self, text=label, anchor="w").grid(row=self._r, column=0, sticky="w", padx=10, pady=4)
        self.vars[key] = ctk.StringVar(value=self.ctx.settings.get(key))
        ctk.CTkOptionMenu(self, values=values, variable=self.vars[key]).grid(row=self._r, column=1, sticky="w", padx=10)
        self._r += 1

    def _secret(self, label: str, name: str) -> None:
        ctk.CTkLabel(self, text=label, anchor="w").grid(row=self._r, column=0, sticky="w", padx=10, pady=4)
        self.secret_vars[name] = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.secret_vars[name], width=300, show="*",
                     placeholder_text="paste to replace").grid(row=self._r, column=1, sticky="w", padx=10)
        self._r += 1
        self.secret_labels[name] = ctk.CTkLabel(self, text=f"Current: {mask(get_secret(name))}", anchor="w",
                                                text_color="gray50")
        self.secret_labels[name].grid(row=self._r, column=1, sticky="w", padx=10)
        self._r += 1

    # ---- actions ---------------------------------------------------------------
    def save(self) -> None:
        for key, var in self.vars.items():
            self.ctx.settings.set(key, var.get().strip())
        stored = []
        for name, var in self.secret_vars.items():
            if var.get().strip():
                stored.append(f"{name} -> {set_secret(name, var.get().strip())}")
                var.set("")
                self.secret_labels[name].configure(text=f"Current: {mask(get_secret(name))}")
        ctk.set_appearance_mode(self.vars["theme"].get() or "system")
        self.status.configure(text="Settings saved." + (f" Stored: {', '.join(stored)}." if stored else ""))

    def _refresh_expiry(self) -> None:
        raw = self.ctx.settings.get("ig.token_expires")
        try:
            date = dt.date.fromisoformat(raw)
            self.expiry_label.configure(text=f"Token expires {date} ({(date - dt.date.today()).days} days left)")
        except ValueError:
            self.expiry_label.configure(text="Token expiry unknown: click Refresh Instagram token after pasting it.")

    def _background(self, work) -> None:
        for b in self.buttons:
            b.configure(state="disabled")
        self.status.configure(text="Working...")

        def run():
            try:
                msg = work()
            except (AIError, GraphError) as exc:
                msg = f"Problem: {getattr(exc, 'message', None) or exc}"
            except Exception:
                log.exception("Settings action failed")
                msg = "Unexpected error. Details are in the log file."
            self.after(0, lambda: self._finish(msg))

        threading.Thread(target=run, daemon=True).start()

    def _finish(self, msg: str) -> None:
        self.status.configure(text=msg)
        self._refresh_expiry()
        for b in self.buttons:
            b.configure(state="normal")

    def _test_ai(self) -> None:
        self.save()
        self._background(lambda: "AI connection works." if self.ctx.make_provider().health_check()
                         else "The provider replied but the test failed.")

    def _test(self, platform: str) -> None:
        self.save()

        def work():
            adapter = self.ctx.make_adapters().get(platform)
            if adapter is None:
                return f"Add the {platform} ID and access token first, then save."
            if adapter.check_auth():
                return f"{platform.title()} connected as {adapter.last_account}."
            return f"{platform.title()} connection failed: {adapter.last_error}"

        self._background(work)

    def _refresh_token(self) -> None:
        self.save()

        def work():
            adapter = self.ctx.make_adapters().get("instagram")
            if adapter is None:
                return "Add the Instagram user ID and access token first, then save."
            token, seconds = adapter.refresh_token()
            set_secret("IG_ACCESS_TOKEN", token)
            self.secret_labels["IG_ACCESS_TOKEN"].configure(text=f"Current: {mask(token)}")
            expires = dt.date.today() + dt.timedelta(seconds=seconds)
            self.ctx.settings.set("ig.token_expires", expires.isoformat())
            return f"Instagram token refreshed. It now expires on {expires}."

        self._background(work)
