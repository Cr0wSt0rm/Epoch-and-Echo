"""Normalize arbitrary source footage into the channel's house format.

The output is always 1920x1080 @ 30fps, H.264 + AAC, with a stereo audio track
(silent audio is synthesized when the source has none) and an optional burned-in
lower-third caption.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..config import TARGET_FPS, TARGET_HEIGHT, TARGET_WIDTH, VideoConfig
from ..fonts import find_bold_font
from ..media import MediaInfo, run_ffmpeg


def _lower_third_filter(text: str) -> str:
    """Build a drawtext filter that renders a caption over a dark banner.

    The caption text is passed via a temp file (textfile=) to avoid the very
    fiddly escaping rules of ffmpeg's inline drawtext text= option.
    """
    font = find_bold_font()
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()
    return (
        "drawtext="
        f"fontfile={font}:"
        f"textfile={tmp.name}:"
        "fontcolor=white:"
        "fontsize=52:"
        "box=1:boxcolor=0x000000AA:boxborderw=24:"
        "x=(w-text_w)/2:"
        "y=h-text_h-90"
    )


def normalize(source: Path, info: MediaInfo, cfg: VideoConfig, dest: Path) -> Path:
    """Transcode ``source`` to the house format, writing to ``dest``."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    vf_parts = [
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease",
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black",
        "setsar=1",
        f"fps={TARGET_FPS}",
    ]
    if cfg.subtitle:
        vf_parts.append(_lower_third_filter(cfg.subtitle))
    vf = ",".join(vf_parts)

    args: list[str] = ["-i", str(source)]
    if not info.has_audio:
        args += [
            "-f",
            "lavfi",
            "-t",
            str(max(info.duration, 0.1)),
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
        ]
        maps = ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        maps = ["-map", "0:v:0", "-map", "0:a:0"]

    args += [
        "-vf",
        vf,
        *maps,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-shortest",
        str(dest),
    ]
    run_ffmpeg(args)
    return dest
