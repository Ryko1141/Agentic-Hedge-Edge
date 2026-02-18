"""Fetch Discord guild info, channels, and invites."""
import requests, os
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("DISCORD_BOT_TOKEN")
headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

# Get bot's guilds
r = requests.get("https://discord.com/api/v10/users/@me/guilds", headers=headers, timeout=10)
guilds = r.json()
print("=== BOT GUILDS ===")
for g in guilds:
    print(f"  ID: {g['id']}  Name: {g['name']}")

if not guilds:
    print("No guilds found!")
    exit()

gid = guilds[0]["id"]

# Get channels
r2 = requests.get(f"https://discord.com/api/v10/guilds/{gid}/channels", headers=headers, timeout=10)
channels = r2.json()
print(f"\n=== CHANNELS in {guilds[0]['name']} ===")
for c in channels:
    print(f"  ID: {c['id']}  Type: {c['type']}  Name: {c.get('name', '?')}")

# Get existing invites
r3 = requests.get(f"https://discord.com/api/v10/guilds/{gid}/invites", headers=headers, timeout=10)
invites = r3.json()
print(f"\n=== EXISTING INVITES ===")
if isinstance(invites, list) and invites:
    for inv in invites:
        print(f"  https://discord.gg/{inv['code']}  (uses: {inv.get('uses',0)}, max_uses: {inv.get('max_uses',0)})")
elif isinstance(invites, list):
    print("  No invites exist yet.")
else:
    print(f"  Error: {invites}")

# Get vanity URL if available
r4 = requests.get(f"https://discord.com/api/v10/guilds/{gid}/vanity-url", headers=headers, timeout=10)
print(f"\n=== VANITY URL ===")
if r4.status_code == 200:
    data = r4.json()
    print(f"  https://discord.gg/{data.get('code', 'N/A')}")
else:
    print(f"  Not available (status {r4.status_code})")
