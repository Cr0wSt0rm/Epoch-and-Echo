"""Shared data structures passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Topic:
    """A historical subject selected for a video."""

    title: str
    summary: str = ""
    era: str = ""
    sources: list[str] = field(default_factory=list)


@dataclass
class Scene:
    """One narrated beat of the video with its visual prompt."""

    index: int
    narration: str
    image_prompt: str
    audio_path: Path | None = None
    image_path: Path | None = None


@dataclass
class Script:
    """The complete video script, split into scenes."""

    topic: Topic
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)

    @property
    def full_narration(self) -> str:
        return "\n\n".join(scene.narration for scene in self.scenes)


@dataclass
class VideoAsset:
    """The rendered video ready for upload."""

    script: Script
    video_path: Path
    thumbnail_path: Path | None = None
    duration_seconds: float = 0.0
