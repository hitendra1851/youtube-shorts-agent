"""
claude_cli.py
Thin wrapper around the Claude Agent SDK (claude-agent-sdk).
Uses your existing Claude Code subscription — zero Anthropic API costs.

Install: pip install claude-agent-sdk
Auth:    claude login  (one-time, stored in ~/.claude/)
Docs:    https://docs.anthropic.com/en/docs/claude-code/sdk
"""

import asyncio
import json
import re
from claude_agent_sdk import query, ClaudeAgentOptions


def ask_claude(prompt: str, system: str = None, max_tokens: int = 1000) -> str:
    """
    Sends a single prompt to Claude via the Agent SDK.
    Returns the final text response as a string.
    No API key needed — uses Claude Code subscription auth.
    """
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    async def _run():
        result_text = ""
        async for message in query(
            prompt=full_prompt,
            options=ClaudeAgentOptions(
                allowed_tools=[],          # text-only, no tools needed
                permission_mode="default",
            ),
        ):
            # ResultMessage carries the final response
            if hasattr(message, "result") and message.result:
                result_text = message.result
        return result_text

    return asyncio.run(_run())


def ask_claude_json(prompt: str, system: str = None) -> dict:
    """
    Calls Claude and parses the response as JSON.
    Strips markdown fences if present.
    """
    raw = ask_claude(prompt, system=system)
    
    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract first JSON object from response
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Claude response was not valid JSON:\n{raw[:300]}")
