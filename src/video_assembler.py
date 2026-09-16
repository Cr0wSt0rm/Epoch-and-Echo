"""Stage 5: stitch scene audio and images into a video with FFmpeg.

Each scene becomes one clip (its image, slowly pushed in, over its narration),
and the clips are concatenated in scene order into `output/final_videos/`.
"""

from __future__ import annotations

import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from config import Settings
from src.models import Scene, Script, VideoAsset
from src.script_generator import slugify

logger = logging.getLogger(__name__)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
# Gentle push-in over the length of the scene; kept small to stay stately.
ZOOM_AMOUNT = 0.08
FADE_SECONDS = 0.5
# Silence after each narration so the pacing breathes.
SCENE_TAIL_SECONDS = 0.6


def _run(command: list[str]) -> None:
    logger.debug("ffmpeg: %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed ({result.returncode}):\n{result.stderr.strip()}")


def require_ffmpeg(settings: Settings) -> None:
    for binary in (settings.ffmpeg_binary, settings.ffprobe_binary):
        if shutil.which(binary) is None:
            raise RuntimeError(f"{binary} not found on PATH; install FFmpeg")


def probe_duration(path: Path, settings: Settings) -> float:
    """Return the duration of a media file in seconds using ffprobe."""
    result = subprocess.run(
        [
            settings.ffprobe_binary,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}:\n{result.stderr.strip()}")
    return float(result.stdout.strip())


def render_scene_clip(scene: Scene, target: Path, settings: Settings) -> Path:
    """Render one scene's image + narration into an H.264/AAC clip."""
    if scene.audio_path is None or scene.image_path is None:
        raise ValueError(f"scene {scene.index} is missing audio or image")
    duration = probe_duration(scene.audio_path, settings) + SCENE_TAIL_SECONDS
    frames = max(1, math.ceil(duration * FPS))
    fade_out_start = max(0.0, duration - FADE_SECONDS)

    video_filter = ",".join(
        [
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase",
            f"crop={WIDTH}:{HEIGHT}",
            (
                f"zoompan=z='1+{ZOOM_AMOUNT}*on/{frames}':d={frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={WIDTH}x{HEIGHT}:fps={FPS}"
            ),
            f"fade=t=in:st=0:d={FADE_SECONDS}",
            f"fade=t=out:st={fade_out_start:.3f}:d={FADE_SECONDS}",
            "format=yuv420p",
        ]
    )
    audio_filter = f"apad=pad_dur={SCENE_TAIL_SECONDS}"

    _run(
        [
            settings.ffmpeg_binary,
            "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(scene.image_path),
            "-i", str(scene.audio_path),
            "-filter_complex", f"[0:v]{video_filter}[v];[1:a]{audio_filter}[a]",
            "-map", "[v]", "-map", "[a]",
            "-t", f"{duration:.3f}",
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart",
            str(target),
        ]
    )
    return target


def concat_clips(clips: list[Path], target: Path, settings: Settings) -> Path:
    """Losslessly concatenate identically encoded clips in order."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        for clip in clips:
            escaped = str(clip.resolve()).replace("'", r"'\''")
            handle.write(f"file '{escaped}'\n")
        list_path = Path(handle.name)
    try:
        _run(
            [
                settings.ffmpeg_binary,
                "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", str(list_path),
                "-c", "copy",
                "-movflags", "+faststart",
                str(target),
            ]
        )
    finally:
        list_path.unlink(missing_ok=True)
    return target


def assemble_video(script: Script, settings: Settings) -> VideoAsset:
    """Render the final video for `script` and return its asset."""
    require_ffmpeg(settings)
    script.require_render_ready()
    settings.paths.final_videos.mkdir(parents=True, exist_ok=True)
    target = settings.paths.final_videos / f"{slugify(script.title)}.mp4"
    logger.info("Assembling %d scenes -> %s", len(script.scenes), target)

    with tempfile.TemporaryDirectory(prefix="epoch_echo_scenes_") as workdir:
        clips: list[Path] = []
        for scene in script.scenes:
            clip = Path(workdir) / f"scene_{scene.index:03d}.mp4"
            logger.info("Rendering scene %d", scene.index)
            clips.append(render_scene_clip(scene, clip, settings))
        concat_clips(clips, target, settings)

    duration = probe_duration(target, settings)
    logger.info("Rendered %s (%.1fs)", target.name, duration)
    return VideoAsset(
        script=script,
        video_path=target,
        thumbnail_path=script.scenes[0].image_path,
        duration_seconds=duration,
    )
