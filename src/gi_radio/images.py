"""ComfyUI image generation: one prompt -> one still per scene.

Works against a local ComfyUI server (COMFYUI_URL, no auth) or Comfy Cloud
(COMFYUI_API_KEY, X-API-Key header, https://cloud.comfy.org). Both expose the
same /api/prompt and /api/view shapes; only job polling differs.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
import zlib
from pathlib import Path
from typing import Any, Protocol

import requests

from .schema import RenderSettings, Scene
from .script import NEGATIVE_PROMPT

DEFAULT_LOCAL_URL = "http://127.0.0.1:8188"
COMFY_CLOUD_URL = "https://cloud.comfy.org"
DEFAULT_CHECKPOINT = "sd_xl_base_1.0.safetensors"

_STATUS_HELP = {
    401: "Comfy rejected the API key. Create one at https://platform.comfy.org/profile/api-keys "
         "and set COMFYUI_API_KEY. Cloud API access needs a Standard, Creator or Pro subscription.",
    402: "Comfy Cloud reports insufficient credits.",
    429: "Comfy Cloud subscription inactive or queue full.",
}


class ComfyUIError(RuntimeError):
    pass


def build_workflow(
    scene: Scene,
    render: RenderSettings,
    *,
    checkpoint: str,
    seed: int,
    steps: int = 30,
    cfg: float = 6.5,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
) -> dict[str, Any]:
    """A plain SDXL txt2img graph in ComfyUI API format.

    Node ids are strings; the "9" SaveImage node's filename_prefix carries the scene id
    so the mapping scene -> image is visible in the ComfyUI output folder too.
    """

    return {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": render.comfyui_width, "height": render.comfyui_height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": scene.comfyui_image_prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEGATIVE_PROMPT, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": f"gi_radio/{scene.scene_id}", "images": ["8", 0]},
        },
    }


def scene_seed(scene: Scene) -> int:
    """Deterministic per-scene seed so re-runs reproduce the same frame."""

    return zlib.crc32(scene.scene_id.encode()) & 0x7FFFFFFF


class ImageGenerator(Protocol):
    def generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path: ...


class ComfyUIImageGenerator:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        checkpoint: str | None = None,
        poll_seconds: float = 2.0,
        timeout_seconds: float = 900.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("COMFYUI_API_KEY") or None
        url = base_url or os.environ.get("COMFYUI_URL") or (COMFY_CLOUD_URL if self.api_key else DEFAULT_LOCAL_URL)
        self.base_url = url.rstrip("/")
        self.is_cloud = "comfy.org" in self.base_url
        if self.is_cloud and not self.api_key:
            raise ComfyUIError("Comfy Cloud needs COMFYUI_API_KEY")
        self.checkpoint = checkpoint or os.environ.get("COMFYUI_CHECKPOINT") or DEFAULT_CHECKPOINT
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.client_id = str(uuid.uuid4())
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["X-API-Key"] = self.api_key

    def _check(self, response: requests.Response, what: str) -> requests.Response:
        if response.ok:
            return response
        hint = _STATUS_HELP.get(response.status_code, "")
        raise ComfyUIError(f"{what} failed with HTTP {response.status_code}: {response.text[:300]} {hint}".strip())

    def check_auth(self) -> dict[str, Any]:
        """Cheap round trip that proves the key/server is usable before spending anything."""

        path = "/api/user" if self.is_cloud else "/api/system_stats"
        return self._check(self.session.get(f"{self.base_url}{path}", timeout=60), "auth check").json()

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        payload: dict[str, Any] = {"prompt": workflow, "client_id": self.client_id}
        response = self._check(
            self.session.post(f"{self.base_url}/api/prompt", json=payload, timeout=120), "queue prompt"
        )
        body = response.json()
        if body.get("error"):
            raise ComfyUIError(f"ComfyUI rejected workflow: {json.dumps(body)[:600]}")
        return body["prompt_id"]

    def wait_for_outputs(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            if self.is_cloud:
                status = self._check(
                    self.session.get(f"{self.base_url}/api/job/{prompt_id}/status", timeout=60), "job status"
                ).json().get("status")
                if status == "completed":
                    job = self._check(
                        self.session.get(f"{self.base_url}/api/jobs/{prompt_id}", timeout=60), "job detail"
                    ).json()
                    return job.get("outputs") or {}
                if status in ("failed", "cancelled"):
                    job = self.session.get(f"{self.base_url}/api/jobs/{prompt_id}", timeout=60).json()
                    raise ComfyUIError(f"Comfy Cloud job {status}: {json.dumps(job.get('execution_error'))[:600]}")
            else:
                history = self._check(
                    self.session.get(f"{self.base_url}/api/history/{prompt_id}", timeout=60), "history"
                ).json()
                entry = history.get(prompt_id)
                if entry:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error":
                        raise ComfyUIError(f"ComfyUI failed prompt {prompt_id}: {json.dumps(status)[:600]}")
                    if entry.get("outputs"):
                        return entry["outputs"]
            time.sleep(self.poll_seconds)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} did not finish in {self.timeout_seconds}s")

    def download_first_image(self, outputs: dict[str, Any], out_path: Path) -> Path:
        for node_output in outputs.values():
            for image in node_output.get("images", []):
                params = {
                    "filename": image["filename"],
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
                response = self.session.get(
                    f"{self.base_url}/api/view", params=params, timeout=120, allow_redirects=False
                )
                if response.status_code in (301, 302, 303, 307, 308):
                    # Cloud hands back a signed storage URL; fetch it without the API key.
                    response = requests.get(response.headers["location"], timeout=300)
                self._check(response, "download image")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(response.content)
                return out_path
        raise ComfyUIError("ComfyUI outputs contained no images")

    def generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path:
        workflow = build_workflow(scene, render, checkpoint=self.checkpoint, seed=scene_seed(scene))
        prompt_id = self.queue_prompt(workflow)
        outputs = self.wait_for_outputs(prompt_id)
        return self.download_first_image(outputs, out_path)


class PlaceholderImageGenerator:
    """Offline stand-in: a flat frame in the grade's palette, one hue per scene."""

    PALETTE = ("0x1b2a1f", "0x2a2f1b", "0x14202b", "0x3a3419", "0x101a14")

    def __init__(self, ffmpeg: str = "ffmpeg") -> None:
        self.ffmpeg = ffmpeg

    def generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path:
        color = self.PALETTE[scene_seed(scene) % len(self.PALETTE)]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                self.ffmpeg, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c={color}:s={render.comfyui_width}x{render.comfyui_height}",
                "-frames:v", "1", str(out_path),
            ],
            check=True,
        )
        return out_path
