"""
Complete Discord server setup:
1. Update server settings (verification, notifications, content filter, system/rules channels)
2. Delete old roles, create new branded role hierarchy
3. Set channel permission overrides (premium-only, staff-only, verified-only)
4. Enable Discord Onboarding with data-collection questions
5. Configure Welcome Screen
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
API = "https://discord.com/api/v10"


def api_get(path):
    r = requests.get(f"{API}{path}", headers=HEADERS, timeout=15)
    return r.json()


def api_patch(path, data):
    for attempt in range(4):
        r = requests.patch(f"{API}{path}", headers=HEADERS, json=data, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 5)
            print(f"    ⏳ Rate limited, waiting {wait}s...")
            time.sleep(wait + 0.5)
            continue
        return r.status_code, r.json()
    return r.status_code, r.json()


def api_post(path, data):
    for attempt in range(4):
        r = requests.post(f"{API}{path}", headers=HEADERS, json=data, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 5)
            print(f"    ⏳ Rate limited, waiting {wait}s...")
            time.sleep(wait + 0.5)
            continue
        return r.status_code, r.json()
    return r.status_code, r.json()


def api_delete(path):
    for attempt in range(4):
        r = requests.delete(f"{API}{path}", headers=HEADERS, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 5)
            time.sleep(wait + 0.5)
            continue
        return r.status_code
    return r.status_code


def api_put(path, data=None):
    for attempt in range(4):
        r = requests.put(f"{API}{path}", headers=HEADERS, json=data or {}, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 5)
            time.sleep(wait + 0.5)
            continue
        return r.status_code, r.json() if r.text else {}
    return r.status_code, {}


# ─── Get channel IDs for reference ────────────────────────────────

channels = api_get(f"/guilds/{GUILD_ID}/channels")
ch_by_name = {}
for ch in channels:
    name = ch.get("name", "")
    clean = name.split("\u30fb")[-1] if "\u30fb" in name else name
    ch_by_name[clean] = ch

def ch_id(name):
    c = ch_by_name.get(name)
    return c["id"] if c else None


# ═══════════════════════════════════════════════════════════════════
# STEP 1: SERVER SETTINGS
# ═══════════════════════════════════════════════════════════════════

print("=" * 60)
print("STEP 1: Updating server settings")
print("=" * 60)

welcome_id = ch_id("welcome")
rules_id = ch_id("rules")
announcements_id = ch_id("announcements")

settings_payload = {
    "verification_level": 2,                # Medium (must be registered 5+ min)
    "default_message_notifications": 1,     # Mentions only
    "explicit_content_filter": 2,           # Scan all members
    "system_channel_id": welcome_id,        # System messages go to #welcome
    # Suppress join notifications and boost msgs in system channel (bit flags)
    # 1 = suppress join, 2 = suppress boost, 4 = suppress tips, 8 = suppress join sticker
    "system_channel_flags": 4 + 8,          # Keep join + boost, suppress tips + stickers
}

if rules_id:
    settings_payload["rules_channel_id"] = rules_id
if announcements_id:
    settings_payload["public_updates_channel_id"] = announcements_id

status, resp = api_patch(f"/guilds/{GUILD_ID}", settings_payload)
if status == 200:
    print(f"  ✅ Verification level → Medium")
    print(f"  ✅ Notifications → Mentions only")
    print(f"  ✅ Content filter → Scan all members")
    print(f"  ✅ System channel → #{ch_by_name.get('welcome', {}).get('name', '?')}")
    print(f"  ✅ Rules channel → #{ch_by_name.get('rules', {}).get('name', '?')}")
    print(f"  ✅ Updates channel → #{ch_by_name.get('announcements', {}).get('name', '?')}")
else:
    print(f"  ❌ Failed: {resp.get('message', resp)}")


# ═══════════════════════════════════════════════════════════════════
# STEP 2: CREATE NEW ROLE HIERARCHY
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("STEP 2: Setting up role hierarchy")
print("=" * 60)

# Get current roles
guild = api_get(f"/guilds/{GUILD_ID}")
existing_roles = {r["name"]: r for r in guild.get("roles", [])}

# Roles to delete (old ones we don't need)
DELETE_ROLES = ["Premium", "Member", "Hedge Edge Team member"]
for role_name in DELETE_ROLES:
    role = existing_roles.get(role_name)
    if role:
        role_id = role["id"]
        if role.get("managed"):
            print(f"  ⚠️  '{role_name}' is bot-managed, skipping delete")
            continue
        status = api_delete(f"/guilds/{GUILD_ID}/roles/{role_id}")
        sym = "✅" if status == 204 else "❌"
        print(f"  {sym} Deleted old role: {role_name} ({status})")
        time.sleep(0.8)

# Permission bit constants
ADMINISTRATOR = 0x8
MANAGE_GUILD = 0x20
MANAGE_CHANNELS = 0x10
MANAGE_ROLES = 0x10000000
MANAGE_MESSAGES = 0x2000
KICK_MEMBERS = 0x2
BAN_MEMBERS = 0x4
VIEW_CHANNEL = 0x400
SEND_MESSAGES = 0x800
SEND_TTS = 0x1000
EMBED_LINKS = 0x4000
ATTACH_FILES = 0x8000
READ_HISTORY = 0x10000
ADD_REACTIONS = 0x40
USE_EXTERNAL_EMOJIS = 0x40000
CONNECT = 0x100000
SPEAK = 0x200000
MENTION_EVERYONE = 0x20000
CHANGE_NICKNAME = 0x4000000
CREATE_INVITE = 0x1
USE_EXTERNAL_STICKERS = 0x2000000000
USE_APP_COMMANDS = 0x80000000
SEND_MESSAGES_IN_THREADS = 0x4000000000
CREATE_PUBLIC_THREADS = 0x800000000

# Standard member perms
MEMBER_PERMS = (
    VIEW_CHANNEL | SEND_MESSAGES | EMBED_LINKS | ATTACH_FILES |
    READ_HISTORY | ADD_REACTIONS | USE_EXTERNAL_EMOJIS | CONNECT |
    SPEAK | CHANGE_NICKNAME | CREATE_INVITE | USE_APP_COMMANDS |
    SEND_MESSAGES_IN_THREADS | CREATE_PUBLIC_THREADS | USE_EXTERNAL_STICKERS
)

# Moderator perms
MOD_PERMS = MEMBER_PERMS | MANAGE_MESSAGES | KICK_MEMBERS | MENTION_EVERYONE

# New roles to create (in order of hierarchy, highest first)
# We create from bottom up, then reorder
NEW_ROLES = [
    # (name, color_hex, permissions, hoist, mentionable)
    ("━━ STAFF ━━",           0x2F3136,  0, False, False),      # divider
    ("🛡️ Admin",              0x00C853,  ADMINISTRATOR, True, False),
    ("⚔️ Moderator",          0x2ECC71,  MOD_PERMS, True, True),

    ("━━ TIERS ━━",           0x2F3136,  0, False, False),      # divider
    ("👑 Unlimited",           0x9B59B6,  MEMBER_PERMS, True, True),
    ("💎 Multi-Challenge",     0x3498DB,  MEMBER_PERMS, True, True),
    ("🛡️ Challenge Shield",   0x2ECC71,  MEMBER_PERMS, True, True),

    ("━━ COMMUNITY ━━",      0x2F3136,  0, False, False),      # divider
    ("🧪 Beta Tester",        0xE91E63,  MEMBER_PERMS, True, True),
    ("🎥 Content Creator",    0xFF9800,  MEMBER_PERMS, True, True),
    ("⭐ OG Member",           0xFFD700,  MEMBER_PERMS, True, True),

    ("━━ TRADING ━━",        0x2F3136,  0, False, False),      # divider
    ("📈 Forex Trader",       0x1ABC9C,  MEMBER_PERMS, False, False),
    ("📊 Indices Trader",     0x3498DB,  MEMBER_PERMS, False, False),
    ("🪙 Crypto Trader",      0xF1C40F,  MEMBER_PERMS, False, False),
    ("⚡ Futures Trader",      0xE74C3C,  MEMBER_PERMS, False, False),
    ("🏦 Prop Firm Trader",   0x2ECC71,  MEMBER_PERMS, False, False),

    ("━━━━━━━━━━━━",         0x2F3136,  0, False, False),      # divider
    ("✅ Verified",            0x99AAB5,  MEMBER_PERMS, False, False),
    ("👀 Unverified",          0x95A5A6,  0, False, False),     # no perms until verified
]

created_roles = {}

for name, color, perms, hoist, mentionable in reversed(NEW_ROLES):
    # Skip if already exists
    if name in existing_roles:
        print(f"  ⏭️  '{name}' already exists, skipping")
        created_roles[name] = existing_roles[name]["id"]
        continue

    payload = {
        "name": name,
        "color": color,
        "permissions": str(perms),
        "hoist": hoist,
        "mentionable": mentionable,
    }
    status, resp = api_post(f"/guilds/{GUILD_ID}/roles", payload)
    if status == 200:
        role_id = resp.get("id")
        created_roles[name] = role_id
        print(f"  ✅ Created: {name} (ID: {role_id})")
    else:
        print(f"  ❌ Failed: {name} — {resp.get('message', resp)}")
    time.sleep(0.8)

# Reorder roles (highest position = most privilege)
# Get fresh roles
time.sleep(1)
guild = api_get(f"/guilds/{GUILD_ID}")
all_roles = {r["name"]: r for r in guild.get("roles", [])}

# Define desired order (highest first)
ROLE_ORDER = [
    "Hedge Edge team",
    "━━ STAFF ━━",
    "🛡️ Admin",
    "⚔️ Moderator",
    "Spotix",                # keep existing bot roles
    "Easy Auth",
    "Agentic Hedge Edge",
    "━━ TIERS ━━",
    "👑 Unlimited",
    "💎 Multi-Challenge",
    "🛡️ Challenge Shield",
    "━━ COMMUNITY ━━",
    "🧪 Beta Tester",
    "🎥 Content Creator",
    "⭐ OG Member",
    "━━ TRADING ━━",
    "📈 Forex Trader",
    "📊 Indices Trader",
    "🪙 Crypto Trader",
    "⚡ Futures Trader",
    "🏦 Prop Firm Trader",
    "━━━━━━━━━━━━",
    "✅ Verified",
    "👀 Unverified",
]

# Build position array (position 1 = lowest non-@everyone)
positions = []
pos = len(ROLE_ORDER)
for role_name in ROLE_ORDER:
    role = all_roles.get(role_name)
    if role and not role.get("managed"):  # can't reorder managed (bot) roles
        positions.append({"id": role["id"], "position": pos})
    pos -= 1

if positions:
    status, resp = api_patch(f"/guilds/{GUILD_ID}/roles", positions)
    if status == 200:
        print(f"  ✅ Role hierarchy reordered ({len(positions)} roles)")
    else:
        print(f"  ⚠️  Role reorder: {resp.get('message', str(resp)[:200])}")

time.sleep(1)

# ═══════════════════════════════════════════════════════════════════
# STEP 3: SET @EVERYONE RESTRICTIONS + CHANNEL PERMISSION OVERRIDES
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("STEP 3: Setting channel permissions")
print("=" * 60)

# Refresh roles
guild = api_get(f"/guilds/{GUILD_ID}")
all_roles = {r["name"]: r for r in guild.get("roles", [])}
everyone_id = GUILD_ID  # @everyone role ID = guild ID

# Get role IDs
verified_id = all_roles.get("✅ Verified", {}).get("id")
unverified_id = all_roles.get("👀 Unverified", {}).get("id")
premium_ids = [
    all_roles.get("🛡️ Challenge Shield", {}).get("id"),
    all_roles.get("💎 Multi-Challenge", {}).get("id"),
    all_roles.get("👑 Unlimited", {}).get("id"),
]
premium_ids = [p for p in premium_ids if p]
admin_id = all_roles.get("🛡️ Admin", {}).get("id")
mod_id = all_roles.get("⚔️ Moderator", {}).get("id")
staff_ids = [admin_id, mod_id, all_roles.get("Hedge Edge team", {}).get("id")]
staff_ids = [s for s in staff_ids if s]

# First: Restrict @everyone — can only see welcome channels
# We'll do this at the category level

# Helper: set permission overwrite on a channel
def set_overwrite(channel_id, target_id, target_type, allow, deny):
    """target_type: 0=role, 1=member"""
    path = f"/channels/{channel_id}/permissions/{target_id}"
    data = {"allow": str(allow), "deny": str(deny), "type": target_type}
    status, _ = api_put(path, data)
    return status in (200, 204)

# Refresh channels
channels = api_get(f"/guilds/{GUILD_ID}/channels")
ch_by_name = {}
cat_by_name = {}
for ch in channels:
    name = ch.get("name", "")
    clean = name.split("\u30fb")[-1] if "\u30fb" in name else name
    if ch.get("type") == 4:
        cat_by_name[name] = ch
    else:
        ch_by_name[clean] = ch

# ── @everyone: deny send in most places, allow view for public channels only
# Strategy: 
# - @everyone can VIEW welcome channels only (rules, welcome, announcements)
# - ✅ Verified can access all public channels
# - Premium roles can access premium channels
# - Staff roles can access staff channels

# Categories to configure
CATEGORIES = {
    "🏠 ━━ WELCOME ━━":    {"everyone_view": True,  "everyone_send": False, "verified_send": True},
    "💬 ━━ COMMUNITY ━━":  {"everyone_view": False, "everyone_send": False, "verified_send": True},
    "📈 ━━ TRADING ━━":    {"everyone_view": False, "everyone_send": False, "verified_send": True},
    "🏦 ━━ PROP FIRMS ━━": {"everyone_view": False, "everyone_send": False, "verified_send": True},
    "🛡️ ━━ HEDGE EDGE ━━": {"everyone_view": False, "everyone_send": False, "verified_send": True},
    "📚 ━━ EDUCATION ━━":  {"everyone_view": False, "everyone_send": False, "verified_send": True},
    "👑 ━━ PREMIUM ━━":    {"everyone_view": False, "everyone_send": False, "verified_send": False},  # premium only
    "🎙️ ━━ VOICE ━━":     {"everyone_view": False, "everyone_send": False, "verified_send": True},
    "🔒 ━━ STAFF ━━":      {"everyone_view": False, "everyone_send": False, "verified_send": False},  # staff only
}

for cat_name, perms_config in CATEGORIES.items():
    cat = cat_by_name.get(cat_name)
    if not cat:
        print(f"  ⚠️  Category '{cat_name}' not found")
        continue

    cat_id = cat["id"]

    # @everyone overwrites
    if perms_config["everyone_view"]:
        # Allow view but deny send (for welcome area — read-only for unverified)
        if not perms_config["everyone_send"]:
            ok = set_overwrite(cat_id, everyone_id, 0, VIEW_CHANNEL | READ_HISTORY, SEND_MESSAGES)
        else:
            ok = set_overwrite(cat_id, everyone_id, 0, VIEW_CHANNEL | READ_HISTORY | SEND_MESSAGES, 0)
    else:
        # Deny view entirely
        ok = set_overwrite(cat_id, everyone_id, 0, 0, VIEW_CHANNEL)

    # ✅ Verified overwrites 
    if verified_id and perms_config["verified_send"]:
        set_overwrite(cat_id, verified_id, 0,
                      VIEW_CHANNEL | SEND_MESSAGES | READ_HISTORY | ADD_REACTIONS |
                      EMBED_LINKS | ATTACH_FILES | USE_EXTERNAL_EMOJIS |
                      SEND_MESSAGES_IN_THREADS | CREATE_PUBLIC_THREADS, 0)

    # Premium overwrites for premium category
    if cat_name == "👑 ━━ PREMIUM ━━":
        for pid in premium_ids:
            set_overwrite(cat_id, pid, 0,
                          VIEW_CHANNEL | SEND_MESSAGES | READ_HISTORY | ADD_REACTIONS |
                          EMBED_LINKS | ATTACH_FILES | USE_EXTERNAL_EMOJIS, 0)

    # Staff overwrites for staff category
    if cat_name == "🔒 ━━ STAFF ━━":
        for sid in staff_ids:
            set_overwrite(cat_id, sid, 0,
                          VIEW_CHANNEL | SEND_MESSAGES | READ_HISTORY |
                          MANAGE_MESSAGES | ADD_REACTIONS | EMBED_LINKS | ATTACH_FILES, 0)

    print(f"  ✅ {cat_name} — permissions set")
    time.sleep(0.5)

# Special: welcome channels — let @everyone view but NOT send (except #introductions)
welcome_view_only = ["welcome", "rules", "announcements", "roles"]
for ch_name in welcome_view_only:
    ch = ch_by_name.get(ch_name)
    if ch:
        set_overwrite(ch["id"], everyone_id, 0, VIEW_CHANNEL | READ_HISTORY | ADD_REACTIONS, SEND_MESSAGES)
        time.sleep(0.3)

# #introductions — verified can send, everyone can view
intro_ch = ch_by_name.get("introductions")
if intro_ch:
    set_overwrite(intro_ch["id"], everyone_id, 0, VIEW_CHANNEL | READ_HISTORY, SEND_MESSAGES)
    if verified_id:
        set_overwrite(intro_ch["id"], verified_id, 0, VIEW_CHANNEL | SEND_MESSAGES | READ_HISTORY | EMBED_LINKS, 0)

# Staff channels — allow staff + mods to always see everything
for staff_ch_name in ["staff-chat", "mod-logs", "bot-commands"]:
    ch = ch_by_name.get(staff_ch_name)
    if ch:
        for sid in staff_ids:
            set_overwrite(ch["id"], sid, 0,
                          VIEW_CHANNEL | SEND_MESSAGES | READ_HISTORY | MANAGE_MESSAGES, 0)

print(f"  ✅ Special channel overrides set")


# ═══════════════════════════════════════════════════════════════════
# STEP 4: CONFIGURE DISCORD ONBOARDING
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("STEP 4: Configuring Discord Onboarding")
print("=" * 60)

# Refresh role IDs
guild = api_get(f"/guilds/{GUILD_ID}")
all_roles = {r["name"]: r for r in guild.get("roles", [])}

def role_id(name):
    return all_roles.get(name, {}).get("id")

# Refresh channels
channels = api_get(f"/guilds/{GUILD_ID}/channels")
ch_by_name_full = {}
for ch in channels:
    name = ch.get("name", "")
    clean = name.split("\u30fb")[-1] if "\u30fb" in name else name
    ch_by_name_full[clean] = ch

def get_ch_id(name):
    return ch_by_name_full.get(name, {}).get("id")

# Default channels everyone sees on join
default_channels = [
    get_ch_id("welcome"),
    get_ch_id("rules"),
    get_ch_id("announcements"),
    get_ch_id("roles"),
    get_ch_id("introductions"),
    get_ch_id("general-chat"),
]
default_channels = [c for c in default_channels if c]

# Onboarding prompts (questions users answer)
prompts = [
    {
        "type": 0,  # MULTIPLE_CHOICE
        "title": "What do you trade?",
        "single_select": False,
        "required": True,
        "in_onboarding": True,
        "options": [
            {
                "title": "📈 Forex",
                "description": "Currencies (EUR/USD, GBP/JPY, etc.)",
                "role_ids": [role_id("📈 Forex Trader")],
                "channel_ids": [get_ch_id("market-talk")],
            },
            {
                "title": "📊 Indices",
                "description": "S&P 500, NASDAQ, DAX, etc.",
                "role_ids": [role_id("📊 Indices Trader")],
                "channel_ids": [get_ch_id("market-talk")],
            },
            {
                "title": "🪙 Crypto",
                "description": "Bitcoin, Ethereum, altcoins",
                "role_ids": [role_id("🪙 Crypto Trader")],
                "channel_ids": [get_ch_id("market-talk")],
            },
            {
                "title": "⚡ Futures",
                "description": "Futures, commodities, oil, gold",
                "role_ids": [role_id("⚡ Futures Trader")],
                "channel_ids": [get_ch_id("market-talk")],
            },
        ],
    },
    {
        "type": 0,
        "title": "Are you a prop firm trader?",
        "single_select": True,
        "required": True,
        "in_onboarding": True,
        "options": [
            {
                "title": "🏦 Yes, I'm funded or in a challenge",
                "description": "Currently trading with a prop firm",
                "role_ids": [role_id("🏦 Prop Firm Trader")],
                "channel_ids": [get_ch_id("prop-firms"), get_ch_id("challenge-updates")],
            },
            {
                "title": "🎯 Planning to start",
                "description": "Looking into prop firms but haven't started yet",
                "role_ids": [],
                "channel_ids": [get_ch_id("prop-firms"), get_ch_id("how-it-works")],
            },
            {
                "title": "📚 Just learning",
                "description": "Here to learn about prop firm trading",
                "role_ids": [],
                "channel_ids": [get_ch_id("resources"), get_ch_id("ask-questions")],
            },
        ],
    },
    {
        "type": 0,
        "title": "Have you heard of hedging for challenges?",
        "single_select": True,
        "required": True,
        "in_onboarding": True,
        "options": [
            {
                "title": "🛡️ Yes, I already hedge",
                "description": "I use hedging to protect my challenges",
                "role_ids": [],
                "channel_ids": [get_ch_id("how-it-works"), get_ch_id("setup-guide")],
            },
            {
                "title": "🤔 I've heard of it but don't fully understand",
                "description": "Curious but need more info",
                "role_ids": [],
                "channel_ids": [get_ch_id("hedge-guide"), get_ch_id("how-it-works"), get_ch_id("ask-questions")],
            },
            {
                "title": "❓ No, what is it?",
                "description": "Brand new to the concept",
                "role_ids": [],
                "channel_ids": [get_ch_id("hedge-guide"), get_ch_id("how-it-works"), get_ch_id("resources")],
            },
        ],
    },
    {
        "type": 0,
        "title": "What channels interest you?",
        "single_select": False,
        "required": False,
        "in_onboarding": True,
        "options": [
            {
                "title": "💬 Community & Chat",
                "description": "General discussion & memes",
                "role_ids": [],
                "channel_ids": [get_ch_id("general-chat"), get_ch_id("memes")],
            },
            {
                "title": "🎯 Trade Ideas & Setups",
                "description": "Analysis and trade ideas from the community",
                "role_ids": [],
                "channel_ids": [get_ch_id("trade-ideas"), get_ch_id("strategies")],
            },
            {
                "title": "🏦 Prop Firm Intel",
                "description": "Reviews, payouts, and challenge updates",
                "role_ids": [],
                "channel_ids": [get_ch_id("prop-firms"), get_ch_id("payouts"), get_ch_id("challenge-updates")],
            },
            {
                "title": "🛡️ Hedge Edge Product",
                "description": "Setup guides, features, and beta testing",
                "role_ids": [],
                "channel_ids": [get_ch_id("how-it-works"), get_ch_id("setup-guide"), get_ch_id("beta-testing")],
            },
            {
                "title": "📚 Education & Resources",
                "description": "Guides, books, and learning materials",
                "role_ids": [],
                "channel_ids": [get_ch_id("resources"), get_ch_id("hedge-guide"), get_ch_id("books")],
            },
        ],
    },
]

# Clean out None values in role_ids and channel_ids
for prompt in prompts:
    for option in prompt.get("options", []):
        option["role_ids"] = [r for r in option.get("role_ids", []) if r]
        option["channel_ids"] = [c for c in option.get("channel_ids", []) if c]
        # Emoji from title
        emoji_char = option["title"][0] if option["title"] else None
        if emoji_char:
            option["emoji"] = {"name": emoji_char}

onboarding_payload = {
    "prompts": prompts,
    "default_channel_ids": default_channels,
    "enabled": True,
    "mode": 0,  # 0 = default (onboarding + default channels), 1 = advanced
}

status, resp = api_put(f"/guilds/{GUILD_ID}/onboarding", onboarding_payload)
if status == 200:
    print(f"  ✅ Onboarding enabled with {len(prompts)} questions")
    print(f"  ✅ Default channels: {len(default_channels)}")
    for p in prompts:
        print(f"    📋 \"{p['title']}\" — {len(p['options'])} options (required={p['required']})")
else:
    print(f"  ❌ Onboarding failed ({status}): {resp.get('message', str(resp)[:300])}")
    # If Community features are required, try enabling
    if "COMMUNITY" in str(resp):
        print("  ℹ️  Trying to enable Community features first...")
        # Enable community by setting rules + public updates channels
        comm_status, comm_resp = api_patch(f"/guilds/{GUILD_ID}", {
            "features": ["COMMUNITY"],
            "rules_channel_id": rules_id,
            "public_updates_channel_id": announcements_id,
        })
        print(f"  Community enable: {comm_status} — {comm_resp.get('message', 'OK')}")
        if comm_status == 200:
            # Retry onboarding
            time.sleep(1)
            status, resp = api_put(f"/guilds/{GUILD_ID}/onboarding", onboarding_payload)
            if status == 200:
                print(f"  ✅ Onboarding enabled (second attempt)")
            else:
                print(f"  ❌ Onboarding still failed: {resp.get('message', str(resp)[:200])}")


# ═══════════════════════════════════════════════════════════════════
# STEP 5: WELCOME SCREEN
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("STEP 5: Configuring Welcome Screen")
print("=" * 60)

welcome_screen_payload = {
    "enabled": True,
    "description": "Welcome to Hedge Edge — The #1 community for prop firm traders who hedge smart. Protect your challenges, recover your fees.",
    "welcome_channels": [
        {
            "channel_id": get_ch_id("rules"),
            "description": "Read the server rules before posting",
            "emoji_name": "📜",
        },
        {
            "channel_id": get_ch_id("introductions"),
            "description": "Introduce yourself to the community",
            "emoji_name": "👋",
        },
        {
            "channel_id": get_ch_id("general-chat"),
            "description": "Join the conversation",
            "emoji_name": "💬",
        },
        {
            "channel_id": get_ch_id("how-it-works"),
            "description": "Learn how Hedge Edge protects your challenges",
            "emoji_name": "🛡️",
        },
        {
            "channel_id": get_ch_id("hedge-guide"),
            "description": "Download the free hedging guide",
            "emoji_name": "📖",
        },
    ],
}

# Filter out entries with None channel_id
welcome_screen_payload["welcome_channels"] = [
    wc for wc in welcome_screen_payload["welcome_channels"] if wc.get("channel_id")
]

status, resp = api_patch(f"/guilds/{GUILD_ID}/welcome-screen", welcome_screen_payload)
if status == 200:
    print(f"  ✅ Welcome screen configured with {len(welcome_screen_payload['welcome_channels'])} channels")
else:
    print(f"  ❌ Welcome screen failed ({status}): {resp.get('message', str(resp)[:300])}")


# ═══════════════════════════════════════════════════════════════════
# STEP 6: SUMMARY
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("SUMMARY")
print("=" * 60)

# Final role count
guild = api_get(f"/guilds/{GUILD_ID}")
role_count = len(guild.get("roles", []))
print(f"Roles: {role_count}")
print(f"Verification: Medium (must register 5+ min)")
print(f"Content filter: Scan all members")
print(f"Notifications: Mentions only")

for r in sorted(guild.get("roles", []), key=lambda x: x.get("position", 0), reverse=True):
    if r.get("name") == "@everyone":
        continue
    managed = " [BOT]" if r.get("managed") else ""
    print(f"  [{r.get('position'):2d}] {r.get('name')}{managed}")

# Output important role IDs for .env
print(f"\n--- Role IDs ---")
important_roles = [
    "✅ Verified", "👀 Unverified", "🛡️ Admin", "⚔️ Moderator",
    "🛡️ Challenge Shield", "💎 Multi-Challenge", "👑 Unlimited",
    "🧪 Beta Tester", "🏦 Prop Firm Trader",
]
for name in important_roles:
    r = all_roles.get(name) or {rr["name"]: rr for rr in guild.get("roles", [])}.get(name)
    if r:
        print(f"  {name}: {r.get('id', r)}")
