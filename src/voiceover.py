"""Stage 3: synthesize narration audio for each scene into output/audio/."""

from __future__ import annotations

import logging
from pathlib import Path

from config import Settings
from src.models import Scene, Script

logger = logging.getLogger(__name__)


def synthesize_scene(scene: Scene, settings: Settings) -> Path:
    """Generate audio for one scene and return the written file path."""
    settings.paths.audio.mkdir(parents=True, exist_ok=True)
    target = settings.paths.audio / f"scene_{scene.index:03d}.mp3"
    logger.info("Synthesizing scene %d -> %s", scene.index, target)
    raise NotImplementedError("text-to-speech is not implemented yet")


def synthesize_script(script: Script, settings: Settings) -> Script:
    """Attach an `audio_path` to every scene in the script."""
    for scene in script.scenes:
        scene.audio_path = synthesize_scene(scene, settings)
    return script
