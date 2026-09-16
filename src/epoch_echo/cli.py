"""Command-line entry point for the Epoch & Echo pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .config import VideoConfig
from .media import ffmpeg_available
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epoch-echo",
        description="Turn raw footage into an upload-ready Epoch & Echo episode.",
    )
    parser.add_argument("--version", action="version", version=f"epoch-echo {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Run the pipeline for one episode.")
    build.add_argument("--title", help="Episode title (required unless --config is given).")
    build.add_argument("--source", type=Path, help="Path to source footage.")
    build.add_argument("--subtitle", default="", help="Lower-third caption text.")
    build.add_argument("--description", default="", help="Video description.")
    build.add_argument("--tag", action="append", default=[], dest="tags", help="Add a tag (repeatable).")
    build.add_argument("--output-dir", type=Path, default=Path("out"), help="Output directory.")
    build.add_argument("--config", type=Path, help="Load an episode recipe from a YAML file.")
    build.add_argument("--demo", action="store_true", help="Use a generated demo clip as the source.")
    build.add_argument("--demo-seconds", type=int, default=5, help="Length of the demo clip.")

    sub.add_parser("doctor", help="Check that required tools are available.")
    return parser


def _config_from_args(args: argparse.Namespace) -> VideoConfig:
    if args.config:
        cfg = VideoConfig.from_yaml(args.config)
        if args.title:
            cfg.title = args.title
    else:
        if not args.title:
            raise SystemExit("error: --title is required unless --config is provided")
        cfg = VideoConfig(title=args.title)

    if args.source and not args.demo:
        cfg.source = args.source
    if args.demo:
        cfg.source = None
    if args.subtitle:
        cfg.subtitle = args.subtitle
    if args.description:
        cfg.description = args.description
    if args.tags:
        cfg.tags = args.tags
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.demo_seconds:
        cfg.demo_seconds = args.demo_seconds
    return cfg


def _cmd_doctor() -> int:
    ok = ffmpeg_available()
    status = "OK" if ok else "MISSING"
    print(f"ffmpeg/ffprobe: {status}")
    if not ok:
        print("  Install with: sudo apt-get install -y ffmpeg")
        return 1
    print("All required tools are available.")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _cmd_doctor()

    if args.command == "build":
        cfg = _config_from_args(args)
        result = run(cfg)
        print("\nArtifacts:")
        print(f"  video:     {result.video}")
        print(f"  thumbnail: {result.thumbnail}")
        print(f"  metadata:  {result.metadata}")
        print(f"  duration:  {result.duration:.2f}s @ {result.resolution}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
