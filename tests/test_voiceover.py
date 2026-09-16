from __future__ import annotations

from dataclasses import replace

import pytest

from src import voiceover
from src.models import Scene


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_synthesize_scene_calls_elevenlabs_and_writes_mp3(settings, monkeypatch):
    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse(b"ID3fake-mp3")

    monkeypatch.setattr(voiceover.requests, "post", fake_post)
    scene = Scene(index=2, narration="The gate stood open.", image_prompt="A gate")

    path = voiceover.synthesize_scene(scene, settings)

    assert path == settings.paths.audio / "scene_002.mp3"
    assert path.read_bytes() == b"ID3fake-mp3"
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://api.elevenlabs.io/v1/text-to-speech/test-voice"
    assert call["headers"]["xi-api-key"] == "test-key"
    assert call["json"]["text"] == "The gate stood open."
    assert call["json"]["model_id"] == settings.elevenlabs_model_id


def test_synthesize_script_maps_every_scene_to_audio(settings, monkeypatch):
    monkeypatch.setattr(voiceover.requests, "post", lambda url, **kw: FakeResponse(b"audio"))
    from src.models import Script, Topic

    script = Script(
        topic=Topic(title="T"),
        title="T",
        scenes=[Scene(index=i, narration=f"Beat {i}.", image_prompt="frame") for i in range(3)],
    )
    voiceover.synthesize_script(script, settings)
    assert [s.audio_path.name for s in script.scenes] == [
        "scene_000.mp3",
        "scene_001.mp3",
        "scene_002.mp3",
    ]


def test_missing_credentials_fail_before_any_request(settings, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("network call should not happen")

    monkeypatch.setattr(voiceover.requests, "post", fail)
    scene = Scene(index=0, narration="x", image_prompt="y")
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        voiceover.synthesize_scene(scene, replace(settings, elevenlabs_api_key=""))
    with pytest.raises(RuntimeError, match="ELEVENLABS_VOICE_ID"):
        voiceover.synthesize_scene(scene, replace(settings, elevenlabs_voice_id=""))
