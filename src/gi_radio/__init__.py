"""gi_radio: typed ElevenLabs + ComfyUI + FFmpeg pipeline for "The Voice in the Hooch"."""

from .schema import (
    CINEMATIC_STYLE,
    ColorGrade,
    EmotionalBeat,
    Scene,
    VideoScript,
    VoiceRole,
    VoiceSettings,
)
from .script import get_script

__all__ = [
    "CINEMATIC_STYLE",
    "ColorGrade",
    "EmotionalBeat",
    "Scene",
    "VideoScript",
    "VoiceRole",
    "VoiceSettings",
    "get_script",
]
