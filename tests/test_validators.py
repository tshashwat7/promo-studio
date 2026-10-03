from promo_studio.core.validators import (
    char_count, compose_text, counter_state, find_banned, normalize_hashtags, validate_post)


def test_normalize_hashtags_cleans_dedupes_caps():
    tags = ["#Sleep Better", "sleepbetter", "  #Wind_Down ", "", 42, "#Nap!!"]
    assert normalize_hashtags(tags, 5) == ["sleepbetter", "wind_down", "nap"]
    assert normalize_hashtags(tags, 2) == ["sleepbetter", "wind_down"]
    assert normalize_hashtags(tags, 0) == []


def test_compose_text_separators():
    assert compose_text("x", "Hi", ["a", "b"]) == "Hi #a #b"
    assert compose_text("instagram", "Hi", ["a"]) == "Hi\n\n#a"
    assert compose_text("facebook", " Hi ", []) == "Hi"


def test_x_counts_urls_as_23():
    text = "Try it https://example.com/a/very/long/path/that/goes/on/and/on/forever"
    assert char_count("x", text) == len("Try it ") + 23
    assert char_count("facebook", text) == len(text)


def test_counter_state():
    assert counter_state(50, 280) == "ok"
    assert counter_state(252, 280) == "warn"
    assert counter_state(281, 280) == "over"


def test_find_banned_case_insensitive():
    assert find_banned("This is GUARANTEED to work", ["guaranteed", "cure"]) == ["guaranteed"]
    assert find_banned("fine", ["", "  "]) == []


def test_validate_post_limits_and_rules():
    assert validate_post("x", "ok", ["a"]) == []
    problems = validate_post("x", "a" * 300)
    assert any("Over the limit by 20" in p for p in problems)
    assert "Text is empty." in validate_post("facebook", "  ")
    assert "Instagram needs an image." in validate_post("instagram", "hello", has_image=False)
    assert validate_post("instagram", "hello", has_image=None) == []
    assert "Reddit needs a title." in validate_post("reddit", "body", title="")
    assert any("banned" in p for p in validate_post("x", "cures insomnia", banned=["cures"]))
