"""ComfyUI image generation: one prompt -> one still per scene."""

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

DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"


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
        checkpoint: str | None = None,
        poll_seconds: float = 2.0,
        timeout_seconds: float = 900.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("COMFYUI_URL") or DEFAULT_COMFYUI_URL).rstrip("/")
        self.checkpoint = checkpoint or os.environ.get("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": self.client_id},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["prompt_id"]

    def wait_for_history(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=60)
            response.raise_for_status()
            history = response.json()
            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI failed prompt {prompt_id}: {json.dumps(status)[:500]}")
                if entry.get("outputs"):
                    return entry
            time.sleep(self.poll_seconds)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} did not finish in {self.timeout_seconds}s")

    def download_first_image(self, history_entry: dict[str, Any], out_path: Path) -> Path:
        for node_output in history_entry["outputs"].values():
            for image in node_output.get("images", []):
                response = requests.get(
                    f"{self.base_url}/view",
                    params={
                        "filename": image["filename"],
                        "subfolder": image.get("subfolder", ""),
                        "type": image.get("type", "output"),
                    },
                    timeout=120,
                )
                response.raise_for_status()
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(response.content)
                return out_path
        raise RuntimeError("ComfyUI history contained no images")

    def generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path:
        workflow = build_workflow(scene, render, checkpoint=self.checkpoint, seed=scene_seed(scene))
        prompt_id = self.queue_prompt(workflow)
        entry = self.wait_for_history(prompt_id)
        return self.download_first_image(entry, out_path)


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
