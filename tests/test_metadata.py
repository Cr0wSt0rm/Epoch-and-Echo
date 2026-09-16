import json

from epoch_echo.config import VideoConfig
from epoch_echo.media import MediaInfo
from epoch_echo.stages import metadata
from epoch_echo.stages.metadata import _format_timestamp


def test_format_timestamp():
    assert _format_timestamp(0) == "0:00"
    assert _format_timestamp(65) == "1:05"
    assert _format_timestamp(3661) == "1:01:01"


def test_build_writes_expected_payload(tmp_path):
    cfg = VideoConfig(title="Test Episode", tags=["a", "b"])
    final_info = MediaInfo(width=1920, height=1080, duration=13.0, has_audio=True)
    dest = tmp_path / "metadata.json"

    metadata.build(cfg, final_info, content_duration=9.0, dest=dest)

    payload = json.loads(dest.read_text())
    assert payload["title"] == "Test Episode | Epoch & Echo"
    assert payload["channel"] == "Epoch & Echo"
    assert payload["tags"] == ["a", "b"]
    assert payload["resolution"] == "1920x1080"
    assert [c["title"] for c in payload["chapters"]] == ["Intro", "Episode", "Outro"]
    # intro (2s) + content (9s) => outro chapter starts at 0:11
    assert payload["chapters"][2]["start"] == "0:11"
