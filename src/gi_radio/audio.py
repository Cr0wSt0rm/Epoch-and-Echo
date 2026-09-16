"""ElevenLabs text-to-speech: one narration -> one audio file per scene."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Protocol

import requests

from .schema import Scene, VoiceSettings, speech_seconds

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_BREAK_TAG = '<break time="{seconds:.1f}s" />'


def narration_to_tts_text(text: str, voice: VoiceSettings) -> str:
    """Turn paragraph breaks into explicit ElevenLabs break tags.

    Paragraph breaks in the script are deliberate silence. ElevenLabs treats blank
    lines loosely, so we make every one of them an explicit pause of the length the
    voice profile asks for.
    """

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    joined = [" ".join(p.split()) for p in paragraphs]
    pause = _BREAK_TAG.format(seconds=voice.paragraph_break_seconds)
    return f" {pause} ".join(joined)


class AudioGenerator(Protocol):
    def generate(self, scene: Scene, voice: VoiceSettings, out_path: Path) -> Path: ...


class ElevenLabsAudioGenerator:
    def __init__(self, api_key: str | None = None, timeout: float = 180.0) -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")
        self.timeout = timeout

    @staticmethod
    def resolve_voice_id(voice: VoiceSettings) -> str:
        return os.environ.get(voice.voice_id_env) or voice.default_voice_id

    def request_payload(self, scene: Scene, voice: VoiceSettings) -> dict:
        return {
            "text": narration_to_tts_text(scene.narration_text, voice),
            "model_id": voice.model_id,
            "voice_settings": voice.api_voice_settings(),
        }

    def generate(self, scene: Scene, voice: VoiceSettings, out_path: Path) -> Path:
        if scene.elevenlabs_voice is not voice.role:
            raise ValueError(f"{scene.scene_id} expects {scene.elevenlabs_voice.value}, got {voice.role.value}")
        url = ELEVENLABS_TTS_URL.format(voice_id=self.resolve_voice_id(voice))
        response = requests.post(
            url,
            params={"output_format": voice.output_format},
            headers={"xi-api-key": self.api_key, "accept": "audio/mpeg"},
            json=self.request_payload(scene, voice),
            timeout=self.timeout,
        )
        response.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        return out_path


class PlaceholderAudioGenerator:
    """Offline stand-in: a near-silent tone sized to the scene's speech length.

    Lets the whole pipeline (durations, radio filter, crossfades) be exercised
    without spending ElevenLabs credits.
    """

    def __init__(self, duration_scale: float = 1.0, ffmpeg: str = "ffmpeg") -> None:
        self.duration_scale = duration_scale
        self.ffmpeg = ffmpeg

    def generate(self, scene: Scene, voice: VoiceSettings, out_path: Path) -> Path:
        seconds = max(0.5, speech_seconds(scene.narration_text) * self.duration_scale)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # A low tone, different per voice, so the radio filter is audible in previews.
        frequency = 110 if voice.role.value == "narrator" else 660
        subprocess.run(
            [
                self.ffmpeg, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000",
                "-t", f"{seconds:.3f}", "-af", "volume=0.15",
                "-c:a", "libmp3lame", "-b:a", "128k", str(out_path),
            ],
            check=True,
        )
        return out_path


def probe_duration_seconds(path: Path, ffprobe: str = "ffprobe") -> float:
    result = subprocess.run(
        [
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())
