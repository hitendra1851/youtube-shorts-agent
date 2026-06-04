"""
Step 1: Research
Picks today's viral topic using Claude Code (Agent SDK).
No Anthropic API key needed — uses your Claude Code subscription.
"""

import random
from steps.claude_cli import ask_claude_json

PSYCHOLOGY_SEEDS = [
    "false memories and how the brain fabricates them",
    "why humans feel physical pain from social rejection",
    "the brain cannot distinguish imagination from reality during sleep",
    "why we remember emotional events more vividly than neutral ones",
    "the psychological reason behind feeling watched when alone",
    "why boredom is more dangerous than stress",
    "how your birth order rewires your personality",
    "the dark side of always being agreeable",
    "why your brain replays embarrassing memories at 2am",
    "the psychological trick behind why sad music feels good",
    "how loneliness physically changes your brain structure",
    "why humans fear uncertainty more than bad news",
    "the reason you cannot remember being a toddler",
    "how strangers predict your personality better than you can",
    "why your brain treats social exclusion the same as physical pain",
    "the placebo effect works even when you know it is a placebo",
    "why sleep deprivation makes you more aggressive",
    "how chronic stress shrinks the hippocampus",
    "the psychology behind why we root for underdogs",
    "why humans are the only species that cry from emotion",
]

WHATIF_SEEDS = [
    "what if the sun disappeared for exactly 1 second",
    "what if humans had 360-degree vision",
    "what if Earth gravity suddenly doubled",
    "what if all bacteria on Earth vanished overnight",
    "what if humans could photosynthesize like plants",
    "what if the moon disappeared tomorrow",
    "what if humans only needed 2 hours of sleep",
    "what if Earth stopped rotating for 1 minute",
    "what if humans had echolocation like bats",
    "what if all oceans evaporated instantly",
]


def fetch_topic(niche: str, sources: list) -> dict:
    seeds = PSYCHOLOGY_SEEDS if niche == "psychology" else WHATIF_SEEDS
    candidates = random.sample(seeds, min(5, len(seeds)))

    prompt = f"""You are a viral YouTube Shorts strategist. Given these topic candidates, 
pick the ONE most likely to get 1M+ views as a 45-second Short in 2026.

Candidates:
{chr(10).join(f"- {c}" for c in candidates)}

Return ONLY a JSON object (no markdown, no explanation):
{{
  "title": "The exact hook title for the Short (under 60 chars, starts with a surprising fact or question)",
  "seed": "the chosen candidate",
  "angle": "the specific surprising angle that makes this viral",
  "why_viral": "one sentence on why this gets replayed and shared",
  "visual_keywords": ["3-5 single-word Pexels search terms for B-roll footage"]
}}"""

    topic = ask_claude_json(prompt)
    topic["niche"] = niche
    return topic
