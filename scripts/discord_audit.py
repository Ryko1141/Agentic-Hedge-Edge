"""
Audit current Discord server settings, roles, and permissions.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
API = "https://discord.com/api/v10"

# ─── Guild info ───
g = requests.get(f"{API}/guilds/{GUILD_ID}?with_counts=true", headers=HEADERS, timeout=10).json()
print("=" * 60)
print("SERVER SETTINGS")
print("=" * 60)
print(f"Name: {g.get('name')}")
print(f"Verification Level: {g.get('verification_level')} (0=none,1=low,2=medium,3=high,4=highest)")
print(f"Default Notifications: {g.get('default_message_notifications')} (0=all,1=mentions)")
print(f"Explicit Content Filter: {g.get('explicit_content_filter')} (0=off,1=no-role,2=all)")
print(f"MFA Level: {g.get('mfa_level')} (0=none,1=elevated)")
print(f"NSFW Level: {g.get('nsfw_level')}")
print(f"Features: {g.get('features', [])}")
print(f"System Channel: {g.get('system_channel_id')}")
print(f"System Channel Flags: {g.get('system_channel_flags')}")
print(f"Rules Channel: {g.get('rules_channel_id')}")
print(f"Public Updates Channel: {g.get('public_updates_channel_id')}")
print(f"Premium Tier: {g.get('premium_tier')}")
print(f"Preferred Locale: {g.get('preferred_locale')}")
print(f"Approximate Members: {g.get('approximate_member_count')}")
print(f"Approximate Presence: {g.get('approximate_presence_count')}")

# ─── Roles ───
print(f"\n{'=' * 60}")
print("ROLES")
print("=" * 60)
roles = sorted(g.get("roles", []), key=lambda r: r.get("position", 0), reverse=True)
for r in roles:
    perms = int(r.get("permissions", "0"))
    admin = bool(perms & 0x8)
    manage_guild = bool(perms & 0x20)
    manage_channels = bool(perms & 0x10)
    manage_roles = bool(perms & 0x10000000)
    kick = bool(perms & 0x2)
    ban = bool(perms & 0x4)
    mention = bool(perms & 0x20000)
    send = bool(perms & 0x800)
    read = bool(perms & 0x400)
    color_hex = f"#{r.get('color', 0):06X}" if r.get("color") else "none"
    flags = []
    if admin: flags.append("ADMIN")
    if manage_guild: flags.append("MANAGE_GUILD")
    if manage_channels: flags.append("MANAGE_CHANNELS")
    if manage_roles: flags.append("MANAGE_ROLES")
    if kick: flags.append("KICK")
    if ban: flags.append("BAN")
    if not send: flags.append("NO_SEND")
    if not read: flags.append("NO_READ")
    if r.get("managed"): flags.append("BOT_MANAGED")
    if r.get("hoist"): flags.append("HOISTED")
    if r.get("mentionable"): flags.append("MENTIONABLE")
    flag_str = " | ".join(flags) if flags else "standard"
    print(f"  [{r.get('position'):2d}] {r.get('name'):30s} ID={r.get('id'):20s} color={color_hex:8s} [{flag_str}]")

# ─── Channels & permission overrides ───
print(f"\n{'=' * 60}")
print("CHANNEL PERMISSION OVERRIDES")
print("=" * 60)
channels = requests.get(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, timeout=10).json()
role_map = {r.get("id"): r.get("name") for r in roles}

for ch in sorted(channels, key=lambda c: c.get("position", 0)):
    overwrites = ch.get("permission_overwrites", [])
    if overwrites:
        name = ch.get("name", "?")
        ch_type = {0: "text", 2: "voice", 4: "cat", 5: "announce", 15: "forum"}.get(ch.get("type"), "?")
        print(f"\n  #{name} ({ch_type})")
        for ow in overwrites:
            target = role_map.get(ow.get("id"), ow.get("id"))
            allow = int(ow.get("allow", "0"))
            deny = int(ow.get("deny", "0"))
            ow_type = "role" if ow.get("type") == 0 else "member"
            print(f"    {ow_type} '{target}': allow={allow:#x} deny={deny:#x}")

# ─── Check for onboarding ───
print(f"\n{'=' * 60}")
print("ONBOARDING STATUS")
print("=" * 60)
ob = requests.get(f"{API}/guilds/{GUILD_ID}/onboarding", headers=HEADERS, timeout=10)
print(f"Status: {ob.status_code}")
if ob.status_code == 200:
    data = ob.json()
    print(f"Enabled: {data.get('enabled')}")
    print(f"Mode: {data.get('mode')}")
    print(f"Prompts: {len(data.get('prompts', []))}")
    for p in data.get("prompts", []):
        print(f"  - {p.get('title')} (required={p.get('required')}, single_select={p.get('single_select')})")
        for o in p.get("options", []):
            print(f"      [{o.get('title')}] roles={o.get('role_ids')} channels={o.get('channel_ids')}")
    print(f"Default channels: {data.get('default_channel_ids', [])}")
else:
    print(f"Body: {ob.text[:300]}")

# ─── Member Welcome Screen ───
print(f"\n{'=' * 60}")
print("WELCOME SCREEN")
print("=" * 60)
ws = requests.get(f"{API}/guilds/{GUILD_ID}/welcome-screen", headers=HEADERS, timeout=10)
print(f"Status: {ws.status_code}")
if ws.status_code == 200:
    data = ws.json()
    print(f"Description: {data.get('description')}")
    for wc in data.get("welcome_channels", []):
        print(f"  - {wc.get('emoji_name','')} {wc.get('description')} → channel {wc.get('channel_id')}")
else:
    print(f"Body: {ws.text[:300]}")
