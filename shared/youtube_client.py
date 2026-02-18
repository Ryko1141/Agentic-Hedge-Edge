"""
Hedge Edge — YouTube Client (OAuth2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YouTube Data API v3 — uploads, analytics, channel management.
Docs: https://developers.google.com/youtube/v3/docs

Usage:
    from shared.youtube_client import get_channel_stats, upload_video, list_videos
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _get_access_token() -> str:
    """Get a fresh access token using the refresh token."""
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("YouTube OAuth credentials must be set in .env")

    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}


def get_channel_stats() -> dict:
    """Get authenticated channel statistics."""
    r = requests.get(
        f"{BASE_URL}/channels",
        headers=_headers(),
        params={"part": "snippet,statistics,contentDetails", "mine": "true"},
        timeout=10,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return {}
    ch = items[0]
    return {
        "id": ch["id"],
        "title": ch["snippet"]["title"],
        "subscribers": int(ch["statistics"].get("subscriberCount", 0)),
        "views": int(ch["statistics"].get("viewCount", 0)),
        "videos": int(ch["statistics"].get("videoCount", 0)),
        "uploads_playlist": ch["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def list_videos(max_results: int = 10) -> list[dict]:
    """List recent videos on the authenticated channel."""
    r = requests.get(
        f"{BASE_URL}/search",
        headers=_headers(),
        params={
            "part": "snippet",
            "forMine": "true",
            "type": "video",
            "maxResults": max_results,
            "order": "date",
        },
        timeout=10,
    )
    r.raise_for_status()
    return [
        {
            "id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "published": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
        }
        for item in r.json().get("items", [])
    ]


def get_video_stats(video_id: str) -> dict:
    """Get statistics for a specific video."""
    r = requests.get(
        f"{BASE_URL}/videos",
        headers=_headers(),
        params={"part": "statistics,snippet", "id": video_id},
        timeout=10,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return {}
    v = items[0]
    return {
        "title": v["snippet"]["title"],
        "views": int(v["statistics"].get("viewCount", 0)),
        "likes": int(v["statistics"].get("likeCount", 0)),
        "comments": int(v["statistics"].get("commentCount", 0)),
    }


def upload_video(
    file_path: str,
    title: str,
    description: str,
    tags: list[str] = None,
    privacy: str = "private",
    category_id: str = "22",  # People & Blogs
) -> dict:
    """
    Upload a video to YouTube.
    
    Args:
        file_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        privacy: 'private', 'unlisted', or 'public'
        category_id: YouTube category (22=People&Blogs, 28=Science&Tech)
    """
    import json

    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy},
    }

    # Resumable upload initiation
    headers = _headers()
    headers["Content-Type"] = "application/json; charset=UTF-8"
    headers["X-Upload-Content-Type"] = "video/*"

    r = requests.post(
        f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
        headers=headers,
        data=json.dumps(metadata),
        timeout=30,
    )
    r.raise_for_status()
    upload_url = r.headers["Location"]

    # Upload video file
    with open(file_path, "rb") as f:
        r2 = requests.put(
            upload_url,
            headers={"Content-Type": "video/*"},
            data=f,
            timeout=600,
        )
        r2.raise_for_status()
        return r2.json()
