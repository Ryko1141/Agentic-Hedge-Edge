"""
Hedge Edge — Discord Music Bot Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creates a 🎵・Music Lounge voice channel and posts setup instructions
for inviting a music bot (Jockie Music / Hydra).

Usage:
    python _discord_music_bot.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if not TOKEN or not GUILD_ID:
    print("ERROR: DISCORD_BOT_TOKEN and DISCORD_GUILD_ID must be set in .env")
    sys.exit(1)

HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
API = "https://discord.com/api/v10"

# ── Known IDs from channel audit ──
VOICE_CATEGORY_ID = "1473694771594793022"   # 🎙️ ━━ VOICE ━━
BOT_COMMANDS_CH   = "1473694819850129459"   # 🤖・bot-commands

# ═══════════════════════════════════════════════════════════
# 1. Create 🎵・Music Lounge voice channel
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("STEP 1: Creating 🎵・Music Lounge voice channel")
print("=" * 60)

# Check if it already exists
channels = requests.get(
    f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, timeout=10
).json()

music_channel = None
for ch in channels:
    if ch.get("name") == "🎵・Music Lounge" and ch.get("type") == 2:
        music_channel = ch
        print(f"  ✓ Channel already exists: #{ch['name']} (ID: {ch['id']})")
        break

if not music_channel:
    payload = {
        "name": "🎵・Music Lounge",
        "type": 2,  # Voice channel
        "parent_id": VOICE_CATEGORY_ID,
        "position": 4,  # After AMA Stage
        "bitrate": 96000,  # 96kbps — good for music
        "user_limit": 0,  # Unlimited
    }
    r = requests.post(
        f"{API}/guilds/{GUILD_ID}/channels",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )
    if r.status_code in (200, 201):
        music_channel = r.json()
        print(f"  ✓ Created: #{music_channel['name']} (ID: {music_channel['id']})")
    else:
        print(f"  ✗ Failed ({r.status_code}): {r.text}")
        sys.exit(1)

MUSIC_CHANNEL_ID = music_channel["id"]

# ═══════════════════════════════════════════════════════════
# 2. Post bot invite links & instructions to #bot-commands
# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print("STEP 2: Posting music bot setup instructions")
print("=" * 60)

# Jockie Music invite (most reliable free music bot as of 2026)
JOCKIE_INVITE = "https://discord.com/oauth2/authorize?client_id=411916947773587456&permissions=36793344&scope=bot%20applications.commands"

# Hydra invite (backup option)
HYDRA_INVITE = "https://discord.com/oauth2/authorize?client_id=547905866255433758&permissions=36793344&scope=bot%20applications.commands"

embed = {
    "title": "🎵 Music Bot Setup — Hedge Edge",
    "description": (
        "Follow the steps below to add a music bot to the server.\n\n"
        f"A dedicated voice channel **<#{MUSIC_CHANNEL_ID}>** has been created for music sessions."
    ),
    "color": 0x00D4AA,  # Hedge Edge brand green
    "fields": [
        {
            "name": "🥇 Option 1: Jockie Music (Recommended)",
            "value": (
                "The most reliable free music bot. Supports YouTube, Spotify, SoundCloud, and more.\n"
                f"**[Click to invite Jockie Music]({JOCKIE_INVITE})**\n\n"
                "**Commands:**\n"
                "`m!play <song/URL>` — Play a song\n"
                "`m!skip` — Skip current track\n"
                "`m!queue` — View queue\n"
                "`m!pause` / `m!resume` — Pause/resume\n"
                "`m!volume <1-100>` — Set volume\n"
                "`m!nowplaying` — Show current track"
            ),
            "inline": False,
        },
        {
            "name": "🥈 Option 2: Hydra",
            "value": (
                "Another solid choice with premium features and a web dashboard.\n"
                f"**[Click to invite Hydra]({HYDRA_INVITE})**\n\n"
                "**Commands:**\n"
                "`.play <song/URL>` — Play a song\n"
                "`.skip` — Skip current track\n"
                "`.queue` — View queue\n"
                "`.pause` / `.resume` — Pause/resume\n"
                "`.volume <1-100>` — Set volume"
            ),
            "inline": False,
        },
        {
            "name": "📋 Setup Steps (Admin Only)",
            "value": (
                "1. Click one of the invite links above\n"
                "2. Select **Hedge Edge** as the server\n"
                "3. Grant the requested permissions\n"
                "4. Done! The bot will appear in the member list\n\n"
                f"5. Join **<#{MUSIC_CHANNEL_ID}>** and use the play command"
            ),
            "inline": False,
        },
        {
            "name": "💡 Tips",
            "value": (
                "• You can use Spotify links — the bot will search YouTube for matching tracks\n"
                "• Use `m!247` (Jockie) to keep the bot in the voice channel 24/7\n"
                "• Create playlists with `m!playlist create <name>`\n"
                "• The bot must have permission to **Connect** and **Speak** in voice channels"
            ),
            "inline": False,
        },
    ],
    "footer": {
        "text": "Hedge Edge Discord • Music Bot Setup"
    },
}

r = requests.post(
    f"{API}/channels/{BOT_COMMANDS_CH}/messages",
    headers=HEADERS,
    json={"embeds": [embed]},
    timeout=10,
)
if r.status_code == 200:
    print(f"  ✓ Instructions posted to #bot-commands")
else:
    print(f"  ✗ Failed to post ({r.status_code}): {r.text}")

# ═══════════════════════════════════════════════════════════
# 3. Post a welcome message in general-chat about music
# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print("STEP 3: Announcing music channel in general-chat")
print("=" * 60)

GENERAL_CHAT = "1473694581676835058"  # 💬・general-chat

announcement = (
    "🎵 **New: Music Lounge is here!**\n\n"
    f"Drop into <#{MUSIC_CHANNEL_ID}> to chill with music while you trade. "
    "Once an admin invites the music bot (instructions in <#1473694819850129459>), "
    "just join the voice channel and use `m!play <song>` to queue tracks.\n\n"
    "Perfect for those long trading sessions. 🎧📈"
)

r = requests.post(
    f"{API}/channels/{GENERAL_CHAT}/messages",
    headers=HEADERS,
    json={"content": announcement},
    timeout=10,
)
if r.status_code == 200:
    print(f"  ✓ Announcement posted to #general-chat")
else:
    print(f"  ✗ Failed ({r.status_code}): {r.text}")

# ═══════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print("DONE — Music Bot Setup Summary")
print("=" * 60)
print(f"  🎵 Music Lounge channel: {MUSIC_CHANNEL_ID}")
print(f"  📋 Instructions posted to: #bot-commands")
print(f"  📢 Announcement posted to: #general-chat")
print()
print("  NEXT STEPS (Admin must do manually):")
print(f"    1. Open one of the invite links from #bot-commands")
print(f"    2. Select Hedge Edge server and authorize")
print(f"    3. Join 🎵・Music Lounge and test with: m!play lofi beats")
