import os
from pathlib import Path

import pytest

from gi_radio.cli import load_dotenv
from gi_radio.images import COMFY_CLOUD_URL, DEFAULT_LOCAL_URL, ComfyUIError, ComfyUIImageGenerator


@pytest.fixture
def clean_env(monkeypatch):
    for key in ("COMFYUI_URL", "COMFYUI_API_KEY", "COMFYUI_CHECKPOINT", "GI_RADIO_TEST_A", "GI_RADIO_TEST_B"):
        monkeypatch.delenv(key, raising=False)


def test_local_comfyui_by_default(clean_env):
    gen = ComfyUIImageGenerator()
    assert gen.base_url == DEFAULT_LOCAL_URL
    assert gen.is_cloud is False
    assert "X-API-Key" not in gen.session.headers


def test_api_key_selects_comfy_cloud_and_sets_header(clean_env, monkeypatch):
    monkeypatch.setenv("COMFYUI_API_KEY", "pk_test")
    gen = ComfyUIImageGenerator()
    assert gen.base_url == COMFY_CLOUD_URL
    assert gen.is_cloud is True
    assert gen.session.headers["X-API-Key"] == "pk_test"


def test_cloud_url_without_key_is_refused(clean_env):
    with pytest.raises(ComfyUIError, match="COMFYUI_API_KEY"):
        ComfyUIImageGenerator(base_url=COMFY_CLOUD_URL)


def test_load_dotenv_does_not_override_existing(clean_env, monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nGI_RADIO_TEST_A=from_file\nGI_RADIO_TEST_B='quoted'\nEMPTY=\n")
    monkeypatch.setenv("GI_RADIO_TEST_A", "from_shell")
    load_dotenv(env)
    assert os.environ["GI_RADIO_TEST_A"] == "from_shell"
    assert os.environ["GI_RADIO_TEST_B"] == "quoted"
    assert "EMPTY" not in os.environ


def test_load_dotenv_missing_file_is_noop(tmp_path):
    load_dotenv(tmp_path / "nope.env")
