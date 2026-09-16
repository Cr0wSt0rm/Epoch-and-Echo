"""Generate a 1280x720 YouTube thumbnail from the finished video.

A representative frame is grabbed with ffmpeg, then Pillow adds a darkening
gradient, the episode title, and the channel brand line.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import BRAND_ACCENT, BRAND_NAME, VideoConfig
from ..fonts import find_bold_font
from ..media import MediaInfo, run_ffmpeg

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def _grab_frame(video: Path, at_seconds: float, dest: Path) -> Path:
    run_ffmpeg(
        [
            "-ss",
            f"{at_seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(dest),
        ]
    )
    return dest


def create(video: Path, info: MediaInfo, cfg: VideoConfig, dest: Path) -> Path:
    """Create a branded thumbnail for ``video`` at ``dest``."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame_path = dest.parent / "_frame.png"
    grab_at = min(max(info.duration * 0.5, 0.0), max(info.duration - 0.1, 0.0))
    _grab_frame(video, grab_at, frame_path)

    base = Image.open(frame_path).convert("RGB").resize((THUMB_WIDTH, THUMB_HEIGHT))

    # Darken the lower portion so text stays legible over any footage.
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(THUMB_HEIGHT):
        alpha = int(200 * (y / THUMB_HEIGHT) ** 2)
        odraw.line([(0, y), (THUMB_WIDTH, y)], fill=(6, 15, 33, alpha))
    base = Image.alpha_composite(base.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(base)
    font_path = str(find_bold_font())
    title_font = ImageFont.truetype(font_path, 84)
    brand_font = ImageFont.truetype(font_path, 40)

    wrapped = textwrap.fill(cfg.title, width=18)
    margin = 60
    y = THUMB_HEIGHT - margin
    for line in reversed(wrapped.split("\n")):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_h = bbox[3] - bbox[1]
        y -= line_h + 14
        draw.text(
            (margin, y),
            line,
            font=title_font,
            fill="white",
            stroke_width=3,
            stroke_fill=(6, 15, 33),
        )

    accent = tuple(int(BRAND_ACCENT.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    draw.text((margin, margin), BRAND_NAME, font=brand_font, fill=accent)

    base.convert("RGB").save(dest, "PNG")
    frame_path.unlink(missing_ok=True)
    return dest
