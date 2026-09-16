"""Stage 5: combine scene audio and images into a video in output/final_videos/."""

from __future__ import annotations

import logging
import re

from config import Settings
from src.models import Script, VideoAsset

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Turn a title into a safe filename stem."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "video"


def assemble_video(script: Script, settings: Settings) -> VideoAsset:
    """Render the final video (e.g. with moviepy or ffmpeg) and return its asset."""
    settings.paths.final_videos.mkdir(parents=True, exist_ok=True)
    target = settings.paths.final_videos / f"{slugify(script.title)}.mp4"
    logger.info("Assembling video -> %s", target)
    raise NotImplementedError("video assembly is not implemented yet")
