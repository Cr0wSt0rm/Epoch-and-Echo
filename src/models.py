"""Typed Pydantic schema for the video script, shared by every pipeline stage.

The schema enforces the project rules in `.cursorrules`:

* every scene maps exactly Narration Text -> Audio -> Image -> Video Stitching,
* every ComfyUI image prompt carries the house cinematic style, and
* narration never contains "AI-sounding" buzzwords.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CINEMATIC_STYLE = (
    "Dark historical atmosphere, cinematic lighting, 8k resolution, "
    "oil painting aesthetic, moody and suspenseful."
)

BANNED_BUZZWORDS: tuple[str, ...] = ("delve", "testament", "moreover")

# Stems so inflections (delves, delved, delving, testaments) are caught too.
_BUZZWORD_STEMS: tuple[str, ...] = ("delv", "testament", "moreover")

_BUZZWORD_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(stem) for stem in _BUZZWORD_STEMS) + r")\w*\b",
    re.IGNORECASE,
)


def find_buzzwords(text: str) -> list[str]:
    """Return the banned buzzwords (and their inflections) present in `text`."""
    return sorted({match.group(0).lower() for match in _BUZZWORD_PATTERN.finditer(text)})


def apply_cinematic_style(prompt: str) -> str:
    """Return `prompt` with the mandatory ComfyUI style suffix appended once."""
    prompt = " ".join(prompt.split())
    if CINEMATIC_STYLE.lower() in prompt.lower():
        return prompt
    return f"{prompt.rstrip('.,;')}. {CINEMATIC_STYLE}"


class Topic(BaseModel):
    """A historical subject selected for a video."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = ""
    era: str = ""
    sources: list[str] = Field(default_factory=list)


class Scene(BaseModel):
    """One narrated beat of the video.

    `narration` is the source of truth; `audio_path` and `image_path` are filled
    in by the voiceover and image stages respectively, then consumed by the
    video assembler.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    index: int = Field(ge=0)
    narration: str = Field(min_length=1)
    image_prompt: str = Field(min_length=1)
    audio_path: Path | None = None
    image_path: Path | None = None

    @field_validator("narration")
    @classmethod
    def _reject_buzzwords(cls, value: str) -> str:
        value = value.strip()
        found = find_buzzwords(value)
        if found:
            raise ValueError(
                f"narration contains banned buzzword(s) {found}; "
                "rewrite in the theatrical, suspenseful house voice"
            )
        return value

    @field_validator("image_prompt")
    @classmethod
    def _enforce_cinematic_style(cls, value: str) -> str:
        return apply_cinematic_style(value)

    @property
    def is_voiced(self) -> bool:
        return self.audio_path is not None

    @property
    def is_illustrated(self) -> bool:
        return self.image_path is not None

    @property
    def is_render_ready(self) -> bool:
        """True once the scene has both assets the video stitcher needs."""
        return self.is_voiced and self.is_illustrated


class Script(BaseModel):
    """The complete video script, split into ordered scenes."""

    model_config = ConfigDict(extra="forbid")

    topic: Topic
    title: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def _scenes_are_contiguous(self) -> "Script":
        indices = [scene.index for scene in self.scenes]
        expected = list(range(len(self.scenes)))
        if indices != expected:
            raise ValueError(
                f"scene indices must be contiguous and ordered {expected}, got {indices}"
            )
        return self

    @property
    def full_narration(self) -> str:
        return "\n\n".join(scene.narration for scene in self.scenes)

    def require_render_ready(self) -> None:
        """Raise if any scene is missing the audio or image the stitcher needs."""
        missing = [
            f"scene {scene.index}: missing "
            + ", ".join(
                name
                for name, present in (("audio", scene.is_voiced), ("image", scene.is_illustrated))
                if not present
            )
            for scene in self.scenes
            if not scene.is_render_ready
        ]
        if missing:
            raise ValueError("script is not ready to stitch: " + "; ".join(missing))

    @classmethod
    def from_json_file(cls, path: Path) -> "Script":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def to_json_file(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


class VideoAsset(BaseModel):
    """The rendered video ready for upload."""

    model_config = ConfigDict(extra="forbid")

    script: Script
    video_path: Path
    thumbnail_path: Path | None = None
    duration_seconds: float = Field(default=0.0, ge=0.0)
