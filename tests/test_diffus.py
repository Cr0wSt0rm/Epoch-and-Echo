"""Diffus client against a fake HTTP layer (no network)."""

from pathlib import Path

import pytest

from gi_radio import diffus as diffus_mod
from gi_radio.diffus import DiffusError, DiffusImageGenerator
from gi_radio.pipeline import default_image_generator
from gi_radio.schema import CINEMATIC_STYLE
from gi_radio.script import get_script

PNG = b"\x89PNG\r\n\x1a\nfake"


class FakeResponse:
    def __init__(self, status=200, json_body=None, content=b"", headers=None):
        self.status_code = status
        self._json = json_body
        self.content = content
        self.text = str(json_body) if json_body is not None else content.decode(errors="ignore")
        self.headers = headers or {"content-type": "application/json"}

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._json


class FakeSession:
    def __init__(self, routes):
        self.headers = {}
        self.routes = routes
        self.calls = []

    def _dispatch(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for (m, needle), handler in self.routes.items():
            if m == method and needle in url:
                return handler(url, kw) if callable(handler) else handler
        raise AssertionError(f"unexpected {method} {url}")

    def get(self, url, **kw):
        return self._dispatch("GET", url, **kw)

    def post(self, url, **kw):
        return self._dispatch("POST", url, **kw)


@pytest.fixture
def scene_and_render():
    script = get_script()
    return script.scenes[0], script.render


def test_default_image_generator_prefers_diffus_when_key_set(monkeypatch):
    monkeypatch.delenv("COMFYUI_API_KEY", raising=False)
    monkeypatch.setenv("DIFFUS_KEY", "pk_test")
    assert isinstance(default_image_generator(), DiffusImageGenerator)
    monkeypatch.delenv("DIFFUS_KEY")
    assert not isinstance(default_image_generator(), DiffusImageGenerator)


def test_fal_mode_headers_and_hosts(monkeypatch):
    monkeypatch.delenv("DIFFUS_API", raising=False)
    monkeypatch.delenv("DIFFUS_MODEL", raising=False)
    gen = DiffusImageGenerator(api_key="pk_test")
    assert gen.mode == "fal"
    assert gen.session.headers["Authorization"] == "Key pk_test"
    assert gen.queue_url == "https://queue.api.diffus.me"
    assert gen.base_url == "https://api.diffus.me"


def test_v3_mode_uses_passkey_header():
    gen = DiffusImageGenerator(api_key="pk_test", mode="v3", model="sd_xl_base_1.0.safetensors")
    assert gen.session.headers["x-diffus-passkey"] == "pk_test"
    assert "Authorization" not in gen.session.headers


def test_missing_key_or_bad_mode(monkeypatch):
    monkeypatch.delenv("DIFFUS_KEY", raising=False)
    with pytest.raises(DiffusError, match="DIFFUS_KEY"):
        DiffusImageGenerator()
    with pytest.raises(DiffusError, match="fal"):
        DiffusImageGenerator(api_key="k", mode="nope")


def test_fal_generate_submits_prompt_polls_and_downloads(monkeypatch, tmp_path, scene_and_render):
    scene, render = scene_and_render
    gen = DiffusImageGenerator(api_key="pk_test", mode="fal", model="diffus-ai/dreamshaper-8", poll_seconds=0)
    statuses = iter(["IN_QUEUE", "IN_PROGRESS", "COMPLETED"])
    gen.session = FakeSession({
        ("POST", "queue.api.diffus.me/diffus-ai/dreamshaper-8"): FakeResponse(
            200, {"request_id": "r1", "status_url": "https://queue.api.diffus.me/x/status",
                  "response_url": "https://queue.api.diffus.me/x/result"}),
        ("GET", "/x/status"): lambda url, kw: FakeResponse(200, {"status": next(statuses)}),
        ("GET", "/x/result"): FakeResponse(200, {"results": [{"url": "https://cdn.example/out.png", "content_type": "image/png"}]}),
    })
    monkeypatch.setattr(diffus_mod.requests, "get", lambda url, **kw: FakeResponse(200, None, PNG, {}))
    monkeypatch.setattr(diffus_mod.time, "sleep", lambda s: None)

    out = gen.generate(scene, render, tmp_path / "S01.png")
    assert out.read_bytes() == PNG
    submit = gen.session.calls[0]
    args = submit[2]["json"]
    assert CINEMATIC_STYLE in args["prompt"]
    assert (args["width"], args["height"]) == (render.comfyui_width, render.comfyui_height)
    assert args["seed"] == diffus_mod.scene_seed(scene)
    assert sum(1 for c in gen.session.calls if "/x/status" in c[1]) == 3


def test_v3_generate_polls_progress_and_reports_codes(monkeypatch, tmp_path, scene_and_render):
    scene, render = scene_and_render
    gen = DiffusImageGenerator(api_key="pk_test", mode="v3", model="sd_xl_base_1.0.safetensors", poll_seconds=0)
    progress = iter([
        {"code": 0, "data": {"status": 0}},
        {"code": 0, "data": {"status": 2, "progress": 0.5}},
        {"code": 0, "data": {"status": 3, "imgs": ["https://cdn.example/v3.png"]}},
    ])
    gen.session = FakeSession({
        ("POST", "/api/v3/txt2img"): FakeResponse(200, {"code": 0, "data": {"task_id": "t1"}}),
        ("GET", "/api/v3/progress"): lambda url, kw: FakeResponse(200, next(progress)),
    })
    monkeypatch.setattr(diffus_mod.requests, "get", lambda url, **kw: FakeResponse(200, None, PNG, {}))
    monkeypatch.setattr(diffus_mod.time, "sleep", lambda s: None)

    out = gen.generate(scene, render, tmp_path / "S01.png")
    assert out.read_bytes() == PNG
    payload = gen.session.calls[0][2]["json"]
    assert payload["model_name"] == "sd_xl_base_1.0.safetensors"
    assert CINEMATIC_STYLE in payload["prompt"]

    failing = DiffusImageGenerator(api_key="pk_test", mode="v3", poll_seconds=0)
    failing.session = FakeSession({
        ("POST", "/api/v3/txt2img"): FakeResponse(200, {"code": 7, "msg": "no balance"}),
    })
    with pytest.raises(DiffusError, match="insufficient funds"):
        failing.generate(scene, render, tmp_path / "x.png")
