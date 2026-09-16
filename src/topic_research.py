"""Stage 1: select the historical topic for a video.

Research itself happens in Cursor Composer while the script is authored; the
resulting summary, era and sources are stored on the script's `topic` field.
This stage only builds the `Topic` used to locate that script.
"""

from __future__ import annotations

import logging

from config import Settings
from src.models import Topic

logger = logging.getLogger(__name__)


def research_topic(title: str, settings: Settings) -> Topic:
    """Return a `Topic` for `title`; enriched details live in the script JSON."""
    logger.info("Selected topic: %s", title)
    return Topic(title=title.strip())
