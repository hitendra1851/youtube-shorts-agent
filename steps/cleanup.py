"""Step 7: Cleanup — removes temp files after upload."""
import os, shutil

def cleanup_output(output_dir: str, keep_video: bool = False):
    for sub in ["clips", "normalized", "concat_list.txt"]:
        p = os.path.join(output_dir, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.isfile(p):
            os.remove(p)
    for f in ["concat.mp4", "with_audio.mp4", "voiceover.mp3"]:
        p = os.path.join(output_dir, f)
        if os.path.isfile(p):
            os.remove(p)
    if not keep_video:
        final = os.path.join(output_dir, "final_short.mp4")
        if os.path.isfile(final):
            os.remove(final)
        if os.path.isdir(output_dir) and not os.listdir(output_dir):
            os.rmdir(output_dir)
