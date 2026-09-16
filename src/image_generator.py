"""Stage 4: create one visual per scene with the ComfyUI API into `output/images/`.

Every scene's `image_prompt` (already carrying the mandatory cinematic style
suffix, see `src.models`) is queued as a txt2img workflow; the resulting PNG is
recorded on the scene as `image_path` for the video assembler.
"""

from __future__ import annotations

import copy
import json
import logging
import time
import uuid
import zlib
from pathlib import Path
from typing import Any

import requests

from config import Settings
from src.models import Scene, Script, apply_cinematic_style

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1.0
GENERATION_TIMEOUT_SECONDS = 600

IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1088  # multiple of 16 for the latent grid; cropped to 1080 by FFmpeg

NEGATIVE_PROMPT = (
    "text, watermark, signature, logo, caption, blurry, low resolution, cartoon, "
    "anime, 3d render, modern clothing, bright flat lighting, cheerful, oversaturated"
)

PROMPT_PLACEHOLDER = "__PROMPT__"
NEGATIVE_PLACEHOLDER = "__NEGATIVE_PROMPT__"
SEED_PLACEHOLDER = "__SEED__"


def scene_seed(script_title: str, scene_index: int) -> int:
    """Deterministic seed so re-runs of the same scene render the same frame."""
    return zlib.crc32(f"{script_title}:{scene_index}".encode("utf-8"))


def build_default_workflow(prompt: str, negative_prompt: str, seed: int, checkpoint: str) -> dict[str, Any]:
    """Return a ComfyUI API-format txt2img workflow (checkpoint -> KSampler -> PNG)."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
            "_meta": {"title": "Positive Prompt"},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["1", 1]},
            "_meta": {"title": "Negative Prompt"},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "epoch_echo", "images": ["6", 0]},
        },
    }


def load_custom_workflow(path: Path, prompt: str, negative_prompt: str, seed: int) -> dict[str, Any]:
    """Load a user workflow JSON and substitute the prompt/negative/seed placeholders."""
    raw = Path(path).read_text(encoding="utf-8")
    if PROMPT_PLACEHOLDER not in raw:
        raise ValueError(f"custom ComfyUI workflow {path} must contain {PROMPT_PLACEHOLDER}")
    raw = raw.replace(PROMPT_PLACEHOLDER, json.dumps(prompt)[1:-1])
    raw = raw.replace(NEGATIVE_PLACEHOLDER, json.dumps(negative_prompt)[1:-1])
    raw = raw.replace(f'"{SEED_PLACEHOLDER}"', str(seed)).replace(SEED_PLACEHOLDER, str(seed))
    return json.loads(raw)


def build_workflow(scene: Scene, script_title: str, settings: Settings) -> dict[str, Any]:
    prompt = apply_cinematic_style(scene.image_prompt)
    seed = scene_seed(script_title, scene.index)
    if settings.comfyui_workflow is not None:
        return load_custom_workflow(settings.comfyui_workflow, prompt, NEGATIVE_PROMPT, seed)
    if not settings.comfyui_checkpoint:
        raise RuntimeError("COMFYUI_CHECKPOINT is not set (or provide COMFYUI_WORKFLOW)")
    return build_default_workflow(prompt, NEGATIVE_PROMPT, seed, settings.comfyui_checkpoint)


class ComfyUIClient:
    """Minimal client for the ComfyUI HTTP API (/prompt, /history, /view)."""

    def __init__(self, base_url: str, session: requests.Session | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.client_id = uuid.uuid4().hex

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        response = self.session.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": self.client_id},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if "prompt_id" not in payload:
            raise RuntimeError(f"ComfyUI rejected the workflow: {payload}")
        return payload["prompt_id"]

    def wait_for_outputs(self, prompt_id: str, timeout: float = GENERATION_TIMEOUT_SECONDS) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self.session.get(
                f"{self.base_url}/history/{prompt_id}", timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            entry = response.json().get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI failed prompt {prompt_id}: {status}")
                if entry.get("outputs"):
                    return entry["outputs"]
            time.sleep(POLL_INTERVAL_SECONDS)
        raise TimeoutError(f"ComfyUI did not finish prompt {prompt_id} within {timeout:.0f}s")

    def download_image(self, image_ref: dict[str, Any]) -> bytes:
        response = self.session.get(
            f"{self.base_url}/view",
            params={
                "filename": image_ref["filename"],
                "subfolder": image_ref.get("subfolder", ""),
                "type": image_ref.get("type", "output"),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.content


def first_image_ref(outputs: dict[str, Any]) -> dict[str, Any]:
    for node_output in outputs.values():
        images = node_output.get("images") or []
        for image in images:
            if image.get("type", "output") == "output":
                return image
    raise RuntimeError("ComfyUI workflow produced no saved images")


def generate_scene_image(
    scene: Scene, settings: Settings, *, script_title: str = "", client: ComfyUIClient | None = None
) -> Path:
    """Generate the still frame for one scene and return its PNG path."""
    settings.paths.images.mkdir(parents=True, exist_ok=True)
    target = settings.paths.images / f"scene_{scene.index:03d}.png"
    logger.info("Generating image for scene %d -> %s", scene.index, target)

    workflow = build_workflow(scene, script_title, settings)
    client = client or ComfyUIClient(settings.comfyui_url)
    prompt_id = client.queue_prompt(copy.deepcopy(workflow))
    outputs = client.wait_for_outputs(prompt_id)
    target.write_bytes(client.download_image(first_image_ref(outputs)))
    return target


def generate_script_images(script: Script, settings: Settings) -> Script:
    """Attach an `image_path` to every scene in the script."""
    client = ComfyUIClient(settings.comfyui_url)
    for scene in script.scenes:
        scene.image_path = generate_scene_image(
            scene, settings, script_title=script.title, client=client
        )
    return script
