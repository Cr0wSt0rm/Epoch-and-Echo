from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src import image_generator
from src.image_generator import ComfyUIClient, build_workflow, load_custom_workflow
from src.models import CINEMATIC_STYLE, Scene


class FakeResponse:
    def __init__(self, payload=None, content: bytes = b"") -> None:
        self._payload = payload
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Simulates ComfyUI: /prompt queues, /history reports outputs, /view serves bytes."""

    def __init__(self) -> None:
        self.posted: list[dict] = []
        self.history_polls = 0

    def post(self, url, json=None, timeout=None):
        assert url.endswith("/prompt")
        self.posted.append(json)
        return FakeResponse({"prompt_id": "abc123", "number": 1})

    def get(self, url, params=None, timeout=None):
        if "/history/" in url:
            self.history_polls += 1
            if self.history_polls == 1:
                return FakeResponse({})
            return FakeResponse(
                {
                    "abc123": {
                        "status": {"status_str": "success"},
                        "outputs": {
                            "7": {"images": [{"filename": "epoch_echo_00001_.png", "subfolder": "", "type": "output"}]}
                        },
                    }
                }
            )
        assert url.endswith("/view")
        assert params == {"filename": "epoch_echo_00001_.png", "subfolder": "", "type": "output"}
        return FakeResponse(content=b"\x89PNGfake")


def test_default_workflow_uses_styled_prompt_and_checkpoint(settings):
    scene = Scene(index=0, narration="x", image_prompt="A gate at dawn")
    workflow = build_workflow(scene, "Title", settings)

    positive = workflow["2"]["inputs"]["text"]
    assert positive.endswith(CINEMATIC_STYLE)
    assert positive.startswith("A gate at dawn")
    assert workflow["1"]["inputs"]["ckpt_name"] == "test.safetensors"
    assert workflow["5"]["inputs"]["seed"] == image_generator.scene_seed("Title", 0)
    assert workflow["7"]["class_type"] == "SaveImage"


def test_default_workflow_requires_checkpoint(settings):
    scene = Scene(index=0, narration="x", image_prompt="y")
    with pytest.raises(RuntimeError, match="COMFYUI_CHECKPOINT"):
        build_workflow(scene, "Title", replace(settings, comfyui_checkpoint=""))


def test_custom_workflow_placeholder_substitution(tmp_path: Path, settings):
    template = {
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "__PROMPT__"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "__NEGATIVE_PROMPT__"}},
        "3": {"class_type": "KSampler", "inputs": {"seed": "__SEED__"}},
    }
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(template))

    workflow = load_custom_workflow(path, 'She said "run".', "blurry", 42)
    assert workflow["1"]["inputs"]["text"] == 'She said "run".'
    assert workflow["2"]["inputs"]["text"] == "blurry"
    assert workflow["3"]["inputs"]["seed"] == 42

    scene = Scene(index=1, narration="x", image_prompt="A gate")
    styled = build_workflow(scene, "Title", replace(settings, comfyui_workflow=path))
    assert styled["1"]["inputs"]["text"].endswith(CINEMATIC_STYLE)

    path.write_text(json.dumps({"1": {"inputs": {"text": "static"}}}))
    with pytest.raises(ValueError, match="__PROMPT__"):
        load_custom_workflow(path, "p", "n", 1)


def test_generate_scene_image_round_trips_through_comfyui(settings):
    session = FakeSession()
    client = ComfyUIClient(settings.comfyui_url, session=session)
    scene = Scene(index=3, narration="x", image_prompt="A cannon at night")

    path = image_generator.generate_scene_image(scene, settings, script_title="T", client=client)

    assert path == settings.paths.images / "scene_003.png"
    assert path.read_bytes() == b"\x89PNGfake"
    assert session.history_polls == 2
    queued = session.posted[0]
    assert queued["client_id"] == client.client_id
    assert queued["prompt"]["2"]["inputs"]["text"].endswith(CINEMATIC_STYLE)


def test_wait_for_outputs_surfaces_comfyui_errors(settings):
    class ErrorSession(FakeSession):
        def get(self, url, params=None, timeout=None):
            return FakeResponse({"abc123": {"status": {"status_str": "error", "messages": ["boom"]}, "outputs": {}}})

    client = ComfyUIClient(settings.comfyui_url, session=ErrorSession())
    with pytest.raises(RuntimeError, match="failed prompt"):
        client.wait_for_outputs("abc123", timeout=5)
