"""
Hedge Edge — Discord Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bot messaging, channel management, and webhook posting.

Usage:
    from shared.discord_client import send_message, send_embed, get_guild_info
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://discord.com/api/v10"


def _headers() -> dict:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN must be set in .env")
    return {"Authorization": f"Bot {token}", "Content-Type": "application/json"}


def send_message(channel_id: str, content: str) -> dict:
    """Send a text message to a Discord channel."""
    r = requests.post(
        f"{BASE_URL}/channels/{channel_id}/messages",
        headers=_headers(),
        json={"content": content},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def send_embed(channel_id: str, title: str, description: str,
               color: int = 0x00D4AA, fields: Optional[list[dict]] = None) -> dict:
    """Send a rich embed to a Discord channel."""
    embed = {"title": title, "description": description, "color": color}
    if fields:
        embed["fields"] = fields
    r = requests.post(
        f"{BASE_URL}/channels/{channel_id}/messages",
        headers=_headers(),
        json={"embeds": [embed]},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_guild_info(guild_id: str) -> dict:
    """Get guild (server) information."""
    r = requests.get(f"{BASE_URL}/guilds/{guild_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def get_guild_channels(guild_id: str) -> list[dict]:
    """List all channels in a guild."""
    r = requests.get(f"{BASE_URL}/guilds/{guild_id}/channels", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def get_guild_members(guild_id: str, limit: int = 100) -> list[dict]:
    """List guild members."""
    r = requests.get(
        f"{BASE_URL}/guilds/{guild_id}/members",
        headers=_headers(),
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def post_webhook(webhook_url: str, content: str, username: str = "Hedge Edge") -> dict:
    """Post via a Discord webhook URL."""
    r = requests.post(
        webhook_url,
        json={"content": content, "username": username},
        timeout=10,
    )
    r.raise_for_status()
    return {"status": "sent"}
