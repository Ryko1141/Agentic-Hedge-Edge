"""Test Community Manager agent's Discord capabilities end-to-end."""
import requests, os, json, time
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("DISCORD_BOT_TOKEN")
guild_id = os.getenv("DISCORD_GUILD_ID", "1101229154386579468")
headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
BASE = "https://discord.com/api/v10"

results = []

def test(name, func):
    try:
        result = func()
        results.append((name, "PASS", result))
        print(f"  PASS  {name}: {result}")
    except Exception as e:
        results.append((name, "FAIL", str(e)))
        print(f"  FAIL  {name}: {e}")

# ── Test 1: Get guild info ──
def t_guild_info():
    r = requests.get(f"{BASE}/guilds/{guild_id}", headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    return f"{data['name']} — {data['member_count']} members"

# ── Test 2: List channels ──
def t_channels():
    r = requests.get(f"{BASE}/guilds/{guild_id}/channels", headers=headers, timeout=10)
    r.raise_for_status()
    channels = r.json()
    text_channels = [c for c in channels if c["type"] == 0]
    return f"{len(text_channels)} text channels, {len(channels)} total"

# ── Test 3: Get guild roles ──
def t_roles():
    r = requests.get(f"{BASE}/guilds/{guild_id}/roles", headers=headers, timeout=10)
    r.raise_for_status()
    roles = r.json()
    role_names = [role["name"] for role in roles if role["name"] != "@everyone"]
    return f"{len(roles)} roles: {', '.join(role_names[:10])}"

# ── Test 4: Send a message to general-chat ──
def t_send_message():
    channel_id = "1423835712532250795"  # general-chat
    r = requests.post(
        f"{BASE}/channels/{channel_id}/messages",
        headers=headers,
        json={"content": "**Hedge Edge Bot** is online and operational. Community Manager agent connected successfully."},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return f"Message sent (ID: {data['id']})"

# ── Test 5: Send an embed to announcements ──
def t_send_embed():
    channel_id = "1432414783486824608"  # announcements
    embed = {
        "title": "Community Manager Agent — Connected",
        "description": "The Hedge Edge Community Manager bot is now live and monitoring this server.\n\n"
                       "**Capabilities:**\n"
                       "• Welcome new members automatically\n"
                       "• Collect and categorize feedback\n"
                       "• Triage support tickets\n"
                       "• Post announcements and updates\n"
                       "• Track community engagement metrics",
        "color": 0x00FF41,  # Hedge Edge green
        "footer": {"text": "Hedge Edge Community Manager Agent"},
    }
    r = requests.post(
        f"{BASE}/channels/{channel_id}/messages",
        headers=headers,
        json={"embeds": [embed]},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return f"Embed sent to #announcements (ID: {data['id']})"

# ── Test 6: Read recent messages from welcome channel ──
def t_read_messages():
    channel_id = "1101261017528422450"  # welcome
    r = requests.get(
        f"{BASE}/channels/{channel_id}/messages",
        headers=headers,
        params={"limit": 5},
        timeout=10,
    )
    r.raise_for_status()
    msgs = r.json()
    return f"{len(msgs)} recent messages in #welcome"

# ── Test 7: Create invite ──
def t_create_invite():
    channel_id = "1101229154386579471"  # general
    r = requests.post(
        f"{BASE}/channels/{channel_id}/invites",
        headers=headers,
        json={"max_age": 86400, "max_uses": 10},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return f"https://discord.gg/{data['code']} (24h, 10 uses)"

# ── Run all tests ──
print("=" * 60)
print("  Community Manager Agent — Discord Integration Test")
print("=" * 60)
print()

test("Guild Info", t_guild_info)
test("List Channels", t_channels)
test("Get Roles", t_roles)
test("Send Message", t_send_message)
test("Send Embed", t_send_embed)
test("Read Messages", t_read_messages)
test("Create Invite", t_create_invite)

# ── Summary ──
print()
print("=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
total = len(results)
print(f"  Results: {passed}/{total} tests passed")
print("=" * 60)
