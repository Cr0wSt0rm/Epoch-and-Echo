import json
import re
from pathlib import Path

import pytest

from gi_radio.schema import (
    CINEMATIC_STYLE,
    MIN_RUNTIME_SECONDS,
    REQUIRED_BEAT_ORDER,
    EmotionalBeat,
    VoiceRole,
    find_forbidden_words,
    speech_seconds,
)
from gi_radio.script import get_script

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def script():
    return get_script()


def test_runtime_clears_fifteen_minutes_without_pauses(script):
    speech_only = speech_seconds(" ".join(s.narration_text for s in script.scenes), wpm=130)
    assert speech_only >= MIN_RUNTIME_SECONDS
    assert script.total_runtime_seconds >= MIN_RUNTIME_SECONDS


def test_every_prompt_carries_the_house_style(script):
    for scene in script.scenes:
        assert CINEMATIC_STYLE in scene.comfyui_image_prompt, scene.scene_id


def test_no_forbidden_words_anywhere(script):
    for scene in script.scenes:
        assert find_forbidden_words(scene.narration_text) == [], scene.scene_id
        assert find_forbidden_words(scene.comfyui_image_prompt) == [], scene.scene_id
        assert find_forbidden_words(scene.visual_subject) == [], scene.scene_id


def test_required_beats_present_in_order(script):
    first = {}
    for index, scene in enumerate(script.scenes):
        first.setdefault(scene.beat, index)
    positions = [first[beat] for beat in REQUIRED_BEAT_ORDER]
    assert positions == sorted(positions)
    assert len(positions) == 11


def test_hannah_fragments(script):
    hannah = [s for s in script.scenes if s.elevenlabs_voice is VoiceRole.HANNAH_RADIO]
    assert 2 <= len(hannah) <= 4
    joined = "\n".join(s.narration_text for s in hannah)
    assert "How are you" in joined and "GI Joe" in joined
    assert re.search(r"look at your watch", joined, re.IGNORECASE)
    assert "ticking" in joined.lower() or "tick." in joined.lower()
    list_scene = next(s for s in hannah if s.beat is EmotionalBeat.NAME_ON_THE_RADIO)
    # A cadence of rank, name, hometown, state.
    assert len(re.findall(r"\. [A-Z][a-z]+, [A-Z][a-z]+\.", list_scene.narration_text)) >= 3
    assert "Roy Lee Macon" in list_scene.narration_text
    for scene in hannah:
        assert scene.grade_variant.value == "night_radio"


def test_protagonist_threads_through_the_script(script):
    text = "\n".join(s.narration_text for s in script.scenes)
    p = script.protagonist
    assert p.first_name in text
    assert p.hometown.split(",")[0] in text
    for correspondent in ("Carol Ann", "mother"):
        assert correspondent in text
    assert "DEROS" in text
    assert "June the eleventh, 1969" in text


def test_scenes_are_one_frame_each(script):
    for scene in script.scenes:
        assert scene.visual_subject
        assert len(scene.sfx_notes) >= 1
        assert 4 <= scene.duration_seconds <= 240


def test_ends_on_an_image_not_a_moral(script):
    last = script.scenes[-1]
    assert last.narration_text.strip().endswith("The boy is not.")
    assert "calendar" in last.visual_subject.lower() or "envelope" in last.visual_subject.lower()


def test_exported_json_is_in_sync(script):
    exported = REPO / "output" / f"{script.slug}.script.json"
    assert exported.exists(), "run: python -m gi_radio export --json output/<slug>.script.json"
    assert json.loads(exported.read_text()) == script.model_dump(mode="json")
