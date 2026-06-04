"""
Step 5: Assemble — ffmpeg
Stitches B-roll clips + voiceover + captions into a 9:16 YouTube Short.
Output: 1080x1920, H.264, AAC audio, burned-in captions.
"""

import os
import subprocess
import json
import textwrap
from steps.voiceover import get_audio_duration


def assemble_video(clips: list, audio_path: str, script: dict, output_dir: str) -> str:
    """
    Assembles final Short video.
    Returns path to final MP4.
    """
    audio_duration = get_audio_duration(audio_path)
    # Add 1s buffer at end
    total_duration = audio_duration + 1.0

    # Step A: Normalize all clips to 1080x1920, trim/loop to fill duration
    normalized = _normalize_clips(clips, total_duration, output_dir)

    # Step B: Concatenate normalized clips
    concat_path = os.path.join(output_dir, "concat.mp4")
    _concatenate_clips(normalized, concat_path)

    # Step C: Add voiceover audio
    with_audio_path = os.path.join(output_dir, "with_audio.mp4")
    _add_audio(concat_path, audio_path, with_audio_path, total_duration)

    # Step D: Burn in captions + title overlay
    final_path = os.path.join(output_dir, "final_short.mp4")
    _add_captions(with_audio_path, script, final_path, total_duration)

    return final_path


def _normalize_clips(clips: list, total_duration: float, output_dir: str) -> list:
    """Resize and pad each clip to 1080x1920 (9:16 portrait)."""
    normalized = []
    norm_dir = os.path.join(output_dir, "normalized")
    os.makedirs(norm_dir, exist_ok=True)

    per_clip = total_duration / max(len(clips), 1)

    for i, clip in enumerate(clips):
        out_path = os.path.join(norm_dir, f"norm_{i:02d}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",        # loop clip if too short
            "-i", clip["path"],
            "-t", str(per_clip + 0.5),   # slight overlap for smooth concat
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "setsar=1"
            ),
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-an",                        # no audio from clips
            out_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        normalized.append({"path": out_path, "duration": per_clip})

    return normalized


def _concatenate_clips(normalized: list, output_path: str):
    """Concat all normalized clips using ffmpeg concat demuxer."""
    # Write concat list file
    list_path = os.path.join(os.path.dirname(output_path), "concat_list.txt")
    with open(list_path, "w") as f:
        for clip in normalized:
            f.write(f"file '{os.path.abspath(clip['path'])}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _add_audio(video_path: str, audio_path: str, output_path: str, duration: float):
    """Mix voiceover onto video, trim to exact duration."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(duration),
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _add_captions(video_path: str, script: dict, output_path: str, duration: float):
    """
    Burn captions + semi-transparent title bar onto video using ffmpeg drawtext.
    Large white bold text, centered, lower-third style.
    """
    title = script.get("title", "").replace("#Shorts", "").strip()
    # Shorten title for overlay display
    display_title = title[:45] + "..." if len(title) > 45 else title

    caption_segments = script.get("caption_segments", [])

    # Build drawtext filter chain
    filters = []

    # Dark gradient overlay at bottom for caption readability
    filters.append(
        "drawbox=x=0:y=ih*0.72:w=iw:h=ih*0.25:color=black@0.55:t=fill"
    )

    # Title at very top (first 3 seconds)
    safe_title = display_title.replace("'", "\\'").replace(":", "\\:")
    filters.append(
        f"drawtext=text='{safe_title}':"
        f"fontsize=42:fontcolor=white:x=(w-text_w)/2:y=80:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"enable='between(t,0,3)':"
        f"shadowcolor=black:shadowx=2:shadowy=2"
    )

    # Caption segments — centered lower third
    for seg in caption_segments[:12]:  # max 12 caption lines
        text = seg.get("text", "").strip()
        if not text:
            continue
        # Wrap long lines
        wrapped = textwrap.fill(text, width=28)
        safe_text = wrapped.replace("'", "\\'").replace(":", "\\:").replace("\n", " ")
        start = seg.get("start_sec", 0)
        end = seg.get("start_sec", 0) + 3.5  # show each caption for ~3.5s

        filters.append(
            f"drawtext=text='{safe_text}':"
            f"fontsize=52:fontcolor=white:x=(w-text_w)/2:y=h*0.78:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"enable='between(t,{start},{min(end, duration)})':"
            f"shadowcolor=black:shadowx=3:shadowy=3"
        )

    # Subscribe CTA in final 5 seconds
    filters.append(
        f"drawtext=text='👆 Follow for more':"
        f"fontsize=44:fontcolor=yellow:x=(w-text_w)/2:y=h*0.88:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"enable='between(t,{max(0, duration-5)},{duration})':"
        f"shadowcolor=black:shadowx=2:shadowy=2"
    )

    vf = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    
    # If caption rendering fails (font issues), fallback to no captions
    if result.returncode != 0:
        print("  Warning: Caption rendering failed, using video without captions")
        import shutil
        shutil.copy(video_path, output_path)
