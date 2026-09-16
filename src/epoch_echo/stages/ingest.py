"""Resolve and validate the pipeline's input footage."""

from __future__ import annotations

from pathlib import Path

from ..config import VideoConfig
from ..media import MediaInfo, generate_test_clip, probe


def resolve_source(cfg: VideoConfig, work_dir: Path) -> tuple[Path, MediaInfo]:
    """Return the source clip and its probed info.

    When no source is configured, a synthetic demo clip is generated so the
    pipeline can always run end to end (useful for demos, CI, and tests).
    """
    if cfg.source is not None:
        source = Path(cfg.source)
        if not source.exists():
            raise FileNotFoundError(f"Source footage not found: {source}")
    else:
        source = generate_test_clip(work_dir / "_demo_source.mp4", cfg.demo_seconds)

    return source, probe(source)
