"""Project settings, resolved output paths, and API-key loading.

Values are read from environment variables, which are populated from a `.env`
file at the project root (see `.env.example`). Only the standard library is
used here so the config layer works before any dependencies are installed.

The stack is fixed by `.cursorrules`: ElevenLabs (audio), ComfyUI (images),
FFmpeg (rendering). Scripts are authored in Cursor Composer, so no LLM vendor
credentials are needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"


def load_dotenv(path: Path = ENV_FILE, *, override: bool = False) -> None:
    """Populate `os.environ` from a simple KEY=VALUE `.env` file.

    Existing environment variables win unless `override` is True. Missing files
    are ignored so the pipeline can run purely off real environment variables.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Paths:
    """Filesystem layout for scripts and generated assets."""

    root: Path = PROJECT_ROOT
    output: Path = PROJECT_ROOT / "output"

    @property
    def episodes(self) -> Path:
        """Cursor-authored, Pydantic-validated script JSON files."""
        return self.root / "episodes"

    @property
    def audio(self) -> Path:
        return self.output / "audio"

    @property
    def images(self) -> Path:
        return self.output / "images"

    @property
    def final_videos(self) -> Path:
        return self.output / "final_videos"

    def ensure(self) -> None:
        """Create all output directories if they do not exist."""
        for directory in (self.audio, self.images, self.final_videos):
            directory.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    """API credentials and runtime options for the pipeline."""

    # Voiceover (ElevenLabs)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = DEFAULT_ELEVENLABS_MODEL_ID
    # Image generation (ComfyUI)
    comfyui_url: str = DEFAULT_COMFYUI_URL
    comfyui_checkpoint: str = ""
    comfyui_workflow: Path | None = None
    # Video rendering (FFmpeg)
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    # YouTube upload
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""
    youtube_channel_id: str = ""
    # Runtime
    log_level: str = "INFO"
    paths: Paths = field(default_factory=Paths)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        output_dir = os.getenv("OUTPUT_DIR", "output")
        output_path = Path(output_dir)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        workflow = os.getenv("COMFYUI_WORKFLOW", "").strip()
        workflow_path = Path(workflow) if workflow else None
        if workflow_path is not None and not workflow_path.is_absolute():
            workflow_path = PROJECT_ROOT / workflow_path
        return cls(
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_ELEVENLABS_MODEL_ID),
            comfyui_url=os.getenv("COMFYUI_URL", DEFAULT_COMFYUI_URL).rstrip("/"),
            comfyui_checkpoint=os.getenv("COMFYUI_CHECKPOINT", ""),
            comfyui_workflow=workflow_path,
            ffmpeg_binary=os.getenv("FFMPEG_BINARY", "ffmpeg"),
            ffprobe_binary=os.getenv("FFPROBE_BINARY", "ffprobe"),
            youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
            youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
            youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
            youtube_channel_id=os.getenv("YOUTUBE_CHANNEL_ID", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            paths=Paths(output=output_path),
        )

    def missing_keys(self) -> list[str]:
        """Return the names of credentials that are still blank."""
        credential_fields = (
            "elevenlabs_api_key",
            "elevenlabs_voice_id",
            "comfyui_checkpoint",
            "youtube_client_id",
            "youtube_client_secret",
            "youtube_refresh_token",
        )
        return [name.upper() for name in credential_fields if not getattr(self, name)]


PATHS = Paths()


def get_settings() -> Settings:
    """Load settings from `.env` / the environment."""
    return Settings.from_env()
