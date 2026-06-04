# YouTube Shorts Agent — CLAUDE.md

## What This Project Does
Fully automated YouTube Shorts publisher. Daily cron triggers Claude to:
1. Pick a viral psychology/science topic
2. Write a high-retention 45-second script
3. Generate voiceover via AWS Polly (Neural TTS)
4. Download B-roll footage from Pexels
5. Assemble 1080×1920 Short via ffmpeg with burned-in captions
6. Upload to YouTube via Data API v3

## Niche Strategy
- **Primary**: Psychology & Human Behavior Facts (global audience, infinite topics, high retention)
- **Secondary**: "What If" Science Scenarios (curiosity loop, 62-73% retention rate)

## Stack
- Orchestration: Python 3.12
- AI Scripting: **Claude Agent SDK** (claude-agent-sdk) — uses Claude Code subscription, zero API cost
- TTS: AWS Polly Neural (Matthew voice, US English)
- Footage: Pexels API (free, portrait-orientation)
- Video: ffmpeg (1080×1920, H.264, AAC, burned captions)
- Publishing: YouTube Data API v3 (OAuth2, token in AWS Secrets Manager)
- Schedule: AWS EventBridge (daily 9AM UTC)
- Runtime: AWS Lambda (container, 3GB RAM, 10min timeout)

## How Claude Code Auth Works
- No `ANTHROPIC_API_KEY` needed
- Uses `claude-agent-sdk` Python package
- Auth token stored at `~/.claude/` after running `claude login` once
- In Lambda: mount `~/.claude/` auth files via Lambda layer or SSM Parameter Store

## File Structure
```
main.py                  # Orchestrator + Lambda handler
steps/
  claude_cli.py          # Agent SDK wrapper (ask_claude, ask_claude_json)
  research.py            # Topic selection via Claude Agent SDK
  script.py              # Script generation via Claude Agent SDK
  voiceover.py           # AWS Polly Neural TTS
  visuals.py             # Pexels B-roll downloader
  assemble.py            # ffmpeg video pipeline
  publish.py             # YouTube Data API v3 upload
  cleanup.py             # Temp file cleanup
setup_youtube_auth.py    # One-time YouTube OAuth setup
aws-deploy.yaml          # CloudFormation (Lambda + EventBridge)
Dockerfile               # Lambda container image
CLAUDE.md                # This file
```

## Setup Order
1. `npm install -g @anthropic-ai/claude-code` (install Claude Code CLI)
2. `claude login` (one-time auth — stores token in ~/.claude/)
3. `pip install -r requirements.txt`
4. Copy `.env.example` → `.env`, fill in AWS + Pexels keys
5. Enable YouTube Data API v3 in Google Cloud Console
6. Run `python setup_youtube_auth.py --secret client_secret.json`
7. Test: `python main.py --niche psychology --dry-run`
8. Deploy: see aws-deploy.yaml

## Running Locally
```bash
# Dry run (renders video, skips YouTube upload)
python main.py --dry-run --niche psychology
python main.py --dry-run --niche whatif

# Full run with upload
python main.py --niche psychology

# AWS Lambda invoke
aws lambda invoke --function-name youtube-shorts-agent \
  --payload '{"niche":"psychology"}' response.json
```

## Extending Topics
Edit `PSYCHOLOGY_SEEDS` / `WHATIF_SEEDS` in `steps/research.py`.
Claude automatically picks the highest-retention angle from the candidates.

## Cost Estimate (per video)
- Claude Agent SDK: $0.00 (uses Claude Code subscription)
- AWS Polly Neural: ~$0.001
- Lambda (10min, 3GB): ~$0.005
- Pexels: Free
- **Total per video: ~$0.006**
- **Monthly (30 videos): ~$0.18**
