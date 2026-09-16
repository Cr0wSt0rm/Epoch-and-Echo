"""End-to-end orchestration of the Epoch & Echo video pipeline.

Stages run in order:

    ingest -> transcode (normalize) -> branding (intro/outro) ->
    thumbnail -> metadata

Each stage writes into the run's output directory and the final artifacts are
returned in a :class:`PipelineResult`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import VideoConfig
from .media import MediaInfo, ffmpeg_available, probe
from .stages import branding, ingest, metadata, thumbnail, transcode

log = logging.getLogger("epoch_echo")


@dataclass
class PipelineResult:
    video: Path
    thumbnail: Path
    metadata: Path
    duration: float
    resolution: str


def run(cfg: VideoConfig) -> PipelineResult:
    """Execute the full pipeline for ``cfg`` and return the produced artifacts."""
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg/ffprobe are required but were not found on PATH. "
            "Install the 'ffmpeg' package and re-run."
        )

    out = Path(cfg.output_dir) / cfg.slug
    out.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", out)

    log.info("[1/5] Ingest")
    source, source_info = ingest.resolve_source(cfg, out)
    log.info("      source=%s %s %.2fs audio=%s",
             source.name, source_info.resolution, source_info.duration,
             source_info.has_audio)

    log.info("[2/5] Transcode / normalize")
    normalized = transcode.normalize(source, source_info, cfg, out / "normalized.mp4")
    content_info = probe(normalized)

    log.info("[3/5] Branding (intro + outro)")
    final_video = branding.add_bookends(normalized, cfg, out / f"{cfg.slug}.mp4")
    final_info: MediaInfo = probe(final_video)

    log.info("[4/5] Thumbnail")
    thumb = thumbnail.create(final_video, final_info, cfg, out / f"{cfg.slug}.png")

    log.info("[5/5] Metadata")
    meta = metadata.build(cfg, final_info, content_info.duration, out / "metadata.json")

    normalized.unlink(missing_ok=True)

    log.info("Done: %s (%.2fs, %s)", final_video.name, final_info.duration,
             final_info.resolution)
    return PipelineResult(
        video=final_video,
        thumbnail=thumb,
        metadata=meta,
        duration=final_info.duration,
        resolution=final_info.resolution,
    )
