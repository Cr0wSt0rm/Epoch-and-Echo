# Epoch-and-Echo

Modular Python pipeline for automating YouTube history videos: research a topic,
write a script, synthesize narration, generate visuals, assemble the video, and
upload it.

## Project structure

```
.
├── config/
│   ├── __init__.py
│   └── settings.py          # loads .env, exposes Settings and output Paths
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point / orchestrator
│   ├── models.py            # Topic, Scene, Script, VideoAsset dataclasses
│   ├── topic_research.py    # stage 1: pick + research a topic
│   ├── script_generator.py  # stage 2: write the narrated script
│   ├── voiceover.py         # stage 3: TTS            -> output/audio/
│   ├── image_generator.py   # stage 4: visuals        -> output/images/
│   ├── video_assembler.py   # stage 5: render video   -> output/final_videos/
│   └── uploader.py          # stage 6: publish to YouTube
├── output/
│   ├── audio/
│   ├── images/
│   └── final_videos/
├── .env.example             # API key template (copy to .env)
├── .gitignore
├── requirements.txt
└── README.md
```

Each stage is a standalone module with a single public function, so
implementations can be swapped (different TTS vendor, image model, etc.) without
touching the rest of the pipeline.

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your API keys
python -m src.main --check-env
```

Run the full pipeline for a topic:

```bash
python -m src.main "The Fall of Constantinople"
python -m src.main "The Fall of Constantinople" --upload
```

The stage modules are currently skeletons that raise `NotImplementedError`;
fill them in as each integration is added, and pin the dependencies you use in
`requirements.txt`.
