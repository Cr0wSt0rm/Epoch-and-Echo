import json

import pytest

from epoch_echo.config import VideoConfig
from epoch_echo.media import ffmpeg_available, probe
from epoch_echo.pipeline import run

pytestmark = pytest.mark.skipif(
    not ffmpeg_available(), reason="ffmpeg/ffprobe not installed"
)


def test_pipeline_end_to_end(tmp_path):
    cfg = VideoConfig(
        title="Pipeline Smoke Test",
        subtitle="a burned-in caption",
        output_dir=tmp_path,
        intro_seconds=1.0,
        outro_seconds=1.0,
        demo_seconds=3,
    )

    result = run(cfg)

    assert result.video.exists()
    assert result.thumbnail.exists()
    assert result.metadata.exists()

    # Final video should be 1080p and roughly demo (3s) + intro (1s) + outro (1s).
    info = probe(result.video)
    assert info.resolution == "1920x1080"
    assert info.has_audio is True
    assert 4.0 <= info.duration <= 7.0

    payload = json.loads(result.metadata.read_text())
    assert payload["title"].startswith("Pipeline Smoke Test")
    assert payload["resolution"] == "1920x1080"

    # Thumbnail should be a valid 1280x720 PNG.
    from PIL import Image

    with Image.open(result.thumbnail) as img:
        assert img.size == (1280, 720)
