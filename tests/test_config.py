from pathlib import Path

import pytest

from epoch_echo.config import VideoConfig


def test_slug_is_url_friendly():
    cfg = VideoConfig(title="The Library of Alexandria!")
    assert cfg.slug == "the-library-of-alexandria"


def test_slug_falls_back_to_episode():
    cfg = VideoConfig(title="!!!")
    assert cfg.slug == "episode"


def test_from_dict_requires_title():
    with pytest.raises(ValueError):
        VideoConfig.from_dict({"description": "no title here"})


def test_from_dict_rejects_unknown_keys():
    with pytest.raises(ValueError):
        VideoConfig.from_dict({"title": "x", "bogus": 1})


def test_from_yaml(tmp_path: Path):
    recipe = tmp_path / "episode.yaml"
    recipe.write_text(
        "title: Test Episode\n"
        "tags:\n  - one\n  - two\n"
        "source: footage.mp4\n"
    )
    cfg = VideoConfig.from_yaml(recipe)
    assert cfg.title == "Test Episode"
    assert cfg.tags == ["one", "two"]
    assert cfg.source == Path("footage.mp4")
