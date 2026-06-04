"""
YouTube Shorts Agent - Orchestrator
Niche: Psychology & Human Behavior Facts + "What If" Science
Stack: Claude Code Agent SDK → AWS Polly (TTS) → Pexels (footage) → ffmpeg → YouTube API
Schedule: AWS EventBridge → Lambda trigger (daily)

No Anthropic API key needed — uses Claude Code subscription via Agent SDK.
Run `claude login` once before deploying.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

from steps.research import fetch_topic
from steps.script import generate_script
from steps.voiceover import generate_voiceover
from steps.visuals import fetch_broll
from steps.assemble import assemble_video
from steps.publish import upload_to_youtube
from steps.cleanup import cleanup_output

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


NICHE_CONFIG = {
    "psychology": {
        "description": "Mind-blowing psychology and human behavior facts",
        "tone": "curious, slightly unsettling, conversational",
        "hook_style": "counterintuitive fact that challenges assumptions",
        "sources": ["psychology_news", "pubmed_abstracts", "prebuilt_topics"],
    },
    "whatif": {
        "description": "What if hypothetical science scenarios",
        "tone": "excited, dramatic, educational",
        "hook_style": "impossible scenario with real scientific explanation",
        "sources": ["prebuilt_topics"],
    },
}


def run_agent(niche: str = "psychology", dry_run: bool = False):
    log.info(f"=== YouTube Shorts Agent Starting | Niche: {niche} ===")
    config = NICHE_CONFIG.get(niche, NICHE_CONFIG["psychology"])
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"output/{run_id}"
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 1: Research — find today's topic
        log.info("Step 1/6: Researching topic...")
        topic = fetch_topic(niche, config["sources"])
        log.info(f"  Topic: {topic['title']}")

        # Step 2: Script — Claude generates hook + body + CTA
        log.info("Step 2/6: Generating script...")
        script = generate_script(topic, config)
        log.info(f"  Script length: {len(script['narration'])} chars")
        log.info(f"  Title: {script['title']}")

        # Step 3: Voiceover — AWS Polly TTS
        log.info("Step 3/6: Generating voiceover (AWS Polly)...")
        audio_path = generate_voiceover(script["narration"], output_dir)
        log.info(f"  Audio: {audio_path}")

        # Step 4: Visuals — Pexels B-roll footage
        log.info("Step 4/6: Fetching B-roll visuals (Pexels)...")
        clips = fetch_broll(script["visual_keywords"], output_dir)
        log.info(f"  Clips downloaded: {len(clips)}")

        # Step 5: Assemble — ffmpeg stitches everything
        log.info("Step 5/6: Assembling video (ffmpeg)...")
        video_path = assemble_video(clips, audio_path, script, output_dir)
        log.info(f"  Video: {video_path}")

        if dry_run:
            log.info("DRY RUN — skipping YouTube upload.")
            log.info(f"Video ready at: {video_path}")
            return video_path

        # Step 6: Publish — YouTube Data API v3
        log.info("Step 6/6: Uploading to YouTube...")
        result = upload_to_youtube(video_path, script)
        log.info(f"  Uploaded! Video ID: {result['id']}")
        log.info(f"  URL: https://youtube.com/shorts/{result['id']}")

        # Cleanup temp files
        cleanup_output(output_dir, keep_video=False)

        log.info("=== Agent Run Complete ✓ ===")
        return result

    except Exception as e:
        log.error(f"Agent failed at step: {e}", exc_info=True)
        raise


# AWS Lambda handler
def lambda_handler(event, context):
    niche = event.get("niche", "psychology")
    return run_agent(niche=niche)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Shorts Agent")
    parser.add_argument("--niche", default="psychology", choices=["psychology", "whatif"])
    parser.add_argument("--dry-run", action="store_true", help="Skip YouTube upload")
    args = parser.parse_args()
    run_agent(niche=args.niche, dry_run=args.dry_run)
