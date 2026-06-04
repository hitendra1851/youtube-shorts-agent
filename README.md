# YouTube Shorts Agent

Fully automated YouTube Shorts publisher using Claude Agent SDK + AWS Polly + Pexels + ffmpeg

## Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | Python 3.12 |
| AI Scripting | Claude Agent SDK — uses Claude Code subscription, zero API cost |
| TTS | AWS Polly Neural (Matthew voice, US English) |
| Footage | Pexels API (free, portrait-orientation) |
| Video | ffmpeg (1080×1920, H.264, AAC, burned captions) |
| Publishing | YouTube Data API v3 (OAuth2, token in AWS Secrets Manager) |
| Schedule | AWS EventBridge (daily 9AM UTC) |
| Runtime | AWS Lambda (container, 3GB RAM, 10min timeout) |

## Setup

1. `npm install -g @anthropic-ai/claude-code` — install Claude Code CLI
2. `claude login` — one-time auth, stores token in `~/.claude/`
3. `pip install -r requirements.txt`
4. Copy `.env.example` → `.env` and fill in AWS + Pexels keys
5. Enable YouTube Data API v3 in Google Cloud Console

## Cost

| Item | Cost |
|------|------|
| Claude Agent SDK | $0.00 (Claude Code subscription) |
| AWS Polly Neural | ~$0.001 |
| Lambda (10min, 3GB) | ~$0.005 |
| Pexels | Free |
| **Total per video** | **~$0.006** |
| Monthly (30 videos) | ~$0.18 |
