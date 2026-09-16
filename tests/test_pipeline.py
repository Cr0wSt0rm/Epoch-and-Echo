"""End-to-end run of `src.main.run_pipeline` with the external APIs stubbed.

ElevenLabs and ComfyUI are replaced by local synthetic assets; FFmpeg runs for
real, so this proves the Narration -> Audio -> Image -> Stitching mapping holds
from the example script through to a finished MP4.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src import image_generator, main, script_generator, voiceover
from src.models import CINEMATIC_STYLE
from tests.conftest import EXAMPLE_SCRIPT, make_silent_audio, make_still_image, requires_ffmpeg

pytestmark = requires_ffmpeg


def test_run_pipeline_end_to_end(settings, monkeypatch, tmp_path: Path):
    voiced: list[str] = []
    illustrated: list[str] = []

    def fake_synthesize_scene(scene, cfg):
        voiced.append(scene.narration)
        return make_silent_audio(cfg.paths.audio / f"scene_{scene.index:03d}.mp3", seconds=0.8)

    def fake_generate_scene_image(scene, cfg, *, script_title="", client=None):
        assert scene.image_prompt.endswith(CINEMATIC_STYLE)
        illustrated.append(scene.image_prompt)
        return make_still_image(cfg.paths.images / f"scene_{scene.index:03d}.png")

    monkeypatch.setattr(voiceover, "synthesize_scene", fake_synthesize_scene)
    monkeypatch.setattr(image_generator, "generate_scene_image", fake_generate_scene_image)
    monkeypatch.setattr(image_generator, "ComfyUIClient", lambda url: None)

    asset = main.run_pipeline("The Fall of Constantinople", settings)

    script = asset.script
    assert len(script.scenes) == 3
    assert voiced == [s.narration for s in script.scenes]
    assert illustrated == [s.image_prompt for s in script.scenes]
    for scene in script.scenes:
        assert scene.audio_path.is_file() and scene.image_path.is_file()
    assert asset.video_path.is_file()
    assert asset.duration_seconds == pytest.approx(3 * 0.8 + 3 * 0.6, abs=0.3)


def test_missing_script_gives_actionable_error(settings):
    from src.models import Topic

    with pytest.raises(FileNotFoundError, match="SCRIPTWRITING_BRIEF"):
        script_generator.generate_script(Topic(title="Nothing Written Yet"), settings)


def test_default_script_path_is_slug_of_topic(settings):
    from src.models import Topic

    path = script_generator.script_path_for(Topic(title="The Fall of Constantinople"), settings)
    assert path == EXAMPLE_SCRIPT


def test_scriptwriting_brief_mentions_style_and_bans():
    brief = script_generator.SCRIPTWRITING_BRIEF
    assert CINEMATIC_STYLE in brief
    for word in ("delve", "testament", "moreover"):
        assert word in brief
