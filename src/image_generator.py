"""Stage 4: create a visual for each scene into output/images/."""

from __future__ import annotations

import logging
from pathlib import Path

from config import Settings
from src.models import Scene, Script

logger = logging.getLogger(__name__)


def generate_scene_image(scene: Scene, settings: Settings) -> Path:
    """Generate (or fetch) an image for one scene and return its path."""
    settings.paths.images.mkdir(parents=True, exist_ok=True)
    target = settings.paths.images / f"scene_{scene.index:03d}.png"
    logger.info("Generating image for scene %d -> %s", scene.index, target)
    raise NotImplementedError("image generation is not implemented yet")


def generate_script_images(script: Script, settings: Settings) -> Script:
    """Attach an `image_path` to every scene in the script."""
    for scene in script.scenes:
        scene.image_path = generate_scene_image(scene, settings)
    return script
