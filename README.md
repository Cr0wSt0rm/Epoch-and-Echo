# Epoch-and-Echo

Automated history video pipeline. A Cursor-authored script is validated with
Pydantic, narrated with the ElevenLabs API, illustrated with the ComfyUI API,
and stitched into an MP4 with FFmpeg.

The rules every contributor (and Cursor) follows live in [`.cursorrules`](.cursorrules).
The code enforces them:

| Rule | Enforcement |
| --- | --- |
| Python 3.11+, Pydantic, ElevenLabs, ComfyUI, FFmpeg | `pyproject.toml` (`requires-python`), `requirements.txt`, one stage module per tool |
| Typed Pydantic models for the script schema | `src/models.py` (`Topic`, `Scene`, `Script`, `VideoAsset`), `extra="forbid"` |
| Every scene maps Narration -> Audio -> Image -> Stitching | `Scene.audio_path` / `image_path` filled per stage; `Script.require_render_ready()` blocks stitching if any scene is missing an asset; scene indices must be contiguous |
| Cohesive ComfyUI cinematic style | `Scene.image_prompt` validator appends `CINEMATIC_STYLE` once; `image_generator` re-applies it before queuing |
| Theatrical, suspenseful narration without AI buzzwords | `Scene.narration` validator rejects `delve`, `testament`, `moreover` (and inflections); `SCRIPTWRITING_BRIEF` carries the persona |

## Project structure

```
.
├── .cursorrules             # role, stack, coding rules, scriptwriting persona
├── config/
│   └── settings.py          # loads .env, exposes Settings and Paths
├── episodes/
│   └── the-fall-of-constantinople.json   # example Cursor-authored script
├── src/
│   ├── main.py              # CLI entry point / orchestrator
│   ├── models.py            # Pydantic schema + rule validators
│   ├── topic_research.py    # stage 1: select the topic
│   ├── script_generator.py  # stage 2: validate the script JSON
│   ├── voiceover.py         # stage 3: ElevenLabs TTS   -> output/audio/
│   ├── image_generator.py   # stage 4: ComfyUI txt2img  -> output/images/
│   ├── video_assembler.py   # stage 5: FFmpeg stitch    -> output/final_videos/
│   └── uploader.py          # stage 6: publish to YouTube
├── tests/
├── .env.example             # API key template (copy to .env)
├── pyproject.toml
└── requirements.txt
```

## Requirements

- Python 3.11 or newer
- FFmpeg (`ffmpeg` and `ffprobe` on `PATH`)
- An ElevenLabs API key and voice ID
- A running ComfyUI server with a checkpoint installed

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
python -m src.main --check-env
```

## Creating a video

1. Author the script in Cursor Composer. Paste `src.script_generator.SCRIPTWRITING_BRIEF`
   as the brief, then save the JSON to `episodes/<topic-slug>.json`. See
   `episodes/the-fall-of-constantinople.json` for the shape and the voice.
2. Run the pipeline:

```bash
python -m src.main "The Fall of Constantinople"
python -m src.main "The Fall of Constantinople" --script episodes/custom.json
python -m src.main "The Fall of Constantinople" --upload
```

Each scene produces `output/audio/scene_NNN.mp3` and `output/images/scene_NNN.png`,
and the final video lands in `output/final_videos/<title-slug>.mp4` (1080p30,
H.264/AAC, slow push-in per scene with fades).

### Custom ComfyUI workflows

Set `COMFYUI_WORKFLOW` to an API-format workflow JSON containing the literal
placeholders `__PROMPT__`, `__NEGATIVE_PROMPT__` and `__SEED__`. The styled scene
prompt is substituted at run time.

## Tests

```bash
pytest
```

The suite validates the schema rules, stubs ElevenLabs and ComfyUI at the HTTP
boundary, and renders a real MP4 with FFmpeg to prove the scene mapping end to end.
