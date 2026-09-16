from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from config.settings import Paths, Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SCRIPT = PROJECT_ROOT / "episodes" / "the-fall-of-constantinople.json"

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="test-voice",
        comfyui_url="http://comfy.test:8188",
        comfyui_checkpoint="test.safetensors",
        paths=Paths(root=PROJECT_ROOT, output=tmp_path / "output"),
    )


def make_silent_audio(target: Path, seconds: float = 1.0) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}",
            "-c:a", "libmp3lame", "-q:a", "4",
            str(target),
        ],
        check=True,
    )
    return target


def make_still_image(target: Path, color: str = "0x1a1a2e") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1920x1088",
            "-frames:v", "1",
            str(target),
        ],
        check=True,
    )
    return target
