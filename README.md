# Epoch-and-Echo

Video pipeline for the **Epoch & Echo** YouTube channel. It turns raw footage
into an upload-ready package: a branded 1080p video (intro + episode + outro), a
1280×720 thumbnail, and a `metadata.json` sidecar (title, description, tags,
chapters) ready for upload.

## How it works

The pipeline runs five composable stages:

```
ingest → transcode (normalize) → branding (intro/outro) → thumbnail → metadata
```

- **ingest** — resolves the source clip (or generates a synthetic demo clip so
  the pipeline can always run end to end) and probes it with `ffprobe`.
- **transcode** — normalizes footage to 1920×1080 @ 30fps, H.264 + AAC, and can
  burn in a lower-third caption.
- **branding** — prepends an intro title card and appends an outro card.
- **thumbnail** — grabs a representative frame and overlays the title + brand.
- **metadata** — writes `metadata.json` with description, tags, and chapters.

## Requirements

- Python ≥ 3.10
- `ffmpeg` (provides `ffmpeg` and `ffprobe`)

## Setup

```bash
bash .cursor/install.sh      # installs ffmpeg (if missing) + Python deps into .venv
source .venv/bin/activate
epoch-echo doctor            # verify tools are available
```

Or manually:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

Generate a full episode from a synthetic demo clip:

```bash
epoch-echo build --title "The Library of Alexandria" \
  --subtitle "How the ancient world's knowledge was lost" --demo
```

From a recipe file:

```bash
epoch-echo build --config examples/episode.yaml --demo
```

From your own footage:

```bash
epoch-echo build --title "My Episode" --source path/to/footage.mp4
```

Artifacts are written to `out/<slug>/`:

```
out/the-library-of-alexandria/
├── the-library-of-alexandria.mp4    # final video
├── the-library-of-alexandria.png    # thumbnail
└── metadata.json                    # upload metadata
```

## Tests

```bash
source .venv/bin/activate
pytest
```
