import json

import pytest

from promo_studio.data.db import Database
from promo_studio.data.models import AppProfile
from promo_studio.data.profile_io import export_profiles, import_profiles


def test_round_trip_and_merge_by_name(tmp_path):
    src = Database(tmp_path / "a.db")
    src.save_profile(AppProfile(name="ClearIQ", pitch="v1", features=["f"], store_links={"ios": "u"}))
    src.save_profile(AppProfile(name="Siddhanta"))
    out = tmp_path / "p.json"
    assert export_profiles(src, out) == 2

    dst = Database(tmp_path / "b.db")
    existing_id = dst.save_profile(AppProfile(name="cleariq", pitch="old"))  # matches case-insensitively
    created, updated = import_profiles(dst, out)
    assert (created, updated) == (1, 1)
    by_name = {p.name.lower(): p for p in dst.list_profiles()}
    assert set(by_name) == {"cleariq", "siddhanta"}
    clear = by_name["cleariq"]
    assert clear.id == existing_id                      # updated in place, not duplicated
    assert clear.pitch == "v1" and clear.features == ["f"] and clear.store_links == {"ios": "u"}


def test_bad_files_give_friendly_errors(tmp_path):
    db = Database(tmp_path / "t.db")
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(ValueError, match="JSON"):
        import_profiles(db, bad)
    bad.write_text(json.dumps({"hello": 1}))
    with pytest.raises(ValueError, match="does not look like"):
        import_profiles(db, bad)
    bad.write_text(json.dumps({"profiles": [{"name": "ok"}, {"pitch": "no name"}]}))
    with pytest.raises(ValueError, match="no name"):
        import_profiles(db, bad)
    assert db.list_profiles() == []  # nothing written when any entry is invalid
