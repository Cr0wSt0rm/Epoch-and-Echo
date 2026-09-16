from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src import video_assembler
from src.models import Scene, Script, Topic
from tests.conftest import make_silent_audio, make_still_image, requires_ffmpeg

pytestmark = requires_ffmpeg


def probe_streams(path: Path) -> dict[str, str]:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,width,height",
            "-of", "csv=p=0",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    streams: dict[str, str] = {}
    for line in out.strip().splitlines():
        parts = line.split(",")
        streams[parts[1] if parts[1] in ("video", "audio") else parts[0]] = line
    return streams


def test_assemble_video_stitches_scenes_in_order(settings, tmp_path: Path):
    scenes = []
    for index, seconds in enumerate((1.0, 1.5)):
        scenes.append(
            Scene(
                index=index,
                narration=f"Beat {index}.",
                image_prompt="frame",
                audio_path=make_silent_audio(tmp_path / f"a{index}.mp3", seconds),
                image_path=make_still_image(tmp_path / f"i{index}.png"),
            )
        )
    script = Script(topic=Topic(title="T"), title="The Night the Walls Fell", scenes=scenes)

    asset = video_assembler.assemble_video(script, settings)

    assert asset.video_path == settings.paths.final_videos / "the-night-the-walls-fell.mp4"
    assert asset.video_path.is_file()
    assert asset.thumbnail_path == scenes[0].image_path
    expected = sum((1.0, 1.5)) + 2 * video_assembler.SCENE_TAIL_SECONDS
    assert asset.duration_seconds == pytest.approx(expected, abs=0.25)

    streams = probe_streams(asset.video_path)
    assert "h264" in streams["video"] and "1920,1080" in streams["video"]
    assert "aac" in streams["audio"]


def test_assemble_video_refuses_incomplete_scene_mapping(settings, tmp_path: Path):
    scenes = [
        Scene(index=0, narration="Beat.", image_prompt="frame", audio_path=tmp_path / "a.mp3"),
    ]
    script = Script(topic=Topic(title="T"), title="T", scenes=scenes)
    with pytest.raises(ValueError, match="scene 0: missing image"):
        video_assembler.assemble_video(script, settings)
    assert not (settings.paths.final_videos / "t.mp4").exists()
