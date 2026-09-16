"""YouTube history video automation pipeline.

Stages (each lives in its own module so they can be swapped or tested alone):

1. `topic_research`   - pick and research a historical topic
2. `script_generator` - turn research into a narrated script
3. `voiceover`        - synthesize narration audio  -> output/audio/
4. `image_generator`  - create visuals per scene     -> output/images/
5. `video_assembler`  - combine audio + images       -> output/final_videos/
6. `uploader`         - publish the final video to YouTube
"""

__version__ = "0.1.0"
