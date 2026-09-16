#!/usr/bin/env bash
# Idempotent bootstrap for the Epoch & Echo video pipeline.
# Safe to run repeatedly: it only installs what is missing.
set -euo pipefail

cd "$(dirname "$0")/.."

# 1. System dependencies: ffmpeg (ffmpeg + ffprobe), fonts for overlays, and the
#    python venv module. Only apt-update/install when something is actually missing.
NEED_APT=0
command -v ffmpeg >/dev/null 2>&1 || NEED_APT=1
command -v ffprobe >/dev/null 2>&1 || NEED_APT=1
python3 -c "import ensurepip" >/dev/null 2>&1 || NEED_APT=1

if [ "$NEED_APT" -eq 1 ]; then
  echo "[install] Installing system dependencies via apt..."
  PY_VENV_PKG="python$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')-venv"
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core "$PY_VENV_PKG"
else
  echo "[install] ffmpeg/ffprobe already present: $(ffmpeg -version | head -1)"
fi

# 2. Python environment (project virtualenv).
if [ ! -d .venv ]; then
  echo "[install] Creating virtualenv at .venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
# Editable install with dev extras so 'epoch-echo' and pytest are available.
python -m pip install -e ".[dev]"

echo "[install] Verifying toolchain..."
epoch-echo doctor

echo "[install] Done. Activate with: source .venv/bin/activate"
