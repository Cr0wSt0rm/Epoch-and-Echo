"""Stage 3: synthesize narration audio for each scene with the ElevenLabs API.

Every scene's `narration` becomes exactly one MP3 in `output/audio/`, which is
recorded on the scene as `audio_path` for the video assembler.
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from config import Settings
from src.models import Scene, Script

logger = logging.getLogger(__name__)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
REQUEST_TIMEOUT_SECONDS = 180

# Tuned for a slow, theatrical read: high stability keeps pacing even, a touch
# of style lets the voice lean into suspense.
VOICE_SETTINGS = {
    "stability": 0.65,
    "similarity_boost": 0.8,
    "style": 0.35,
    "use_speaker_boost": True,
}


def _require_credentials(settings: Settings) -> None:
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    if not settings.elevenlabs_voice_id:
        raise RuntimeError("ELEVENLABS_VOICE_ID is not set")


def synthesize_scene(scene: Scene, settings: Settings) -> Path:
    """Generate audio for one scene's narration and return the written MP3 path."""
    _require_credentials(settings)
    settings.paths.audio.mkdir(parents=True, exist_ok=True)
    target = settings.paths.audio / f"scene_{scene.index:03d}.mp3"
    logger.info("Synthesizing scene %d -> %s", scene.index, target)

    response = requests.post(
        ELEVENLABS_TTS_URL.format(voice_id=settings.elevenlabs_voice_id),
        headers={
            "xi-api-key": settings.elevenlabs_api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        },
        json={
            "text": scene.narration,
            "model_id": settings.elevenlabs_model_id,
            "voice_settings": VOICE_SETTINGS,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    if not response.content:
        raise RuntimeError(f"ElevenLabs returned no audio for scene {scene.index}")
    target.write_bytes(response.content)
    return target


def synthesize_script(script: Script, settings: Settings) -> Script:
    """Attach an `audio_path` to every scene in the script."""
    for scene in script.scenes:
        scene.audio_path = synthesize_scene(scene, settings)
    return script
