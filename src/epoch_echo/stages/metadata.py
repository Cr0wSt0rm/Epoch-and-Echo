"""Produce the upload metadata sidecar (title, description, tags, chapters)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..config import BRAND_NAME, VideoConfig
from ..media import MediaInfo

DEFAULT_TAGS = ["epoch and echo", "history", "storytelling"]


def _format_timestamp(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def build(
    cfg: VideoConfig,
    final_info: MediaInfo,
    content_duration: float,
    dest: Path,
) -> Path:
    """Write a metadata.json describing the finished upload."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    intro_end = cfg.intro_seconds
    content_end = cfg.intro_seconds + content_duration
    chapters = [
        {"start": _format_timestamp(0.0), "title": "Intro"},
        {"start": _format_timestamp(intro_end), "title": "Episode"},
        {"start": _format_timestamp(content_end), "title": "Outro"},
    ]

    tags = cfg.tags or DEFAULT_TAGS
    description_lines = [
        cfg.description or f"{cfg.title} — a new episode from {BRAND_NAME}.",
        "",
        "Chapters:",
        *[f"{c['start']} {c['title']}" for c in chapters],
        "",
        f"Produced with the {BRAND_NAME} video pipeline.",
    ]

    payload = {
        "title": f"{cfg.title} | {BRAND_NAME}",
        "channel": BRAND_NAME,
        "description": "\n".join(description_lines),
        "tags": tags,
        "category": "Education",
        "visibility": "private",
        "duration_seconds": final_info.duration,
        "duration_human": _format_timestamp(final_info.duration),
        "resolution": final_info.resolution,
        "chapters": chapters,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest
