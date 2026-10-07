"""Atomically package review-only daily scene PNGs, cover and contact sheets."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from PIL import Image

from promo_studio.models import DataError

from .scenes import DURATIONS, render_daily


def write_preview(plan: dict, output: Path) -> dict:
    """Never overwrite a dated preview or create an apparently approved artifact."""
    if plan.get("status") != "planning_only":
        raise DataError("Only a fresh validated planning contract can be previewed")
    daily = [spec for spec in plan["deliverables"] if spec["kind"] == "daily"]
    if not daily:
        raise DataError("There are no validated daily Reel scenes to preview")
    target = output / plan["date"]
    if target.exists():
        raise DataError(f"Preview already exists at {target}; never overwrite a reviewed preview")
    # Render all requested languages before opening any output directory. Exceptions
    # leave the previous previews untouched and do not produce a partial new date.
    rendered = [(spec, render_daily(spec)) for spec in daily]
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".reel-preview-", dir=output) as staging:
        folder = Path(staging)
        artifacts: list[dict] = []

        def save(image: Image.Image, filename: str) -> None:
            path = folder / filename
            image.save(path, format="PNG", optimize=True)
            artifacts.append({"file": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

        for spec, scenes in rendered:
            language = spec["language"]
            for index, scene in enumerate(scenes, 1):
                save(scene.image, f"daily_{language}_scene_{index:02d}.png")
            save(scenes[0].image, f"daily_{language}_cover.png")
            thumbs = Image.new("RGB", (1080, 384), "#182238")
            for index, scene in enumerate(scenes):
                thumb = scene.image.convert("RGB").resize((216, 384), Image.Resampling.LANCZOS)
                thumbs.paste(thumb, (216 * index, 0))
            save(thumbs, f"daily_{language}_contact_sheet.png")

        summary = {"status": "preview_only", "date": plan["date"],
                   "review_state": "not_reviewed", "publication_ready": False,
                   "scene_durations_seconds": list(DURATIONS), "artifacts": artifacts,
                   "warnings": plan["warnings"], "held": plan["held"],
                   "not_rendered": [{"kind": spec["kind"], "language": spec["language"]}
                                    for spec in plan["deliverables"] if spec["kind"] != "daily"]}
        (folder / "preview.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
        if target.exists():
            raise DataError(f"Preview already exists at {target}")
        folder.rename(target)
    return {"path": str(target), **summary}
