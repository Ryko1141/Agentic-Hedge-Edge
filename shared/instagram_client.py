"""
Hedge Edge — Instagram Client (Graph API)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instagram Graph API for @hedgeedge — posts, stories, insights, media.
Docs: https://developers.facebook.com/docs/instagram-api

Usage:
    from shared.instagram_client import get_profile, publish_post, get_insights
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://graph.facebook.com/v19.0"


def _token() -> str:
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN must be set in .env")
    return token


def _ig_id() -> str:
    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    if not ig_id:
        raise RuntimeError("INSTAGRAM_ACCOUNT_ID must be set in .env")
    return ig_id


def get_profile() -> dict:
    """Get @hedgeedge profile stats."""
    r = requests.get(
        f"{BASE_URL}/{_ig_id()}",
        params={
            "fields": "id,username,name,biography,followers_count,follows_count,media_count,profile_picture_url",
            "access_token": _token(),
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_media(limit: int = 10) -> list[dict]:
    """List recent media posts."""
    r = requests.get(
        f"{BASE_URL}/{_ig_id()}/media",
        params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
            "limit": limit,
            "access_token": _token(),
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def get_insights(period: str = "day", metrics: str = "impressions,reach,profile_views") -> list[dict]:
    """
    Get account-level insights.
    
    Args:
        period: 'day', 'week', 'days_28', 'month', 'lifetime'
        metrics: Comma-separated metric names
    """
    r = requests.get(
        f"{BASE_URL}/{_ig_id()}/insights",
        params={
            "metric": metrics,
            "period": period,
            "access_token": _token(),
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def publish_post(image_url: str, caption: str) -> dict:
    """
    Publish a single image post (2-step process).
    
    Args:
        image_url: Public URL of the image
        caption: Post caption with hashtags
    """
    # Step 1: Create media container
    r1 = requests.post(
        f"{BASE_URL}/{_ig_id()}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": _token(),
        },
        timeout=30,
    )
    r1.raise_for_status()
    container_id = r1.json()["id"]

    # Step 2: Publish the container
    r2 = requests.post(
        f"{BASE_URL}/{_ig_id()}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": _token(),
        },
        timeout=30,
    )
    r2.raise_for_status()
    return r2.json()


def publish_carousel(image_urls: list[str], caption: str) -> dict:
    """
    Publish a carousel post (multiple images).
    
    Args:
        image_urls: List of public image URLs (2-10)
        caption: Post caption
    """
    children = []
    for url in image_urls:
        r = requests.post(
            f"{BASE_URL}/{_ig_id()}/media",
            params={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": _token(),
            },
            timeout=30,
        )
        r.raise_for_status()
        children.append(r.json()["id"])

    # Create carousel container
    r2 = requests.post(
        f"{BASE_URL}/{_ig_id()}/media",
        params={
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": _token(),
        },
        timeout=30,
    )
    r2.raise_for_status()
    container_id = r2.json()["id"]

    # Publish
    r3 = requests.post(
        f"{BASE_URL}/{_ig_id()}/media_publish",
        params={"creation_id": container_id, "access_token": _token()},
        timeout=30,
    )
    r3.raise_for_status()
    return r3.json()


def publish_reel(video_url: str, caption: str, cover_url: Optional[str] = None,
                 share_to_feed: bool = True) -> dict:
    """
    Publish a Reel.
    
    Args:
        video_url: Public URL of the video (MP4, 3-90 seconds)
        caption: Reel caption
        cover_url: Optional cover image URL
        share_to_feed: Whether to also share to feed
    """
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": str(share_to_feed).lower(),
        "access_token": _token(),
    }
    if cover_url:
        params["cover_url"] = cover_url

    r1 = requests.post(f"{BASE_URL}/{_ig_id()}/media", params=params, timeout=60)
    r1.raise_for_status()
    container_id = r1.json()["id"]

    # Poll until ready, then publish
    import time
    for _ in range(30):
        check = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": _token()},
            timeout=10,
        )
        status = check.json().get("status_code")
        if status == "FINISHED":
            break
        time.sleep(5)

    r2 = requests.post(
        f"{BASE_URL}/{_ig_id()}/media_publish",
        params={"creation_id": container_id, "access_token": _token()},
        timeout=30,
    )
    r2.raise_for_status()
    return r2.json()
