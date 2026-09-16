"""Stage 2: load and validate the scene-by-scene narration script for a topic.

Scripts are written in Cursor Composer following the persona in `.cursorrules`
and saved as JSON under `episodes/<slug>.json`. This stage validates that file
against the typed `Script` schema so downstream API calls are safe.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from config import Settings
from src.models import CINEMATIC_STYLE, Script, Topic

logger = logging.getLogger(__name__)

SCRIPTWRITING_BRIEF = f"""You are an elite narrative scriptwriter for a history channel.

Write narration that is deeply engaging, slow-paced, theatrical, and filled with
suspense. Open curiosity gaps and resolve them late. Favour concrete sensory
detail over summary. Never use corporate or "AI-sounding" buzzwords such as
"delve", "testament", or "moreover".

Return a JSON document matching the `Script` schema in src/models.py:
- topic: {{title, summary, era, sources[]}}
- title, description, tags[]
- scenes[]: {{index (0-based, contiguous), narration, image_prompt}}

Each scene's narration is voiced as one continuous audio clip and paired with
exactly one image, so keep scenes to a single dramatic beat (roughly 40-90
words). Every image_prompt describes one still frame and must end with:
"{CINEMATIC_STYLE}"
"""


def slugify(text: str) -> str:
    """Turn a title into a safe filename stem."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "video"


def script_path_for(topic: Topic, settings: Settings) -> Path:
    return settings.paths.episodes / f"{slugify(topic.title)}.json"


def generate_script(topic: Topic, settings: Settings, *, script_path: Path | None = None) -> Script:
    """Return the validated `Script` for `topic`.

    The script JSON is authored in Cursor Composer using `SCRIPTWRITING_BRIEF`.
    Validation enforces the cinematic image style, the buzzword ban, and the
    contiguous scene ordering that the audio/image/stitching stages rely on.
    """
    path = Path(script_path) if script_path else script_path_for(topic, settings)
    if not path.is_file():
        raise FileNotFoundError(
            f"No script found at {path}. Author one in Cursor Composer using "
            "src.script_generator.SCRIPTWRITING_BRIEF and save it there."
        )
    logger.info("Loading script for %s from %s", topic.title, path)
    script = Script.from_json_file(path)
    logger.info("Validated script '%s' with %d scenes", script.title, len(script.scenes))
    return script
