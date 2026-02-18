"""
Hedge Edge — LinkedIn Client (OAuth2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LinkedIn API v2 — posts, articles, profile, analytics.
Docs: https://learn.microsoft.com/en-us/linkedin/

Usage:
    from shared.linkedin_client import get_profile, create_post, get_post_stats
"""

import os
import json
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://api.linkedin.com/v2"
REST_URL = "https://api.linkedin.com/rest"


def _headers() -> dict:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN must be set in .env")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202402",
    }


def _get_person_urn() -> str:
    """Get the authenticated user's person URN."""
    r = requests.get(f"{BASE_URL}/userinfo", headers=_headers(), timeout=10)
    r.raise_for_status()
    return f"urn:li:person:{r.json()['sub']}"


def get_profile() -> dict:
    """Get authenticated user's profile info."""
    r = requests.get(f"{BASE_URL}/userinfo", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def create_text_post(text: str) -> dict:
    """
    Create a text-only LinkedIn post.
    
    Args:
        text: Post content (max 3000 chars)
    """
    person_urn = _get_person_urn()
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = requests.post(
        f"{BASE_URL}/ugcPosts",
        headers=_headers(),
        data=json.dumps(payload),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def create_article_post(text: str, article_url: str, title: str,
                        description: str = "") -> dict:
    """
    Create a LinkedIn post with an article link.
    
    Args:
        text: Post commentary text
        article_url: URL of the article to share
        title: Article title shown in preview
        description: Article description shown in preview
    """
    person_urn = _get_person_urn()
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "originalUrl": article_url,
                        "title": {"text": title},
                        "description": {"text": description},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = requests.post(
        f"{BASE_URL}/ugcPosts",
        headers=_headers(),
        data=json.dumps(payload),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def create_image_post(text: str, image_path: str) -> dict:
    """
    Create a LinkedIn post with an image.
    
    Args:
        text: Post text
        image_path: Local path to image file
    """
    person_urn = _get_person_urn()
    headers = _headers()

    # Step 1: Register upload
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    r1 = requests.post(
        f"{BASE_URL}/assets?action=registerUpload",
        headers=headers,
        data=json.dumps(register_payload),
        timeout=15,
    )
    r1.raise_for_status()
    upload_data = r1.json()["value"]
    upload_url = upload_data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset = upload_data["asset"]

    # Step 2: Upload binary
    with open(image_path, "rb") as f:
        r2 = requests.put(
            upload_url,
            headers={"Authorization": headers["Authorization"]},
            data=f,
            timeout=60,
        )
        r2.raise_for_status()

    # Step 3: Create post with image
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": asset}],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r3 = requests.post(
        f"{BASE_URL}/ugcPosts",
        headers=headers,
        data=json.dumps(payload),
        timeout=15,
    )
    r3.raise_for_status()
    return r3.json()


def refresh_token() -> dict:
    """Refresh LinkedIn access token using refresh_token. Updates .env."""
    from shared.refresh_linkedin import refresh_linkedin_token
    return refresh_linkedin_token()
