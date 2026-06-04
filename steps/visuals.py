"""
Step 4: Visuals — Pexels API
Downloads free B-roll video clips matching script keywords.
Clips are vertical (portrait) or will be cropped to 9:16 by ffmpeg.
"""

import os
import requests
import random

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
TARGET_CLIPS = 4          # Number of clips to download
MIN_CLIP_DURATION = 5     # Minimum clip length in seconds
MAX_CLIP_DURATION = 15    # Maximum clip length in seconds


def fetch_broll(keywords: list, output_dir: str) -> list:
    """
    Downloads B-roll video clips from Pexels for given keywords.
    Returns list of local file paths.
    """
    clips = []
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    headers = {"Authorization": PEXELS_API_KEY}

    for i, keyword in enumerate(keywords[:TARGET_CLIPS]):
        try:
            # Search Pexels for vertical/portrait videos
            params = {
                "query": keyword,
                "orientation": "portrait",
                "size": "medium",
                "per_page": 10,
            }
            response = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            videos = data.get("videos", [])
            if not videos:
                # Fallback: try landscape (ffmpeg will crop to 9:16)
                params["orientation"] = "landscape"
                response = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=10)
                data = response.json()
                videos = data.get("videos", [])

            if not videos:
                print(f"  No clips found for keyword: {keyword}")
                continue

            # Pick a random video from results for variety
            video = random.choice(videos[:5])
            
            # Get best quality video file that fits duration range
            video_files = sorted(
                video.get("video_files", []),
                key=lambda x: x.get("width", 0),
                reverse=True,
            )

            download_url = None
            for vf in video_files:
                duration = video.get("duration", 0)
                if MIN_CLIP_DURATION <= duration <= MAX_CLIP_DURATION:
                    download_url = vf.get("link")
                    break
            
            if not download_url and video_files:
                download_url = video_files[0].get("link")

            if not download_url:
                continue

            # Download the clip
            clip_path = os.path.join(clips_dir, f"clip_{i:02d}_{keyword.replace(' ', '_')}.mp4")
            clip_response = requests.get(download_url, stream=True, timeout=30)
            clip_response.raise_for_status()

            with open(clip_path, "wb") as f:
                for chunk in clip_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            clips.append({
                "path": clip_path,
                "keyword": keyword,
                "duration": video.get("duration", 10),
                "width": video_files[0].get("width", 1080) if video_files else 1080,
                "height": video_files[0].get("height", 1920) if video_files else 1920,
            })
            print(f"  Downloaded clip for '{keyword}': {os.path.basename(clip_path)}")

        except Exception as e:
            print(f"  Warning: Could not download clip for '{keyword}': {e}")
            continue

    # If we got no clips at all, use a fallback solid color background
    if not clips:
        clips = _generate_fallback_clips(clips_dir, TARGET_CLIPS)

    return clips


def _generate_fallback_clips(clips_dir: str, count: int) -> list:
    """
    Generates simple solid-color background clips using ffmpeg as fallback.
    """
    import subprocess
    clips = []
    colors = ["#0a0a1a", "#1a0a2e", "#0d1b2a", "#16213e"]
    
    for i in range(count):
        path = os.path.join(clips_dir, f"fallback_{i:02d}.mp4")
        color = colors[i % len(colors)]
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color.lstrip('#')}:size=1080x1920:rate=30",
            "-t", "10",
            "-c:v", "libx264",
            path
        ], capture_output=True)
        clips.append({"path": path, "keyword": "fallback", "duration": 10, "width": 1080, "height": 1920})
    
    return clips
