"""Stage 1: select a historical topic and gather source material."""

from __future__ import annotations

import logging

from config import Settings
from src.models import Topic

logger = logging.getLogger(__name__)


def research_topic(title: str, settings: Settings) -> Topic:
    """Return a `Topic` populated with a summary and reference sources.

    Implement with an LLM and/or web search using the credentials in `settings`.
    """
    logger.info("Researching topic: %s", title)
    raise NotImplementedError("topic research is not implemented yet")
