import pytest
from PIL import Image

from promo_studio.core.image_host import ImageHostError, ImgBBHost
from promo_studio.core.image_service import ImageService
from tests.fakes import FakeHttp, FakeResponse


def make(path, size, mode="RGB", color="red"):
    Image.new(mode, size, color).save(path)
    return str(path)


@pytest.fixture
def svc(tmp_path):
    return ImageService(tmp_path / "tmp")


def ratio(path):
    with Image.open(path) as im:
        return im.width / im.height, im.width, im.format


def test_wide_image_cropped_and_resized_for_instagram(svc, tmp_path):
    src = make(tmp_path / "wide.png", (3000, 1000))
    out = svc.prepare("instagram", src)
    r, w, fmt = ratio(out)
    assert fmt == "JPEG" and w <= 1080 and 0.8 <= r <= 1.91


def test_tall_image_cropped_for_instagram(svc, tmp_path):
    out = svc.prepare("instagram", make(tmp_path / "tall.jpg", (1000, 3000)))
    r, _, _ = ratio(out)
    assert 0.8 <= r <= 1.91


def test_transparent_png_flattened_and_original_untouched(svc, tmp_path):
    src = make(tmp_path / "t.png", (800, 800), "RGBA", (255, 0, 0, 0))
    before = (tmp_path / "t.png").read_bytes()
    out = svc.prepare("facebook", src)
    with Image.open(out) as im:
        assert im.mode == "RGB" and im.getpixel((5, 5)) == (255, 255, 255)
    assert (tmp_path / "t.png").read_bytes() == before


def test_facebook_keeps_ratio_but_caps_width(svc, tmp_path):
    out = svc.prepare("facebook", make(tmp_path / "big.jpg", (4000, 1000)))
    r, w, _ = ratio(out)
    assert w == 2048 and abs(r - 4.0) < 0.01


def test_check_reports_missing_unreadable_and_small(svc, tmp_path):
    assert svc.check("instagram", str(tmp_path / "nope.jpg")) == ["Image file not found."]
    bad = tmp_path / "bad.jpg"
    bad.write_text("not an image")
    assert svc.check("instagram", str(bad)) == ["The image could not be opened."]
    small = make(tmp_path / "s.jpg", (100, 100))
    assert "at least 320px" in svc.check("instagram", small)[0]
    assert svc.check("instagram", make(tmp_path / "ok.jpg", (800, 800))) == []


def test_discard_only_removes_files_in_temp_dir(svc, tmp_path):
    outside = tmp_path / "keep.jpg"
    outside.write_bytes(b"x")
    svc.discard(str(outside))
    assert outside.exists()
    made = svc.prepare("facebook", make(tmp_path / "a.jpg", (500, 500)))
    svc.discard(made)
    assert not __import__("os").path.exists(made)


# ---- image host -----------------------------------------------------------
def test_imgbb_returns_url(tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"abc")
    http = FakeHttp({"data": {"url": "https://i.ibb.co/x/a.jpg"}, "success": True})
    assert ImgBBHost("KEY", http=http).upload(str(f)) == "https://i.ibb.co/x/a.jpg"
    assert http.calls[0][2]["params"] == {"key": "KEY"} and http.calls[0][2]["data"]["expiration"] == 3600


def test_imgbb_errors(tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"abc")
    with pytest.raises(ImageHostError, match="missing"):
        ImgBBHost("").upload(str(f))
    with pytest.raises(ImageHostError) as e:
        ImgBBHost("K", http=FakeHttp(FakeResponse(500, {}))).upload(str(f))
    assert e.value.retryable
    with pytest.raises(ImageHostError) as e:
        ImgBBHost("K", http=FakeHttp(FakeResponse(400, {"error": "bad key"}))).upload(str(f))
    assert not e.value.retryable
