"""
Step 6: Publish — YouTube Data API v3
Uploads the Short to YouTube with optimized metadata.
Credentials stored in AWS Secrets Manager.
"""

import os
import json
import boto3
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SECRET_NAME = os.getenv("YOUTUBE_SECRET_NAME", "youtube-shorts-agent/oauth-token")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Category IDs: 27=Education, 28=Science & Technology, 22=People & Blogs
CATEGORY_ID = "27"  # Education — best for psychology/science content


def _get_credentials() -> Credentials:
    """
    Loads OAuth2 credentials from AWS Secrets Manager.
    On first run, generate token locally with setup_youtube_auth.py
    then store in Secrets Manager.
    """
    sm = boto3.client("secretsmanager", region_name=AWS_REGION)
    
    try:
        secret = sm.get_secret_value(SecretId=SECRET_NAME)
        token_data = json.loads(secret["SecretString"])
        
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=YOUTUBE_SCOPES,
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token back to Secrets Manager
            updated = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
            }
            sm.update_secret(SecretId=SECRET_NAME, SecretString=json.dumps(updated))

        return creds

    except sm.exceptions.ResourceNotFoundException:
        raise RuntimeError(
            f"YouTube credentials not found in Secrets Manager (key: {SECRET_NAME}). "
            "Run setup_youtube_auth.py first to generate and store OAuth token."
        )


def upload_to_youtube(video_path: str, script: dict) -> dict:
    """
    Uploads video to YouTube as a Short.
    Returns YouTube API response with video ID.
    """
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    title = script.get("title", "Mind-Blowing Psychology Fact #Shorts")
    description = script.get("description", "")
    tags = script.get("tags", ["Shorts", "psychology", "facts", "mindblowing"])

    # Ensure Shorts-friendly metadata
    if "#Shorts" not in title and "#shorts" not in title:
        title = title[:90] + " #Shorts"

    body = {
        "snippet": {
            "title": title[:100],          # YouTube title limit
            "description": description[:5000],
            "tags": tags[:15],             # YouTube tag limit
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,  # 4MB chunks
    )

    try:
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"  Upload progress: {progress}%")

        return response

    except HttpError as e:
        raise RuntimeError(f"YouTube upload failed: {e.resp.status} — {e.content}")
