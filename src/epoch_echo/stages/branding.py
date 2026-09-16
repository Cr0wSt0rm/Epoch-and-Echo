"""Wrap normalized footage with branded intro/outro title cards."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..config import (
    BRAND_ACCENT,
    BRAND_NAME,
    BRAND_PRIMARY,
    TARGET_FPS,
    TARGET_HEIGHT,
    TARGET_WIDTH,
    VideoConfig,
)
from ..fonts import find_bold_font
from ..media import run_ffmpeg


def _hex_to_ffmpeg(color: str) -> str:
    """Convert ``#rrggbb`` to ffmpeg's ``0xRRGGBB`` form."""
    return "0x" + color.lstrip("#")


def _text_arg(text: str) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()
    return tmp.name


def _title_card(primary: str, headline: str, subline: str, seconds: float, dest: Path) -> Path:
    """Render a solid-color card with a big headline and an accent subline."""
    font = find_bold_font()
    duration = max(seconds, 0.5)
    headline_file = _text_arg(headline)
    subline_file = _text_arg(subline)

    drawtext_headline = (
        "drawtext="
        f"fontfile={font}:"
        f"textfile={headline_file}:"
        "fontcolor=white:"
        "fontsize=96:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2-40"
    )
    drawtext_subline = (
        "drawtext="
        f"fontfile={font}:"
        f"textfile={subline_file}:"
        f"fontcolor={_hex_to_ffmpeg(BRAND_ACCENT)}:"
        "fontsize=48:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2+70"
    )

    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c={_hex_to_ffmpeg(primary)}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:"
            f"r={TARGET_FPS}:d={duration}",
            "-f",
            "lavfi",
            "-t",
            str(duration),
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-vf",
            f"{drawtext_headline},{drawtext_subline}",
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
    )
    return dest


def add_bookends(normalized: Path, cfg: VideoConfig, dest: Path) -> Path:
    """Prepend an intro card and append an outro card to ``normalized``."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = dest.parent

    intro = _title_card(
        BRAND_PRIMARY, cfg.title, BRAND_NAME, cfg.intro_seconds, work / "_intro.mp4"
    )
    outro = _title_card(
        BRAND_PRIMARY,
        "Thanks for watching",
        f"{BRAND_NAME}  -  Subscribe",
        cfg.outro_seconds,
        work / "_outro.mp4",
    )

    run_ffmpeg(
        [
            "-i",
            str(intro),
            "-i",
            str(normalized),
            "-i",
            str(outro),
            "-filter_complex",
            "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
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
            str(dest),
        ]
    )

    for tmp in (intro, outro):
        tmp.unlink(missing_ok=True)
    return dest
