"""Stage 6: publish the rendered video to YouTube."""

from __future__ import annotations

import logging

from config import Settings
from src.models import VideoAsset

logger = logging.getLogger(__name__)


def upload_video(asset: VideoAsset, settings: Settings, *, privacy: str = "private") -> str:
    """Upload `asset` via the YouTube Data API and return the new video ID."""
    logger.info("Uploading %s (privacy=%s)", asset.video_path, privacy)
    raise NotImplementedError("YouTube upload is not implemented yet")
