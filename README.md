# Epoch-and-Echo

## The Voice in the Hooch

A typed, end-to-end pipeline for a cinematic video on the inner experience of one American GI in Vietnam, 1968-69, and the woman in Hanoi whose voice would not leave the hooch.

Stack: Python 3.11+, Pydantic v2, ElevenLabs (narration), ComfyUI (stills), FFmpeg (stitch).

Every scene maps exactly once through the chain

```
Narration Text -> Audio Generation -> Image Generation -> Video Stitching
```

and the Pydantic models enforce that shape before any API is called.

### Layout

| Path | What it is |
| --- | --- |
| `src/gi_radio/schema.py` | `VoiceSettings`, `Scene`, `VideoScript`, `Protagonist`, `ColorGrade`, `RenderSettings`, validators |
| `src/gi_radio/script.py` | The full `VideoScript` instance: 30 scenes, ~3,600 spoken words, ~32 min at 125 wpm |
| `src/gi_radio/audio.py` | ElevenLabs TTS client (+ offline placeholder), paragraph breaks -> `<break>` tags |
| `src/gi_radio/images.py` | ComfyUI API client with an SDXL txt2img graph (+ offline placeholder) |
| `src/gi_radio/render.py` | FFmpeg plan: per-scene clip (Ken Burns + grade), radio filter on Hannah, xfade timeline |
| `src/gi_radio/pipeline.py` | Orchestrator that runs the chain per scene and writes `manifest.json` |
| `src/gi_radio/cli.py` | `validate`, `export`, `plan`, `render` |
| `output/the-voice-in-the-hooch.md` | Readable screenplay export (narration, SFX, prompts, timings) |
| `output/the-voice-in-the-hooch.script.json` | Machine export of the validated `VideoScript` |

### Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in ELEVENLABS_API_KEY, COMFYUI_URL
```

FFmpeg 6+ with `libx264`, `xfade`, `zoompan`, `anoisesrc` must be on `PATH`.

### Commands

```bash
python -m gi_radio validate                                   # schema check + per-scene table
python -m gi_radio export --json output/the-voice-in-the-hooch.script.json \
                          --markdown output/the-voice-in-the-hooch.md
python -m gi_radio plan --build-dir build --out build/plan.json   # FFmpeg plan with scripted durations
python -m gi_radio render --build-dir build                    # real ElevenLabs + ComfyUI + FFmpeg run
python -m gi_radio render --build-dir build --placeholder --duration-scale 0.05   # offline dry run
python -m gi_radio render --build-dir build --scenes S19 S20 S21                  # subset
pytest
```

`render` writes `build/audio/<scene>.mp3`, `build/images/<scene>.png`, `build/clips/<scene>.mp4`,
`build/manifest.json` and the final `build/the-voice-in-the-hooch.mp4`. Existing assets are reused
unless `--force` is passed, so a failed ComfyUI call can be resumed without re-spending ElevenLabs credits.

### Schema guarantees

- Every `comfyui_image_prompt` carries the mandatory style string
  `Dark historical atmosphere, cinematic lighting, 8k resolution, oil painting aesthetic, moody and suspenseful.`
- Narration rejects the banned word list (`delve`, `testament`, `moreover`, `tapestry`, `landscape`, `underscore`, `pivotal`, `embark`, `nestled`).
- A scene's `duration_seconds` can never be shorter than its word count at 130 wpm; the script's total must be at least 15 minutes.
- The eleven required emotional beats must all appear, first occurrences in order.
- Both voices (`narrator`, `hannah_radio`) must be configured and used.

### FFmpeg stitch strategy

1. Per scene: still -> `scale`/`crop` to 1920x1080 -> `zoompan` (slow push to 1.08x) -> house grade -> `yuv420p`.
   Narration -> `aresample` -> pad/trim to clip length -> short fade in/out.
   Hannah lines additionally get `highpass=300, lowpass=3400, acompressor, tremolo, volume` and pink-noise hiss mixed under.
   Clip length = max(scripted duration, audio length + 2.5s hold).
2. Timeline: `xfade` chain in scene order (`fade` default, `fadeblack` for chapter breaks, `dissolve` for radio cut-ins)
   with matching `acrossfade`; fade from black at the head, fade to black at the tail.
3. Fallback: concat demuxer with stream copy for a hard-cut assembly.

### Color grade

**Bruised Green / Wet Black / Sick Yellow / Cold Blue.** One `curves` + `colorbalance` + `eq` + `vignette` chain
for every frame; night and radio scenes use the same chain swung toward a cold blue glow.
