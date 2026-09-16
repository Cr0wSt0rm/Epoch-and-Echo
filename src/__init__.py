"""Epoch & Echo history video automation pipeline.

Every scene maps exactly Narration Text -> Audio -> Image -> Video Stitching:

1. `topic_research`   - select the topic (research happens while scripting)
2. `script_generator` - validate the Cursor-authored script (Pydantic)
3. `voiceover`        - ElevenLabs narration per scene  -> output/audio/
4. `image_generator`  - ComfyUI still per scene         -> output/images/
5. `video_assembler`  - FFmpeg stitch in scene order    -> output/final_videos/
6. `uploader`         - publish the final video to YouTube
"""

__version__ = "0.2.0"
