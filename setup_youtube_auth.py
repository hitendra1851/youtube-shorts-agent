"""
setup_youtube_auth.py
Run this ONCE locally to generate OAuth2 token and store in AWS Secrets Manager.

Steps:
1. Go to Google Cloud Console → Enable YouTube Data API v3
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download client_secret.json
4. Run: python setup_youtube_auth.py --secret client_secret.json
5. Authorize in browser
6. Token is stored in AWS Secrets Manager automatically
"""

import json
import os
import argparse
import boto3
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SECRET_NAME = os.getenv("YOUTUBE_SECRET_NAME", "youtube-shorts-agent/oauth-token")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--secret", required=True, help="Path to client_secret.json from Google Cloud")
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.secret, SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }

    sm = boto3.client("secretsmanager", region_name=AWS_REGION)
    try:
        sm.create_secret(
            Name=SECRET_NAME,
            SecretString=json.dumps(token_data),
            Description="YouTube OAuth2 token for Shorts agent",
        )
        print(f"✅ Token stored in Secrets Manager: {SECRET_NAME}")
    except sm.exceptions.ResourceExistsException:
        sm.update_secret(SecretId=SECRET_NAME, SecretString=json.dumps(token_data))
        print(f"✅ Token updated in Secrets Manager: {SECRET_NAME}")


if __name__ == "__main__":
    main()
