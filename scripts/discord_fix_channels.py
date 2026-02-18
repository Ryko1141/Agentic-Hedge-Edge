"""Fix the 2 failed announcement channels by creating them as text channels, then update .env."""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
API = "https://discord.com/api/v10"

# Find the WELCOME category ID
channels = requests.get(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, timeout=15).json()

welcome_cat_id = None
for ch in channels:
    if ch.get("type") == 4 and "WELCOME" in ch.get("name", ""):
        welcome_cat_id = ch.get("id")
        break

print(f"WELCOME category ID: {welcome_cat_id}")

# Check if welcome and announcements already exist (they shouldn't since they failed)
existing_names = {ch.get("name"): ch.get("id") for ch in channels}
print(f"Existing channel names: welcome={existing_names.get('welcome')}, announcements={existing_names.get('announcements')}")

created = {}

# Create #welcome as text channel
if "welcome" not in existing_names:
    r = requests.post(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, json={
        "name": "welcome",
        "type": 0,  # text
        "parent_id": welcome_cat_id,
        "topic": "Welcome to Hedge Edge! Read the rules and get started.",
        "position": 0,  # first in category
    }, timeout=15)
    data = r.json()
    created["welcome"] = data.get("id")
    print(f"Created #welcome: {r.status_code} — ID: {data.get('id')}")
    time.sleep(1)

# Create #announcements as text channel
if "announcements" not in existing_names:
    r = requests.post(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, json={
        "name": "announcements",
        "type": 0,  # text
        "parent_id": welcome_cat_id,
        "topic": "Official Hedge Edge announcements and updates.",
        "position": 2,  # after rules
    }, timeout=15)
    data = r.json()
    created["announcements"] = data.get("id")
    print(f"Created #announcements: {r.status_code} — ID: {data.get('id')}")

# Print all key IDs for .env update
print("\n--- Updated .env values ---")
key_channels = {
    "DISCORD_WELCOME_CHANNEL_ID": created.get("welcome") or existing_names.get("welcome"),
    "DISCORD_ANNOUNCEMENTS_CHANNEL_ID": created.get("announcements") or existing_names.get("announcements"),
    "DISCORD_GENERAL_CHANNEL_ID": existing_names.get("general-chat"),
    "DISCORD_RULES_CHANNEL_ID": existing_names.get("rules"),
    "DISCORD_MARKET_CHANNEL_ID": existing_names.get("market-discussion"),
    "DISCORD_PREMIUM_CHANNEL_ID": existing_names.get("premium-chat"),
    "DISCORD_STAFF_CHANNEL_ID": existing_names.get("staff-chat"),
    "DISCORD_BOT_CHANNEL_ID": existing_names.get("bot-commands"),
    "DISCORD_INTRODUCTIONS_CHANNEL_ID": existing_names.get("introduce-yourself"),
}

for key, val in key_channels.items():
    print(f"{key}={val}")

# Final count
final = requests.get(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, timeout=15).json()
cats = sum(1 for c in final if c.get("type") == 4)
text = sum(1 for c in final if c.get("type") in (0, 5, 15))
voice = sum(1 for c in final if c.get("type") == 2)
print(f"\nFinal: {cats} categories, {text} text/forum, {voice} voice = {len(final)} total")
