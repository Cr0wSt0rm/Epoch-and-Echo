"""Command line entry points.

  python -m gi_radio validate
  python -m gi_radio export --json output/the-voice-in-the-hooch.script.json --markdown output/...md
  python -m gi_radio plan --build-dir build
  python -m gi_radio render --build-dir build [--placeholder --duration-scale 0.05] [--scenes S01 S08]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import Pipeline, PipelineConfig
from .schema import VideoScript, speech_seconds
from .script import get_script


def script_to_markdown(script: VideoScript) -> str:
    p = script.protagonist
    lines = [
        f"# {script.title}",
        "",
        f"_{script.logline}_",
        "",
        f"**Protagonist:** {p.first_name} {p.last_name}, {p.age_on_arrival}, {p.hometown}. "
        f"{p.unit}. {p.area_of_operations}. In-country {p.arrival_date.isoformat()}, "
        f"DEROS {p.deros_date.isoformat()} ({p.tour_days} days). Writes home to {', '.join(p.writes_home_to)}.",
        "",
        f"**Scenes:** {script.scene_count}  **Spoken words:** {script.total_word_count}  "
        f"**Scripted runtime:** {script.total_runtime_seconds / 60:.1f} min",
        "",
        "## Voices",
        "",
    ]
    for role, voice in script.voices.items():
        lines += [
            f"### {role.value}",
            "",
            f"- ElevenLabs voice: `{voice.voice_name}` (`${voice.voice_id_env}`, default `{voice.default_voice_id}`)",
            f"- Model `{voice.model_id}`, stability {voice.stability}, similarity {voice.similarity_boost}, "
            f"style {voice.style}, speed {voice.speed}, paragraph break {voice.paragraph_break_seconds}s",
            f"- Direction: {voice.performance_notes}",
            "",
        ]
    lines += ["## Color grade", "", f"**{script.color_grade.name}.** {script.color_grade.description}", ""]
    lines += ["## Scenes", ""]
    clock = 0.0
    for scene in script.scenes:
        start = f"{int(clock // 60):02d}:{int(clock % 60):02d}"
        clock += scene.duration_seconds
        lines += [
            f"### {scene.scene_id} - {scene.beat.value} - {scene.elevenlabs_voice.value} "
            f"({scene.word_count} words, {scene.duration_seconds:.0f}s, starts {start})",
            "",
            f"**Frame:** {scene.visual_subject}",
            "",
            f"**Enter:** {scene.transition_in.value}  **Grade:** {scene.grade_variant.value}",
            "",
            f"**SFX:** {'; '.join(scene.sfx_notes)}",
            "",
        ]
        prefix = "> RADIO: " if scene.elevenlabs_voice.value == "hannah_radio" else ""
        for paragraph in scene.narration_text.split("\n\n"):
            lines += [f"{prefix}{' '.join(paragraph.split())}", ""]
        lines += [f"**ComfyUI:** `{scene.comfyui_image_prompt}`", ""]
    return "\n".join(lines).rstrip() + "\n"


def cmd_validate(_: argparse.Namespace) -> int:
    script = get_script()
    words = script.total_word_count
    print(f"{script.title}: {script.scene_count} scenes, {words} spoken words")
    print(f"scripted runtime {script.total_runtime_seconds / 60:.1f} min "
          f"(speech alone {speech_seconds(' '.join(s.narration_text for s in script.scenes)) / 60:.1f} min at 125 wpm)")
    for scene in script.scenes:
        print(f"  {scene.scene_id} {scene.beat.value:20s} {scene.elevenlabs_voice.value:12s} "
              f"{scene.word_count:4d}w {scene.duration_seconds:5.0f}s  {scene.visual_subject}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    script = get_script()
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(script.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {args.json}")
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(script_to_markdown(script))
        print(f"wrote {args.markdown}")
    if not args.json and not args.markdown:
        print(json.dumps(script.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """Emit the FFmpeg stitch plan using scripted durations (no assets touched)."""

    from .render import build_stitch_plan

    script = get_script()
    durations = {scene.scene_id: scene.duration_seconds for scene in script.scenes}
    plan = build_stitch_plan(script, Path(args.build_dir), durations)
    out = Path(args.out) if args.out else None
    text = json.dumps(plan.model_dump(mode="json"), indent=2)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
        print(f"wrote {out} ({len(plan.clips)} clips, {plan.total_runtime_seconds / 60:.1f} min)")
    else:
        print(text)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    config = PipelineConfig(
        build_dir=Path(args.build_dir),
        placeholder_assets=args.placeholder,
        duration_scale=args.duration_scale,
        scene_ids=args.scenes,
        skip_existing=not args.force,
    )
    manifest = Pipeline(get_script(), config).run(render=not args.no_render)
    for entry in manifest.scenes:
        print(f"  {entry.scene_id} {entry.voice.value:12s} audio {entry.audio_duration_seconds:6.2f}s "
              f"clip {entry.clip_duration_seconds:6.2f}s")
    print(f"timeline {manifest.plan.total_runtime_seconds:.1f}s")
    if manifest.final_video:
        print(f"final video: {manifest.final_video}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gi_radio")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate").set_defaults(func=cmd_validate)

    export = sub.add_parser("export")
    export.add_argument("--json")
    export.add_argument("--markdown")
    export.set_defaults(func=cmd_export)

    plan = sub.add_parser("plan")
    plan.add_argument("--build-dir", default="build")
    plan.add_argument("--out")
    plan.set_defaults(func=cmd_plan)

    render = sub.add_parser("render")
    render.add_argument("--build-dir", default="build")
    render.add_argument("--placeholder", action="store_true")
    render.add_argument("--duration-scale", type=float, default=1.0)
    render.add_argument("--scenes", nargs="+")
    render.add_argument("--force", action="store_true")
    render.add_argument("--no-render", action="store_true", help="generate assets and plan only")
    render.set_defaults(func=cmd_render)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
