"""Stage 2: generate a scene-by-scene narration script from a topic."""

from __future__ import annotations

import logging

from config import Settings
from src.models import Script, Topic

logger = logging.getLogger(__name__)


def generate_script(topic: Topic, settings: Settings, *, target_minutes: int = 8) -> Script:
    """Produce a `Script` whose scenes each carry narration and an image prompt.

    Implement with an LLM (e.g. OpenAI or Anthropic) using `settings`.
    """
    logger.info("Generating ~%d minute script for: %s", target_minutes, topic.title)
    raise NotImplementedError("script generation is not implemented yet")
