"""Configuration model for a pipeline run.

A run is described by a small, serializable :class:`VideoConfig`. It can be
built from CLI arguments or loaded from a YAML file so the same episode recipe
can be checked into the repo alongside the footage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# The channel's house style. Kept here so every stage shares one source of truth.
BRAND_NAME = "Epoch & Echo"
BRAND_PRIMARY = "#0b1e3f"  # deep navy
BRAND_ACCENT = "#f4b41a"  # amber
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30


@dataclass
class VideoConfig:
    """Everything the pipeline needs to produce one episode."""

    title: str
    source: Path | None = None
    output_dir: Path = Path("out")
    subtitle: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    intro_seconds: float = 2.0
    outro_seconds: float = 2.0
    demo_seconds: int = 5

    @classmethod
    def from_yaml(cls, path: Path) -> "VideoConfig":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "VideoConfig":
        data = dict(raw)
        if data.get("source"):
            data["source"] = Path(data["source"])
        if data.get("output_dir"):
            data["output_dir"] = Path(data["output_dir"])
        allowed = cls.__dataclass_fields__.keys()
        unknown = set(data) - set(allowed)
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
        if not data.get("title"):
            raise ValueError("A 'title' is required.")
        return cls(**data)

    @property
    def slug(self) -> str:
        """A filesystem/URL-friendly identifier derived from the title."""
        keep = [c.lower() if c.isalnum() else "-" for c in self.title]
        slug = "".join(keep)
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug.strip("-") or "episode"
