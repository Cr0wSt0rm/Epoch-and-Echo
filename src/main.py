"""Pipeline entry point.

Usage:
    python -m src.main "The Fall of Constantinople"
    python -m src.main --check-env
"""

from __future__ import annotations

import argparse
import logging
import sys

from config import Settings, get_settings
from src import image_generator, script_generator, topic_research, uploader, video_assembler, voiceover
from src.models import VideoAsset


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def run_pipeline(topic_title: str, settings: Settings, *, upload: bool = False) -> VideoAsset:
    """Run every stage in order and return the finished video asset."""
    settings.paths.ensure()
    topic = topic_research.research_topic(topic_title, settings)
    script = script_generator.generate_script(topic, settings)
    script = voiceover.synthesize_script(script, settings)
    script = image_generator.generate_script_images(script, settings)
    asset = video_assembler.assemble_video(script, settings)
    if upload:
        uploader.upload_video(asset, settings)
    return asset


def check_env(settings: Settings) -> int:
    """Print the output layout and any blank credentials; return an exit code."""
    settings.paths.ensure()
    print("Output directories:")
    for name in ("audio", "images", "final_videos"):
        print(f"  {name:<13} {getattr(settings.paths, name)}")
    missing = settings.missing_keys()
    if missing:
        print("\nBlank API keys (fill these in .env):")
        for key in missing:
            print(f"  - {key}")
        return 1
    print("\nAll API keys are set.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube history video automation pipeline")
    parser.add_argument("topic", nargs="?", help="historical topic to turn into a video")
    parser.add_argument("--upload", action="store_true", help="upload the finished video to YouTube")
    parser.add_argument("--check-env", action="store_true", help="verify folders and API keys, then exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)

    if args.check_env:
        return check_env(settings)
    if not args.topic:
        build_parser().print_help()
        return 2

    asset = run_pipeline(args.topic, settings, upload=args.upload)
    print(f"Finished: {asset.video_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
