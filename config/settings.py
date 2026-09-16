"""Project settings, resolved output paths, and API-key loading.

Values are read from environment variables, which are populated from a `.env`
file at the project root (see `.env.example`). Only the standard library is
used here so the config layer works before any dependencies are installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


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
    """Filesystem layout for generated assets."""

    root: Path = PROJECT_ROOT
    output: Path = PROJECT_ROOT / "output"

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

    # Script generation
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # Voiceover
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    # Image generation
    stability_api_key: str = ""
    replicate_api_token: str = ""
    # Stock media
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
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
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
            stability_api_key=os.getenv("STABILITY_API_KEY", ""),
            replicate_api_token=os.getenv("REPLICATE_API_TOKEN", ""),
            pexels_api_key=os.getenv("PEXELS_API_KEY", ""),
            pixabay_api_key=os.getenv("PIXABAY_API_KEY", ""),
            youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
            youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
            youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
            youtube_channel_id=os.getenv("YOUTUBE_CHANNEL_ID", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            paths=Paths(output=output_path),
        )

    def missing_keys(self) -> list[str]:
        """Return the names of API credentials that are still blank."""
        credential_fields = (
            "openai_api_key",
            "anthropic_api_key",
            "elevenlabs_api_key",
            "stability_api_key",
            "replicate_api_token",
            "pexels_api_key",
            "pixabay_api_key",
            "youtube_client_id",
            "youtube_client_secret",
            "youtube_refresh_token",
        )
        return [name.upper() for name in credential_fields if not getattr(self, name)]


PATHS = Paths()


def get_settings() -> Settings:
    """Load settings from `.env` / the environment."""
    return Settings.from_env()
