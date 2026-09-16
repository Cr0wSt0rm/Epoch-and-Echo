"""FFmpeg stitch plan: one still + one narration -> one clip per scene, then a
single crossfaded timeline with the house grade and a radio filter on Hannah."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .schema import (
    ColorGrade,
    RenderSettings,
    Scene,
    Transition,
    VideoScript,
    VoiceRole,
)

XFADE_NAMES: dict[Transition, str] = {
    Transition.CROSSFADE: "fade",
    Transition.FADE_BLACK: "fadeblack",
    Transition.RADIO_DISSOLVE: "dissolve",
    Transition.HARD_CUT: "fade",
}


def transition_seconds(transition: Transition, render: RenderSettings) -> float:
    if transition is Transition.FADE_BLACK:
        return render.fade_black_seconds
    if transition is Transition.RADIO_DISSOLVE:
        return render.radio_dissolve_seconds
    if transition is Transition.HARD_CUT:
        return 0.08
    return render.crossfade_seconds


class ClipJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    scene_id: str
    voice: VoiceRole
    image_path: str
    audio_path: str
    clip_path: str
    clip_duration_seconds: float = Field(gt=0)
    transition_in: Transition
    transition_in_seconds: float = Field(ge=0)
    radio_filter_applied: bool
    video_filter: str
    audio_filter: str
    command: list[str]

    @property
    def shell(self) -> str:
        return shlex.join(self.command)


class FFmpegStitchPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_path: str
    width: int
    height: int
    fps: int
    scene_order: list[str]
    clips: list[ClipJob]
    crossfade_command: list[str]
    fallback_concat_list: str
    fallback_concat_command: list[str]
    total_runtime_seconds: float
    color_grade_base: str
    color_grade_night_radio: str
    radio_filter: str
    notes: list[str]

    @property
    def crossfade_shell(self) -> str:
        return shlex.join(self.crossfade_command)


def video_filter_for(scene: Scene, render: RenderSettings, grade: ColorGrade, frames: int) -> str:
    w, h = render.width, render.height
    zoom = render.ken_burns_max_zoom
    return (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"zoompan=z='1+({zoom}-1)*on/{frames}':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={render.fps},"
        f"{grade.filter_for(scene.grade_variant)},"
        "format=yuv420p,setsar=1[v]"
    )


def audio_filter_for(scene: Scene, render: RenderSettings, duration: float) -> str:
    sr = render.sample_rate
    fade_out_start = max(0.0, duration - 1.0)
    tail = f"apad,atrim=0:{duration:.3f},afade=t=in:st=0:d=0.25,afade=t=out:st={fade_out_start:.3f}:d=1.0[a]"
    if scene.elevenlabs_voice is VoiceRole.HANNAH_RADIO:
        return (
            f"[1:a]aresample={sr},{render.radio_filter}[voice];"
            f"anoisesrc=r={sr}:color=pink:amplitude={render.radio_hiss_amplitude}:d={duration:.3f}[hiss];"
            f"[voice][hiss]amix=inputs=2:duration=longest:normalize=0,{tail}"
        )
    return f"[1:a]aresample={sr},{tail}"


def clip_command(
    scene: Scene,
    render: RenderSettings,
    grade: ColorGrade,
    image_path: Path,
    audio_path: Path,
    clip_path: Path,
    duration: float,
    ffmpeg: str = "ffmpeg",
) -> tuple[list[str], str, str]:
    frames = max(1, round(duration * render.fps))
    vf = video_filter_for(scene, render, grade, frames)
    af = audio_filter_for(scene, render, duration)
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-filter_complex", f"{vf};{af}",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{duration:.3f}",
        "-r", str(render.fps),
        "-c:v", render.video_codec, "-preset", render.preset, "-crf", str(render.crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", render.audio_bitrate, "-ar", str(render.sample_rate),
        "-movflags", "+faststart",
        str(clip_path),
    ]
    return command, vf, af


def crossfade_command(
    clips: list[ClipJob],
    render: RenderSettings,
    output_path: Path,
    ffmpeg: str = "ffmpeg",
) -> tuple[list[str], float]:
    """Chain xfade/acrossfade across every clip in scene order.

    offset_k = (sum of clip durations before clip k) - (sum of transition lengths so far).
    The first clip fades in from black; the last fades out to black.
    """

    if not clips:
        raise ValueError("no clips to stitch")

    inputs: list[str] = []
    for clip in clips:
        inputs += ["-i", clip.clip_path]

    if len(clips) == 1:
        d = clips[0].clip_duration_seconds
        filter_graph = (
            f"[0:v]fade=t=in:d=1.5,fade=t=out:st={max(0.0, d - 2.5):.3f}:d=2.5[vout];"
            f"[0:a]acopy[aout]"
        )
        total = d
    else:
        parts: list[str] = [f"[0:v]fade=t=in:d=1.5[v0]"]
        vprev, aprev = "[v0]", "[0:a]"
        elapsed = clips[0].clip_duration_seconds
        for index, clip in enumerate(clips[1:], start=1):
            t = min(clip.transition_in_seconds, clips[index - 1].clip_duration_seconds / 2, clip.clip_duration_seconds / 2)
            offset = elapsed - t
            vout, aout = f"[v{index}]", f"[a{index}]"
            parts.append(
                f"{vprev}[{index}:v]xfade=transition={XFADE_NAMES[clip.transition_in]}"
                f":duration={t:.3f}:offset={offset:.3f}{vout}"
            )
            parts.append(f"{aprev}[{index}:a]acrossfade=d={t:.3f}:c1=tri:c2=tri{aout}")
            vprev, aprev = vout, aout
            elapsed = offset + clip.clip_duration_seconds
        total = elapsed
        parts.append(f"{vprev}fade=t=out:st={max(0.0, total - 2.5):.3f}:d=2.5[vout]")
        parts.append(f"{aprev}afade=t=out:st={max(0.0, total - 2.5):.3f}:d=2.5[aout]")
        filter_graph = ";".join(parts)

    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_graph,
        "-map", "[vout]", "-map", "[aout]",
        "-r", str(render.fps),
        "-c:v", render.video_codec, "-preset", render.preset, "-crf", str(render.crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", render.audio_bitrate, "-ar", str(render.sample_rate),
        "-movflags", "+faststart",
        str(output_path),
    ]
    return command, round(total, 3)


def build_stitch_plan(
    script: VideoScript,
    build_dir: Path,
    clip_durations: dict[str, float],
    output_name: str | None = None,
    ffmpeg: str = "ffmpeg",
) -> FFmpegStitchPlan:
    """Assemble the full plan. `clip_durations` are the real per-scene clip lengths
    (audio length + tail hold, never shorter than the scripted duration)."""

    render = script.render
    audio_dir, image_dir, clip_dir = build_dir / "audio", build_dir / "images", build_dir / "clips"
    output_path = build_dir / (output_name or f"{script.slug}.mp4")

    clips: list[ClipJob] = []
    for scene in script.scenes:
        duration = clip_durations[scene.scene_id]
        image_path = image_dir / f"{scene.asset_stem}.png"
        audio_path = audio_dir / f"{scene.asset_stem}.mp3"
        clip_path = clip_dir / f"{scene.asset_stem}.mp4"
        command, vf, af = clip_command(
            scene, render, script.color_grade, image_path, audio_path, clip_path, duration, ffmpeg
        )
        clips.append(
            ClipJob(
                scene_id=scene.scene_id,
                voice=scene.elevenlabs_voice,
                image_path=str(image_path),
                audio_path=str(audio_path),
                clip_path=str(clip_path),
                clip_duration_seconds=round(duration, 3),
                transition_in=scene.transition_in,
                transition_in_seconds=transition_seconds(scene.transition_in, render),
                radio_filter_applied=scene.elevenlabs_voice is VoiceRole.HANNAH_RADIO,
                video_filter=vf,
                audio_filter=af,
                command=command,
            )
        )

    xfade_cmd, total = crossfade_command(clips, render, output_path, ffmpeg)
    concat_list = "".join(f"file '{clip.clip_path}'\n" for clip in clips)
    concat_list_path = build_dir / "concat.txt"
    fallback = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
        "-c", "copy", str(build_dir / f"{script.slug}.hardcut.mp4"),
    ]

    notes = [
        "Scene order is scene_id order; every scene yields exactly one still, one narration file, one clip.",
        "Per-clip: still is scaled/cropped to frame, given a slow Ken Burns push "
        f"(max zoom {render.ken_burns_max_zoom}), then graded. Narrator scenes use the base grade; "
        "night/radio scenes use the cold-blue variant.",
        f"Hannah lines: {render.radio_filter} then pink-noise hiss mixed under at "
        f"amplitude {render.radio_hiss_amplitude}. Narrator lines are left clean.",
        "Transitions: crossfade (xfade=fade) by default; fadeblack for chapter breaks; "
        "dissolve for radio cut-ins; acrossfade with matching length on audio.",
        "First clip fades in from black over 1.5s; final frame fades to black over 2.5s and audio follows.",
        "Fallback: concat demuxer with stream copy produces a hard-cut assembly if xfade memory is a problem.",
    ]

    return FFmpegStitchPlan(
        output_path=str(output_path),
        width=render.width,
        height=render.height,
        fps=render.fps,
        scene_order=[scene.scene_id for scene in script.scenes],
        clips=clips,
        crossfade_command=xfade_cmd,
        fallback_concat_list=concat_list,
        fallback_concat_command=fallback,
        total_runtime_seconds=total,
        color_grade_base=script.color_grade.base_filter,
        color_grade_night_radio=script.color_grade.night_radio_filter,
        radio_filter=render.radio_filter,
        notes=notes,
    )


def run_plan(plan: FFmpegStitchPlan, build_dir: Path) -> Path:
    (build_dir / "clips").mkdir(parents=True, exist_ok=True)
    for clip in plan.clips:
        subprocess.run(clip.command, check=True)
    (build_dir / "concat.txt").write_text(plan.fallback_concat_list)
    subprocess.run(plan.crossfade_command, check=True)
    return Path(plan.output_path)
