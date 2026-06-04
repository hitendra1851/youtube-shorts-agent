"""
Step 2: Script Generation
Claude Code (Agent SDK) writes a high-retention 45-second Short script.
Format: Hook (3s) → Body (35s) → Payoff + CTA (7s)
No Anthropic API key needed — uses your Claude Code subscription.
"""

import json
from steps.claude_cli import ask_claude_json

SCRIPT_SYSTEM = """You are a viral YouTube Shorts scriptwriter specializing in 
psychology and science content. You write scripts that:
- Hook viewers in the FIRST 3 SECONDS with a shocking or counterintuitive statement
- Use short punchy sentences (max 12 words each)
- Build curiosity throughout — never reveal the payoff early
- End with a twist or "so next time you..." moment that triggers shares
- Target the 25-34 global audience who loves self-understanding content
- Sound conversational, NOT like a Wikipedia article
- Total duration: 40-50 seconds when spoken at normal pace"""


def generate_script(topic: dict, config: dict) -> dict:
    prompt = f"""{SCRIPT_SYSTEM}

Write a YouTube Shorts script for this topic:

TOPIC: {topic['title']}
ANGLE: {topic['angle']}
TONE: {config['tone']}
HOOK STYLE: {config['hook_style']}

Return ONLY a JSON object (no markdown):
{{
  "title": "YouTube video title with #Shorts at end (max 70 chars, curiosity-driven)",
  "narration": "The full spoken script. Use line breaks between sentences. NO stage directions. Pure speech text only.",
  "description": "YouTube description (3-4 sentences, includes keywords, ends with subscribe CTA)",
  "tags": ["8-10 relevant tags as array"],
  "visual_keywords": {json.dumps(topic.get('visual_keywords', ['brain', 'science', 'psychology']))},
  "caption_segments": [
    {{"text": "First sentence", "start_sec": 0}},
    {{"text": "Second sentence", "start_sec": 3}}
  ]
}}

RULES:
- narration must be 110-140 words (fits 40-50 seconds)
- First sentence must be under 12 words and shocking
- caption_segments: one entry per sentence with estimated start_sec
- tags must include: Shorts, psychology, facts, mindblowing"""

    script = ask_claude_json(prompt)

    if "#Shorts" not in script["title"] and "#shorts" not in script["title"]:
        script["title"] = script["title"].rstrip() + " #Shorts"

    return script
