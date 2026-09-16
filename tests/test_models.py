from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models import CINEMATIC_STYLE, Scene, Script, Topic, apply_cinematic_style, find_buzzwords
from tests.conftest import EXAMPLE_SCRIPT


def scene(**overrides) -> Scene:
    data = {"index": 0, "narration": "The gate stood open.", "image_prompt": "A gate at dawn"}
    data.update(overrides)
    return Scene(**data)


def test_image_prompt_gets_cinematic_style_suffix():
    assert scene().image_prompt == f"A gate at dawn. {CINEMATIC_STYLE}"


def test_cinematic_style_is_not_duplicated():
    prompt = f"A gate at dawn. {CINEMATIC_STYLE}"
    assert scene(image_prompt=prompt).image_prompt == prompt
    assert apply_cinematic_style(prompt.lower()).lower().count(CINEMATIC_STYLE.lower()) == 1


@pytest.mark.parametrize(
    "narration",
    [
        "Let us delve into the archives.",
        "They were delving into the dark.",
        "A Testament to their courage.",
        "Moreover, the walls held.",
    ],
)
def test_banned_buzzwords_are_rejected(narration: str):
    with pytest.raises(ValidationError, match="banned buzzword"):
        scene(narration=narration)


def test_find_buzzwords_reports_inflections():
    assert find_buzzwords("They delved deeper, moreover, as a testament.") == [
        "delved",
        "moreover",
        "testament",
    ]
    assert find_buzzwords("The last emperor vanished into the fighting.") == []


def test_script_requires_contiguous_scene_indices():
    topic = Topic(title="T")
    with pytest.raises(ValidationError, match="contiguous"):
        Script(topic=topic, title="T", scenes=[scene(index=1), scene(index=2)])
    with pytest.raises(ValidationError, match="contiguous"):
        Script(topic=topic, title="T", scenes=[scene(index=0), scene(index=0)])
    with pytest.raises(ValidationError):
        Script(topic=topic, title="T", scenes=[])


def test_require_render_ready_names_missing_assets():
    script = Script(
        topic=Topic(title="T"),
        title="T",
        scenes=[scene(index=0, audio_path=Path("a.mp3")), scene(index=1, image_path=Path("b.png"))],
    )
    with pytest.raises(ValueError) as excinfo:
        script.require_render_ready()
    assert "scene 0: missing image" in str(excinfo.value)
    assert "scene 1: missing audio" in str(excinfo.value)

    for item in script.scenes:
        item.audio_path = Path("a.mp3")
        item.image_path = Path("b.png")
    script.require_render_ready()
    assert all(item.is_render_ready for item in script.scenes)


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        Scene(index=0, narration="x", image_prompt="y", voice="deep")


def test_example_script_conforms(tmp_path: Path):
    script = Script.from_json_file(EXAMPLE_SCRIPT)
    assert [s.index for s in script.scenes] == list(range(len(script.scenes)))
    for item in script.scenes:
        assert item.image_prompt.endswith(CINEMATIC_STYLE)
        assert find_buzzwords(item.narration) == []
        assert 40 <= len(item.narration.split()) <= 90

    roundtrip = tmp_path / "roundtrip.json"
    script.to_json_file(roundtrip)
    assert Script.from_json_file(roundtrip) == script
