from __future__ import annotations
import hashlib, io, os, tempfile
from pathlib import Path
from typing import Any, Mapping
from .models import parse_day, DataError
from .adapter import adapt_siddhanta
from .posts import REGISTRY
from .selector import select
from .caption import caption_input, system_prompt
from .theme import require_raqm

class PromoStudio:
    def __init__(self, output_dir="output"):
        require_raqm()
        self.output_dir = Path(output_dir)

    def generate(self, payload: Mapping[str, Any], overwrite: bool = True, muhurta_data: Mapping[str, Any] | None = None) -> dict:
        # Accept either the internal normalized payload or the real Siddhanta workflow output.
        today = payload.get("today") if isinstance(payload, Mapping) else None
        looks_like_siddhanta = isinstance(payload, Mapping) and ("metadata" in payload or (isinstance(today, Mapping) and "day_of_week_en" in today))
        if looks_like_siddhanta:
            if not isinstance(today, Mapping) or not isinstance(today.get("english"), Mapping):
                raise DataError("not a Siddhanta payload: today.english is required")
            payload = adapt_siddhanta(payload, muhurta_data)
        day = parse_day(payload)                        # raises DataError on bad data
        spec = select(day)
        path = self.output_dir / f"{spec.date}_{spec.kind}_1080x1350.png"   # date is validated ISO
        if path.exists() and not overwrite:
            return self._result(spec, path, None, skipped=True)
        img = REGISTRY[spec.kind].render(spec)
        buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)                # no metadata => reproducible
        data = buf.getvalue()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.output_dir, suffix=".tmp")         # atomic: no half-written PNGs
        try:
            with os.fdopen(fd, "wb") as fh: fh.write(data)
            os.replace(tmp, path)
        except BaseException:
            try: os.unlink(tmp)
            except OSError: pass
            raise
        return self._result(spec, path, hashlib.sha256(data).hexdigest())

    @staticmethod
    def _result(spec, path, sha, skipped=False):
        return {"post_type": spec.kind, "path": str(path), "width": 1080, "height": 1350,
                "sha256": sha, "skipped": skipped, "illustrative": spec.illustrative,
                "warnings": list(spec.warnings),
                "caption_facts": spec.to_dict()["facts"],
                "caption_input": caption_input(spec).to_dict(),
                "caption_system_prompt": system_prompt()}
