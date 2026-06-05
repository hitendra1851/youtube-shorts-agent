"""
setup_claude_auth.py
Run this ONCE on your local machine to store your Claude Code OAuth credentials
in AWS Secrets Manager so the Lambda can authenticate for free using your
Claude Pro/Max subscription.

Steps:
1. Make sure you've run `claude login` at least once on this machine
2. Run: python setup_claude_auth.py
3. The script reads ~/.claude.json and stores it securely in Secrets Manager
"""

import json
import os
import sys
from pathlib import Path

import boto3

SECRET_NAME = os.getenv("CLAUDE_SECRET_NAME", "youtube-shorts-agent/claude-auth")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1"))


def find_claude_json() -> Path:
    candidates = [
        Path.home() / ".claude.json",
        Path(os.environ.get("APPDATA", "")) / "claude" / ".claude.json",
        Path(os.environ.get("LOCALAPPDATA", "")) / "claude" / ".claude.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def main():
    claude_json_path = find_claude_json()
    if not claude_json_path:
        print("ERROR: Could not find ~/.claude.json — run 'claude login' first.")
        print("  Mac/Linux: ~/.claude.json")
        print("  Windows:   %USERPROFILE%\\.claude.json")
        sys.exit(1)

    print(f"Found Claude credentials at: {claude_json_path}")
    claude_data = json.loads(claude_json_path.read_text(encoding="utf-8"))

    # Wrap in a container so we can add more fields later (e.g. .claude/ dir)
    secret_payload = {"claude_json": claude_data}

    sm = boto3.client("secretsmanager", region_name=AWS_REGION)
    try:
        sm.create_secret(
            Name=SECRET_NAME,
            SecretString=json.dumps(secret_payload),
            Description="Claude Code OAuth credentials for YouTube Shorts agent Lambda",
        )
        print(f"✅ Stored in Secrets Manager: {SECRET_NAME}")
    except sm.exceptions.ResourceExistsException:
        sm.update_secret(
            SecretId=SECRET_NAME,
            SecretString=json.dumps(secret_payload),
        )
        print(f"✅ Updated in Secrets Manager: {SECRET_NAME}")

    print(f"\nRegion: {AWS_REGION}")
    print("Lambda will now authenticate using your Claude Pro/Max subscription.")


if __name__ == "__main__":
    main()
