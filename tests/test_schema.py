import pytest
from pydantic import ValidationError

from gi_radio.schema import (
    CINEMATIC_STYLE,
    EmotionalBeat,
    Scene,
    VoiceRole,
    count_words,
    find_forbidden_words,
    timed,
)


def make_scene(**overrides):
    text = "You learn the rain first. Not weather. A weight. It fills your collar and your boots."
    base = dict(
        scene_id="S01",
        beat=EmotionalBeat.LAND_AS_ENEMY,
        duration_seconds=timed(text),
        narration_text=text,
        elevenlabs_voice=VoiceRole.NARRATOR,
        sfx_notes=["rain on tin"],
        comfyui_image_prompt=f"Monsoon paddy, soldiers under ponchos. {CINEMATIC_STYLE}",
        visual_subject="monsoon paddy",
    )
    base.update(overrides)
    return Scene(**base)


def test_scene_requires_house_style_string():
    with pytest.raises(ValidationError, match="mandatory style string"):
        make_scene(comfyui_image_prompt="Monsoon paddy, soldiers under ponchos, cinematic lighting, 8k.")


def test_scene_rejects_forbidden_words():
    with pytest.raises(ValidationError, match="forbidden words"):
        make_scene(narration_text="The rain was a testament to the monsoon, a tapestry of water and mud.")


def test_scene_rejects_compressed_timing():
    with pytest.raises(ValidationError, match="faster than 130 wpm"):
        make_scene(duration_seconds=4.0)


def test_scene_id_pattern():
    with pytest.raises(ValidationError):
        make_scene(scene_id="scene-1")


def test_forbidden_word_search_catches_inflections():
    assert find_forbidden_words("We delved into it; it underscores the point.") == ["delve", "underscore"]
    assert find_forbidden_words("A plain sentence.") == []


def test_word_count_handles_apostrophes_and_diacritics():
    assert count_words("Trịnh Thị Ngọ. She's here, GI Joe.") == 7
