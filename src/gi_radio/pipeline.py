"""Orchestrates the exact per-scene chain:
Narration Text -> Audio Generation -> Image Generation -> Video Stitching."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .audio import (
    AudioGenerator,
    ElevenLabsAudioGenerator,
    PlaceholderAudioGenerator,
    probe_duration_seconds,
)
from .images import ComfyUIImageGenerator, ImageGenerator, PlaceholderImageGenerator
from .render import FFmpegStitchPlan, build_stitch_plan, run_plan
from .schema import Scene, VideoScript, VoiceRole


class PipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    build_dir: Path
    placeholder_audio: bool = Field(
        default=False, description="Generate tones sized to the narration instead of calling ElevenLabs."
    )
    placeholder_images: bool = Field(
        default=False, description="Generate flat frames instead of calling ComfyUI."
    )
    duration_scale: float = Field(
        default=1.0,
        gt=0.0,
        le=1.0,
        description="Preview shrink factor applied to scripted durations (placeholder audio only).",
    )
    preset: str | None = Field(
        default=None, description="Override the x264 preset from RenderSettings (e.g. veryfast for drafts)."
    )
    scene_ids: list[str] | None = Field(
        default=None, description="Restrict the run to these scenes, in script order."
    )
    skip_existing: bool = True
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"


class SceneAssets(BaseModel):
    model_config = ConfigDict(frozen=True)

    scene_id: str
    voice: VoiceRole
    narration_words: int
    audio_path: str
    audio_duration_seconds: float
    image_path: str
    clip_path: str
    clip_duration_seconds: float


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    scenes: list[SceneAssets]
    plan: FFmpegStitchPlan
    final_video: str | None = None


class Pipeline:
    def __init__(
        self,
        script: VideoScript,
        config: PipelineConfig,
        audio: AudioGenerator | None = None,
        images: ImageGenerator | None = None,
    ) -> None:
        if config.preset:
            script = script.model_copy(update={"render": script.render.model_copy(update={"preset": config.preset})})
        self.script = script
        self.config = config
        if audio is None:
            audio = (
                PlaceholderAudioGenerator(config.duration_scale, config.ffmpeg)
                if config.placeholder_audio
                else ElevenLabsAudioGenerator()
            )
        if images is None:
            images = (
                PlaceholderImageGenerator(config.ffmpeg)
                if config.placeholder_images
                else ComfyUIImageGenerator()
            )
        self.audio = audio
        self.images = images

    @property
    def selected_scenes(self) -> list[Scene]:
        if self.config.scene_ids is None:
            return list(self.script.scenes)
        wanted = set(self.config.scene_ids)
        return [scene for scene in self.script.scenes if scene.scene_id in wanted]

    def _audio_path(self, scene: Scene) -> Path:
        return self.config.build_dir / "audio" / f"{scene.asset_stem}.mp3"

    def _image_path(self, scene: Scene) -> Path:
        return self.config.build_dir / "images" / f"{scene.asset_stem}.png"

    def clip_duration(self, scene: Scene, audio_seconds: float) -> float:
        scripted = scene.duration_seconds * (
            self.config.duration_scale if self.config.placeholder_audio else 1.0
        )
        return round(max(scripted, audio_seconds + self.script.render.audio_tail_hold_seconds), 3)

    def generate_assets(self) -> dict[str, tuple[Path, Path, float]]:
        """Step 1 and 2 for every scene: narration -> audio, prompt -> image."""

        produced: dict[str, tuple[Path, Path, float]] = {}
        for scene in self.selected_scenes:
            audio_path = self._audio_path(scene)
            if not (self.config.skip_existing and audio_path.exists()):
                self.audio.generate(scene, self.script.voice_for(scene), audio_path)
            image_path = self._image_path(scene)
            if not (self.config.skip_existing and image_path.exists()):
                self.images.generate(scene, self.script.render, image_path)
            produced[scene.scene_id] = (
                audio_path,
                image_path,
                probe_duration_seconds(audio_path, self.config.ffprobe),
            )
        return produced

    def plan(self, produced: dict[str, tuple[Path, Path, float]]) -> FFmpegStitchPlan:
        """Step 3 for every scene plus the timeline: build (not run) the FFmpeg plan."""

        selected = self.selected_scenes
        durations = {
            scene.scene_id: self.clip_duration(scene, produced[scene.scene_id][2]) for scene in selected
        }
        subset = self.script.model_copy(update={"scenes": selected}) if self.config.scene_ids else self.script
        return build_stitch_plan(subset, self.config.build_dir, durations, ffmpeg=self.config.ffmpeg)

    def run(self, render: bool = True) -> Manifest:
        self.config.build_dir.mkdir(parents=True, exist_ok=True)
        produced = self.generate_assets()
        plan = self.plan(produced)
        final: str | None = None
        if render:
            final = str(run_plan(plan, self.config.build_dir))

        scenes = [
            SceneAssets(
                scene_id=clip.scene_id,
                voice=clip.voice,
                narration_words=self.script.scene_by_id(clip.scene_id).word_count,
                audio_path=clip.audio_path,
                audio_duration_seconds=round(produced[clip.scene_id][2], 3),
                image_path=clip.image_path,
                clip_path=clip.clip_path,
                clip_duration_seconds=clip.clip_duration_seconds,
            )
            for clip in plan.clips
        ]
        manifest = Manifest(slug=self.script.slug, scenes=scenes, plan=plan, final_video=final)
        (self.config.build_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2)
        )
        return manifest
