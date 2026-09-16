"""Typed schema for the Vietnam GI radio-drama video pipeline.

Every scene maps exactly once through the chain
Narration Text -> Audio Generation -> Image Generation -> Video Stitching.
The models here guarantee that shape before any API is touched.
"""

from __future__ import annotations

import math
import re
from datetime import date
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

CINEMATIC_STYLE = (
    "Dark historical atmosphere, cinematic lighting, 8k resolution, "
    "oil painting aesthetic, moody and suspenseful."
)

FORBIDDEN_WORDS: frozenset[str] = frozenset(
    {
        "delve",
        "testament",
        "moreover",
        "tapestry",
        "landscape",
        "underscore",
        "pivotal",
        "embark",
        "nestled",
    }
)

MIN_RUNTIME_SECONDS = 15 * 60
# Slow theatrical pace after pauses. 125 is the midpoint of the 120-130 target.
THEATRICAL_WPM = 125
# A scene may never be timed faster than this; it would compress the read.
MAX_WPM = 130

_WORD_RE = re.compile(r"[A-Za-z0-9'\u2019\u00C0-\u1EF9-]+")


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def speech_seconds(text: str, wpm: int = THEATRICAL_WPM) -> float:
    return count_words(text) / wpm * 60.0


def find_forbidden_words(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(
        word
        for word in FORBIDDEN_WORDS
        if re.search(rf"\b{re.escape(word)}\w*", lowered)
    )


class VoiceRole(str, Enum):
    NARRATOR = "narrator"
    HANNAH_RADIO = "hannah_radio"


class EmotionalBeat(str, Enum):
    COLD_OPEN = "cold_open"
    LAST_ORDINARY_NIGHT = "last_ordinary_night"
    AIRCRAFT_DOOR_OPENS = "aircraft_door_opens"
    SHORT_TIMER_MATH = "short_timer_math"
    RADIO_INTERLUDE = "radio_interlude"
    LAND_AS_ENEMY = "land_as_enemy"
    MAIL_CALL = "mail_call"
    RADIO_AFTER_DARK = "radio_after_dark"
    SEARCH_AND_DESTROY = "search_and_destroy"
    NAME_ON_THE_RADIO = "name_on_the_radio"
    HOLIDAY_IN_THE_RAIN = "holiday_in_the_rain"
    SHORT_AND_SHORTER = "short_and_shorter"
    COMING_HOME = "coming_home"


# The eleven required beats. The first appearance of each must occur in this order.
REQUIRED_BEAT_ORDER: tuple[EmotionalBeat, ...] = (
    EmotionalBeat.LAST_ORDINARY_NIGHT,
    EmotionalBeat.AIRCRAFT_DOOR_OPENS,
    EmotionalBeat.SHORT_TIMER_MATH,
    EmotionalBeat.LAND_AS_ENEMY,
    EmotionalBeat.MAIL_CALL,
    EmotionalBeat.RADIO_AFTER_DARK,
    EmotionalBeat.SEARCH_AND_DESTROY,
    EmotionalBeat.NAME_ON_THE_RADIO,
    EmotionalBeat.HOLIDAY_IN_THE_RAIN,
    EmotionalBeat.SHORT_AND_SHORTER,
    EmotionalBeat.COMING_HOME,
)


class Transition(str, Enum):
    """How a scene enters. Maps onto FFmpeg xfade transition names."""

    CROSSFADE = "crossfade"
    FADE_BLACK = "fade_black"
    RADIO_DISSOLVE = "radio_dissolve"
    HARD_CUT = "hard_cut"


class GradeVariant(str, Enum):
    DAY_BRUISED = "day_bruised"
    NIGHT_RADIO = "night_radio"


class VoiceSettings(BaseModel):
    """ElevenLabs voice configuration for one role."""

    model_config = ConfigDict(frozen=True)

    role: VoiceRole
    voice_name: str = Field(min_length=1)
    voice_id_env: str = Field(
        min_length=1,
        description="Environment variable holding the ElevenLabs voice id.",
    )
    default_voice_id: str = Field(
        min_length=1,
        description="Fallback ElevenLabs voice id used when the env var is unset.",
    )
    model_id: str = "eleven_multilingual_v2"
    output_format: str = "mp3_44100_128"
    stability: float = Field(ge=0.0, le=1.0)
    similarity_boost: float = Field(ge=0.0, le=1.0)
    style: float = Field(ge=0.0, le=1.0)
    use_speaker_boost: bool = True
    speed: float = Field(ge=0.7, le=1.2)
    paragraph_break_seconds: float = Field(ge=0.0, le=3.0)
    performance_notes: str = Field(min_length=10)

    def api_voice_settings(self) -> dict[str, Any]:
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
            "speed": self.speed,
        }


class Scene(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    scene_id: str = Field(pattern=r"^S\d{2}$")
    beat: EmotionalBeat
    duration_seconds: float = Field(ge=4.0, le=240.0)
    narration_text: str = Field(min_length=20)
    elevenlabs_voice: VoiceRole
    sfx_notes: list[str] = Field(min_length=1)
    comfyui_image_prompt: str = Field(min_length=40)
    visual_subject: str = Field(min_length=5)
    transition_in: Transition = Transition.CROSSFADE
    grade_variant: GradeVariant = GradeVariant.DAY_BRUISED

    @computed_field  # type: ignore[prop-decorator]
    @property
    def word_count(self) -> int:
        return count_words(self.narration_text)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def asset_stem(self) -> str:
        return f"{self.scene_id}_{self.elevenlabs_voice.value}"

    @field_validator("comfyui_image_prompt")
    @classmethod
    def _must_carry_house_style(cls, value: str) -> str:
        if CINEMATIC_STYLE not in value:
            raise ValueError(
                "comfyui_image_prompt must contain the mandatory style string: "
                f"{CINEMATIC_STYLE!r}"
            )
        return value

    @field_validator("narration_text")
    @classmethod
    def _no_forbidden_words(cls, value: str) -> str:
        hits = find_forbidden_words(value)
        if hits:
            raise ValueError(f"narration_text uses forbidden words: {hits}")
        return value

    @field_validator("sfx_notes")
    @classmethod
    def _sfx_not_blank(cls, value: list[str]) -> list[str]:
        cleaned = [note.strip() for note in value]
        if any(not note for note in cleaned):
            raise ValueError("sfx_notes may not contain blank entries")
        return cleaned

    @model_validator(mode="after")
    def _not_compressed(self) -> "Scene":
        floor = speech_seconds(self.narration_text, wpm=MAX_WPM)
        if self.duration_seconds + 1e-6 < floor:
            raise ValueError(
                f"{self.scene_id}: duration {self.duration_seconds:.1f}s is faster than "
                f"{MAX_WPM} wpm for {self.word_count} words (needs >= {floor:.1f}s)"
            )
        return self


class Protagonist(BaseModel):
    model_config = ConfigDict(frozen=True)

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    age_on_arrival: int = Field(ge=18, le=25)
    hometown: str = Field(min_length=3)
    unit: str = Field(min_length=5)
    area_of_operations: str = Field(min_length=3)
    arrival_date: date
    deros_date: date
    writes_home_to: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_year_tour(self) -> "Protagonist":
        days = (self.deros_date - self.arrival_date).days
        if not 360 <= days <= 370:
            raise ValueError(f"tour must be ~365 days, got {days}")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tour_days(self) -> int:
        return (self.deros_date - self.arrival_date).days


class ColorGrade(BaseModel):
    """One cohesive grade for every frame, with a night/radio variant."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = Field(min_length=20)
    base_filter: str = Field(min_length=10, description="FFmpeg filter chain")
    night_radio_filter: str = Field(min_length=10, description="FFmpeg filter chain")

    def filter_for(self, variant: GradeVariant) -> str:
        if variant is GradeVariant.NIGHT_RADIO:
            return self.night_radio_filter
        return self.base_filter


class RenderSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    width: int = 1920
    height: int = 1080
    fps: int = 24
    crossfade_seconds: float = Field(default=1.25, gt=0.0, le=4.0)
    fade_black_seconds: float = Field(default=2.0, gt=0.0, le=6.0)
    radio_dissolve_seconds: float = Field(default=0.6, gt=0.0, le=3.0)
    ken_burns_max_zoom: float = Field(default=1.08, ge=1.0, le=1.3)
    audio_tail_hold_seconds: float = Field(default=2.5, ge=0.0, le=10.0)
    video_codec: str = "libx264"
    crf: int = Field(default=18, ge=0, le=51)
    preset: str = "medium"
    audio_bitrate: str = "192k"
    sample_rate: int = 48000
    comfyui_width: int = 1344
    comfyui_height: int = 768
    radio_filter: str = Field(
        default=(
            "highpass=f=300,lowpass=f=3400,"
            "acompressor=threshold=-20dB:ratio=4:attack=5:release=80,"
            "tremolo=f=0.35:d=0.12,volume=1.3"
        ),
        description="Applied to every hannah_radio line before mixing in pink-noise hiss.",
    )
    radio_hiss_amplitude: float = Field(default=0.012, ge=0.0, le=0.2)


class VideoScript(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=3)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    logline: str = Field(min_length=20)
    protagonist: Protagonist
    voices: dict[VoiceRole, VoiceSettings]
    scenes: list[Scene] = Field(min_length=1)
    color_grade: ColorGrade
    render: RenderSettings = RenderSettings()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_runtime_seconds(self) -> float:
        return round(sum(scene.duration_seconds for scene in self.scenes), 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_word_count(self) -> int:
        return sum(scene.word_count for scene in self.scenes)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def scene_count(self) -> int:
        return len(self.scenes)

    @field_validator("voices")
    @classmethod
    def _both_roles_defined(cls, value: dict[VoiceRole, VoiceSettings]) -> dict:
        missing = [role.value for role in VoiceRole if role not in value]
        if missing:
            raise ValueError(f"voices missing roles: {missing}")
        for role, settings in value.items():
            if settings.role is not role:
                raise ValueError(f"voice keyed {role.value} is configured as {settings.role.value}")
        return value

    @model_validator(mode="after")
    def _structure(self) -> "VideoScript":
        ids = [scene.scene_id for scene in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("scene_id values must be unique")
        if ids != sorted(ids):
            raise ValueError("scenes must be listed in ascending scene_id order")

        used = {scene.elevenlabs_voice for scene in self.scenes}
        if used != set(VoiceRole):
            raise ValueError("both narrator and hannah_radio must be used by at least one scene")

        if self.total_runtime_seconds < MIN_RUNTIME_SECONDS:
            raise ValueError(
                f"total runtime {self.total_runtime_seconds:.0f}s is under the "
                f"{MIN_RUNTIME_SECONDS}s minimum"
            )

        first_seen: dict[EmotionalBeat, int] = {}
        for index, scene in enumerate(self.scenes):
            first_seen.setdefault(scene.beat, index)
        missing = [beat.value for beat in REQUIRED_BEAT_ORDER if beat not in first_seen]
        if missing:
            raise ValueError(f"required emotional beats missing: {missing}")
        positions = [first_seen[beat] for beat in REQUIRED_BEAT_ORDER]
        if positions != sorted(positions):
            raise ValueError("required emotional beats first appear out of order")
        return self

    def scene_by_id(self, scene_id: str) -> Scene:
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        raise KeyError(scene_id)

    def voice_for(self, scene: Scene) -> VoiceSettings:
        return self.voices[scene.elevenlabs_voice]


def timed(text: str, hold_seconds: float = 3.0, wpm: int = THEATRICAL_WPM) -> float:
    """Scene duration for a narration at theatrical pace plus a silent hold."""

    return float(math.ceil(speech_seconds(text, wpm=wpm) + hold_seconds))
