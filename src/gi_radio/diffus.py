"""diffus.me image generation: one prompt -> one still per scene.

Diffus is a hosted Stable Diffusion service, not a ComfyUI server, so the
ComfyUI workflow graph is not used here; the scene's prompt, negative prompt,
size and seed are sent to one of Diffus' two HTTP surfaces:

* ``fal``  - fal.ai-compatible queue API (what the official ``diffus`` SDK uses):
             POST https://queue.api.diffus.me/{app}  with ``Authorization: Key <DIFFUS_KEY>``
* ``v3``   - Diffus Stable Diffusion API v3 (https://api.diffus.me/openapi.json):
             POST /api/v3/txt2img + GET /api/v3/progress  with ``x-diffus-passkey``
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

from .images import ComfyUIError, scene_seed
from .schema import RenderSettings, Scene
from .script import NEGATIVE_PROMPT

DIFFUS_RUN_HOST = "api.diffus.me"
DEFAULT_FAL_APP = "diffus-ai/juggernaut-xl-v9-rundiffusionphoto2"
DEFAULT_V3_MODEL = "sd_xl_base_1.0.safetensors"

_V3_CODES = {
    -1: "internal error", 1: "invalid JSON", 2: "model not found in your Diffus workspace",
    3: "task id not found", 4: "invalid auth", 5: "host unavailable", 6: "invalid query parameters",
    7: "insufficient funds", 8: "sampler not found", 9: "timeout", 10: "not supported",
}
_V3_STATUS = {-1: "unknown", 0: "queued", 1: "initializing", 2: "running", 3: "complete", 4: "failed", 5: "timeout"}


class DiffusError(ComfyUIError):
    pass


class DiffusImageGenerator:
    def __init__(
        self,
        api_key: str | None = None,
        mode: str | None = None,
        model: str | None = None,
        run_host: str | None = None,
        poll_seconds: float = 3.0,
        timeout_seconds: float = 900.0,
        steps: int = 30,
        cfg_scale: float = 6.5,
    ) -> None:
        self.api_key = api_key or os.environ.get("DIFFUS_KEY")
        if not self.api_key:
            raise DiffusError("DIFFUS_KEY is not set")
        self.mode = (mode or os.environ.get("DIFFUS_API") or "fal").lower()
        if self.mode not in ("fal", "v3"):
            raise DiffusError(f"DIFFUS_API must be 'fal' or 'v3', got {self.mode!r}")
        self.model = model or os.environ.get("DIFFUS_MODEL") or (DEFAULT_FAL_APP if self.mode == "fal" else DEFAULT_V3_MODEL)
        self.run_host = run_host or os.environ.get("DIFFUS_RUN_HOST") or DIFFUS_RUN_HOST
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.steps = steps
        self.cfg_scale = cfg_scale
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "gi-radio/0.1 (+diffus)"
        if self.mode == "fal":
            self.session.headers["Authorization"] = f"Key {self.api_key}"
        else:
            self.session.headers["x-diffus-passkey"] = self.api_key

    # Shared -----------------------------------------------------------------

    @property
    def base_url(self) -> str:
        return f"https://{self.run_host}"

    @property
    def queue_url(self) -> str:
        return f"https://queue.{self.run_host}"

    @property
    def is_cloud(self) -> bool:
        return True

    def _check(self, response: requests.Response, what: str) -> requests.Response:
        if response.ok:
            return response
        raise DiffusError(f"Diffus {what} failed with HTTP {response.status_code}: {response.text[:300]}")

    def _get_retrying(
        self, url: str, what: str, *, attempts: int = 6, authenticated: bool = True, **kwargs: Any
    ) -> requests.Response:
        """GET with retries on transient failures.

        Only idempotent reads go through here (status polls, results, downloads);
        a retried submit could spend a second credit for the same still. Downloads
        hit a third-party CDN, so they go out without the passkey header.
        """

        getter = self.session.get if authenticated else requests.get
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                response = getter(url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last = exc
            else:
                if response.status_code < 500:
                    return self._check(response, what)
                last = DiffusError(f"Diffus {what} returned HTTP {response.status_code}")
            time.sleep(min(2.0 * 2**attempt, 30.0))
        raise DiffusError(f"Diffus {what} kept failing after {attempts} attempts: {last}")

    def _download(self, url: str, out_path: Path) -> Path:
        response = self._get_retrying(url, "image download", authenticated=False, timeout=300)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        return out_path

    def check_auth(self) -> dict[str, Any]:
        """Read-only probe. v3 can validate the passkey cheaply; fal has no free auth call."""

        if self.mode == "v3":
            response = self.session.get(
                f"{self.base_url}/api/v3/progress", params={"task_id": "gi-radio-auth-probe"}, timeout=60
            )
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            code = (body.get("data") or {}).get("code", body.get("code"))
            if response.status_code == 500 or code == 4:
                raise DiffusError(f"Diffus rejected the passkey: {response.text[:200]}")
            return {"mode": "v3", "model": self.model, "probe": body}
        response = self.session.get(f"{self.base_url}/{self.model}", timeout=60)
        if response.status_code == 405:
            return {"mode": "fal", "model": self.model, "note": "endpoint reachable; key is validated on first job"}
        raise DiffusError(f"Diffus fal endpoint probe returned HTTP {response.status_code}: {response.text[:200]}")

    # fal-compatible queue -----------------------------------------------------

    def _fal_generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path:
        arguments = {
            "prompt": scene.comfyui_image_prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "width": render.comfyui_width,
            "height": render.comfyui_height,
            "seed": scene_seed(scene),
            "num_inference_steps": self.steps,
            "guidance_scale": self.cfg_scale,
            "batch_size": 1,
        }
        submitted = self._check(
            self.session.post(f"{self.queue_url}/{self.model}", json=arguments, timeout=120), "submit"
        ).json()
        status_url, response_url = submitted["status_url"], submitted["response_url"]
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            status = self._get_retrying(status_url, "status", params={"logs": "0"}, timeout=60).json()
            state = status.get("status")
            if state == "COMPLETED":
                break
            if state in ("FAILED", "ERROR", "CANCELLED"):
                raise DiffusError(f"Diffus job for {scene.scene_id} ended {state}: {str(status)[:300]}")
            time.sleep(self.poll_seconds)
        else:
            raise TimeoutError(f"Diffus job for {scene.scene_id} did not finish in {self.timeout_seconds}s")
        result = self._get_retrying(response_url, "result", timeout=120).json()
        # Diffus returns {"results": [{"url", "content_type"}]}; fal apps use "images"/"image".
        images = result.get("results") or result.get("images") or result.get("image") or []
        if isinstance(images, dict):
            images = [images]
        if not images:
            raise DiffusError(f"Diffus returned no images: {str(result)[:300]}")
        return self._download(images[0]["url"] if isinstance(images[0], dict) else images[0], out_path)

    # v3 REST ---------------------------------------------------------------------

    def _v3_generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path:
        payload = {
            "prompt": scene.comfyui_image_prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "model_name": self.model,
            "sampler_name": "DPM++ 2M Karras",
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "seed": scene_seed(scene),
            "width": render.comfyui_width,
            "height": render.comfyui_height,
            "batch_size": 1,
            "n_iter": 1,
        }
        body = self._check(self.session.post(f"{self.base_url}/api/v3/txt2img", json=payload, timeout=120), "txt2img").json()
        if body.get("code", 0) != 0:
            raise DiffusError(f"Diffus txt2img error {body.get('code')} ({_V3_CODES.get(body.get('code'), '?')}): {body.get('msg')}")
        task_id = body["data"]["task_id"]
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            progress = self._get_retrying(
                f"{self.base_url}/api/v3/progress", "progress", params={"task_id": task_id}, timeout=60
            ).json()
            if progress.get("code", 0) != 0:
                raise DiffusError(f"Diffus progress error {progress.get('code')}: {progress.get('msg')}")
            detail = progress.get("data") or {}
            status = detail.get("status", -1)
            if status == 3:
                imgs = detail.get("imgs") or []
                if not imgs:
                    raise DiffusError("Diffus task completed without images")
                return self._download(imgs[0], out_path)
            if status in (4, 5):
                raise DiffusError(f"Diffus task {_V3_STATUS[status]}: {detail.get('failed_reason')}")
            time.sleep(self.poll_seconds)
        raise TimeoutError(f"Diffus task {task_id} did not finish in {self.timeout_seconds}s")

    def generate(self, scene: Scene, render: RenderSettings, out_path: Path) -> Path:
        if self.mode == "fal":
            return self._fal_generate(scene, render, out_path)
        return self._v3_generate(scene, render, out_path)
