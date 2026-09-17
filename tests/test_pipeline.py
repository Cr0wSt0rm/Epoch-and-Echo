import shutil
import subprocess
from pathlib import Path

import pytest

from gi_radio.audio import narration_to_tts_text, probe_duration_seconds
from gi_radio.images import build_workflow, scene_seed
from gi_radio.pipeline import Pipeline, PipelineConfig
from gi_radio.render import build_stitch_plan
from gi_radio.schema import CINEMATIC_STYLE, VoiceRole
from gi_radio.script import get_script

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_tts_text_turns_paragraph_breaks_into_break_tags():
    script = get_script()
    scene = script.scenes[0]
    voice = script.voice_for(scene)
    tts = narration_to_tts_text(scene.narration_text, voice)
    assert f'<break time="{voice.paragraph_break_seconds:.1f}s" />' in tts
    assert "\n" not in tts


def test_comfyui_workflow_carries_prompt_and_scene_id():
    script = get_script()
    scene = script.scenes[3]
    wf = build_workflow(scene, script.render, checkpoint="sd_xl_base_1.0.safetensors", seed=scene_seed(scene))
    assert CINEMATIC_STYLE in wf["6"]["inputs"]["text"]
    assert wf["9"]["inputs"]["filename_prefix"].endswith(scene.scene_id)
    assert wf["3"]["inputs"]["seed"] == scene_seed(scene)
    assert (wf["5"]["inputs"]["width"], wf["5"]["inputs"]["height"]) == (1344, 768)


def test_stitch_plan_maps_every_scene_once_and_filters_hannah(tmp_path):
    script = get_script()
    durations = {s.scene_id: s.duration_seconds for s in script.scenes}
    plan = build_stitch_plan(script, tmp_path, durations)

    assert plan.scene_order == [s.scene_id for s in script.scenes]
    assert len(plan.clips) == len(script.scenes)
    assert len({c.audio_path for c in plan.clips}) == len(plan.clips)
    assert len({c.image_path for c in plan.clips}) == len(plan.clips)
    assert len({c.clip_path for c in plan.clips}) == len(plan.clips)

    for clip, scene in zip(plan.clips, script.scenes):
        is_hannah = scene.elevenlabs_voice is VoiceRole.HANNAH_RADIO
        assert clip.radio_filter_applied is is_hannah
        assert ("highpass" in clip.audio_filter) is is_hannah
        assert ("anoisesrc" in clip.audio_filter) is is_hannah
        expected_grade = script.color_grade.filter_for(scene.grade_variant)
        assert expected_grade in clip.video_filter
        assert "zoompan" in clip.video_filter

    xfade = " ".join(plan.crossfade_command)
    assert xfade.count("xfade=") == len(script.scenes) - 1
    assert xfade.count("acrossfade=") == len(script.scenes) - 1
    assert "transition=dissolve" in xfade and "transition=fadeblack" in xfade
    overlap = sum(min(c.transition_in_seconds, 999) for c in plan.clips[1:])
    assert plan.total_runtime_seconds == pytest.approx(sum(durations.values()) - overlap, abs=0.5)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_placeholder_render_end_to_end(tmp_path):
    """Real FFmpeg run over three scenes (narrator, hannah, narrator) at 1/20 duration."""

    script = get_script()
    config = PipelineConfig(
        build_dir=tmp_path,
        placeholder_audio=True,
        placeholder_images=True,
        duration_scale=0.05,
        scene_ids=["S07", "S08", "S09"],
    )
    manifest = Pipeline(script, config).run(render=True)

    assert [s.scene_id for s in manifest.scenes] == ["S07", "S08", "S09"]
    for entry in manifest.scenes:
        assert Path(entry.audio_path).exists()
        assert Path(entry.image_path).exists()
        assert Path(entry.clip_path).exists()
        clip_len = probe_duration_seconds(Path(entry.clip_path))
        assert clip_len == pytest.approx(entry.clip_duration_seconds, abs=0.15)

    final = Path(manifest.final_video)
    assert final.exists()
    assert probe_duration_seconds(final) == pytest.approx(manifest.plan.total_runtime_seconds, abs=0.25)

    streams = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "csv=p=0", str(final)],
        check=True, capture_output=True, text=True,
    ).stdout
    assert "video,1920,1080" in streams and "audio" in streams
    assert (tmp_path / "manifest.json").exists()
