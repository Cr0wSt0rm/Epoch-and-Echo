"""Font discovery shared by the ffmpeg (drawtext) and Pillow stages.

We prefer bundled/system DejaVu or Liberation fonts so the pipeline works on a
stock Debian/Ubuntu image without downloading anything.
"""

from __future__ import annotations

from pathlib import Path

_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def find_bold_font() -> Path:
    for candidate in _CANDIDATES:
        p = Path(candidate)
        if p.exists():
            return p
    raise FileNotFoundError(
        "No usable TrueType font found. Install 'fonts-dejavu-core' or "
        "'fonts-liberation'."
    )
