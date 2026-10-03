from __future__ import annotations

import customtkinter as ctk
from PIL import Image


class PreviewDialog(ctk.CTkToplevel):
    """Shows exactly what will be published. With `on_confirm` it becomes the Post now confirmation."""

    def __init__(self, master, entries: list[dict], image_path: str | None = None, on_confirm=None):
        super().__init__(master)
        self.title("Confirm and post" if on_confirm else "Preview")
        self.geometry("680x680")
        self.on_confirm = on_confirm
        body = ctk.CTkTextbox(self, wrap="word")
        body.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        for e in entries:
            body.insert("end", f"{e['label'].upper()}\n", )
            body.insert("end", f"{e['text']}\n")
            for problem in e["problems"]:
                body.insert("end", f"  ! {problem}\n")
            body.insert("end", "\n")
        body.configure(state="disabled")
        if image_path:
            try:
                img = Image.open(image_path)
                img.load()
                scale = min(260 / img.width, 200 / img.height)
                self._thumb = ctk.CTkImage(light_image=img, dark_image=img,
                                           size=(int(img.width * scale), int(img.height * scale)))
                ctk.CTkLabel(self, image=self._thumb, text="").pack(pady=4)
                ctk.CTkLabel(self, text="Instagram crop shown (other platforms keep your original shape).",
                             text_color="gray50").pack()
            except Exception:
                pass
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkButton(row, text="Close" if not on_confirm else "Cancel", width=100, fg_color="gray40",
                      command=self.destroy).pack(side="left", padx=6)
        if on_confirm:
            ctk.CTkButton(row, text="Post now", width=120, command=self._confirm).pack(side="left", padx=6)
        self.after(150, self._focus)

    def _focus(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _confirm(self) -> None:
        self.destroy()
        if self.on_confirm:
            self.on_confirm()
