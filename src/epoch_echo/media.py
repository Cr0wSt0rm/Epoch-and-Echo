"""Thin wrappers around the ffmpeg / ffprobe command-line tools.

Keeping all subprocess handling in one place makes the pipeline stages easy to
read and lets us fail with clear, actionable errors when the system ffmpeg
binaries are missing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class MediaError(RuntimeError):
    """Raised when an ffmpeg/ffprobe invocation fails or a tool is missing."""


def _require(tool: str) -> str:
    path = shutil.which(tool)
    if path is None:
        raise MediaError(
            f"Required tool {tool!r} was not found on PATH. "
            "Install ffmpeg (which provides ffmpeg and ffprobe) and try again."
        )
    return path


def ffmpeg_available() -> bool:
    """Return True when both ffmpeg and ffprobe are available on PATH."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_ffmpeg(args: list[str]) -> None:
    """Run ffmpeg with the given args, overwriting output files (-y)."""
    ffmpeg = _require("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(
            "ffmpeg failed (exit %d)\ncommand: %s\nstderr:\n%s"
            % (proc.returncode, " ".join(cmd), proc.stderr.strip())
        )


@dataclass(frozen=True)
class MediaInfo:
    """A subset of ffprobe output that the pipeline actually uses."""

    width: int
    height: int
    duration: float
    has_audio: bool

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"


def probe(path: Path) -> MediaInfo:
    """Return basic media information for a video file via ffprobe."""
    ffprobe = _require("ffprobe")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(
            "ffprobe failed for %s (exit %d)\nstderr:\n%s"
            % (path, proc.returncode, proc.stderr.strip())
        )

    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise MediaError(f"No video stream found in {path}")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    duration = 0.0
    fmt = data.get("format", {})
    for source in (fmt.get("duration"), video.get("duration")):
        try:
            duration = float(source)
            if duration > 0:
                break
        except (TypeError, ValueError):
            continue

    return MediaInfo(
        width=int(video.get("width", 0)),
        height=int(video.get("height", 0)),
        duration=round(duration, 3),
        has_audio=has_audio,
    )


def generate_test_clip(dest: Path, seconds: int = 5) -> Path:
    """Generate a synthetic test clip (video + tone) using ffmpeg sources.

    Useful for demos and tests where no real footage is available.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size=1280x720:rate=30:duration={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(dest),
        ]
    )
    return dest
