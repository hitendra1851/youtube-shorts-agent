"""
Step 3: Voiceover — AWS Polly (Neural TTS)
Converts script narration to MP3 audio.
Uses Neural engine for natural-sounding voice.
"""

import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# AWS Polly neural voices — pick one that sounds engaging for psychology content
# Options: Matthew (US Male), Joanna (US Female), Amy (UK Female), Brian (UK Male)
POLLY_VOICE = os.getenv("POLLY_VOICE", "Matthew")
POLLY_ENGINE = "neural"  # Neural sounds far better than standard
POLLY_REGION = os.getenv("AWS_REGION", "us-east-1")


def generate_voiceover(narration: str, output_dir: str) -> str:
    """
    Converts narration text to MP3 using AWS Polly Neural TTS.
    Returns path to output audio file.
    """
    polly = boto3.client(
        "polly",
        region_name=POLLY_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    # Clean narration — remove any accidental stage directions
    clean_text = narration.strip()

    try:
        response = polly.synthesize_speech(
            Text=clean_text,
            OutputFormat="mp3",
            VoiceId=POLLY_VOICE,
            Engine=POLLY_ENGINE,
            # Add SSML prosody for natural Short pacing
            TextType="ssml" if clean_text.startswith("<speak>") else "text",
            SampleRate="24000",
        )
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"AWS Polly error: {e}")

    audio_path = os.path.join(output_dir, "voiceover.mp3")
    with open(audio_path, "wb") as f:
        f.write(response["AudioStream"].read())

    return audio_path


def get_audio_duration(audio_path: str) -> float:
    """
    Returns audio duration in seconds using ffprobe.
    """
    import subprocess
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            audio_path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 45.0  # fallback default
