"""
Restructure the Hedge Edge Discord server with proper categories and channels.
Deletes old channels, creates categories, and sets up a professional trading community layout.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
API = f"https://discord.com/api/v10"


def api_get(path):
    r = requests.get(f"{API}{path}", headers=HEADERS, timeout=15)
    return r.json()


def api_post(path, data):
    for attempt in range(3):
        r = requests.post(f"{API}{path}", headers=HEADERS, json=data, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 3)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait + 0.5)
            continue
        return r.status_code, r.json()
    return r.status_code, r.json()


def api_delete(path):
    for attempt in range(3):
        r = requests.delete(f"{API}{path}", headers=HEADERS, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 3)
            time.sleep(wait + 0.5)
            continue
        return r.status_code
    return r.status_code


def api_patch(path, data):
    for attempt in range(3):
        r = requests.patch(f"{API}{path}", headers=HEADERS, json=data, timeout=15)
        if r.status_code == 429:
            wait = r.json().get("retry_after", 3)
            time.sleep(wait + 0.5)
            continue
        return r.status_code, r.json()
    return r.status_code, r.json()


# ─── Step 1: Audit existing channels ──────────────────────────────

print("=" * 60)
print("STEP 1: Auditing existing channels")
print("=" * 60)

channels = api_get(f"/guilds/{GUILD_ID}/channels")
print(f"Found {len(channels)} existing channels:\n")

categories = {}
orphans = []
for ch in sorted(channels, key=lambda c: c.get("position", 0)):
    ch_type = ch.get("type", -1)
    name = ch.get("name", "?")
    ch_id = ch.get("id")
    parent = ch.get("parent_id")
    # type 4 = category, 0 = text, 2 = voice, 5 = announcement, 13 = stage, 15 = forum
    type_names = {0: "text", 2: "voice", 4: "category", 5: "announcement", 13: "stage", 15: "forum"}
    t = type_names.get(ch_type, f"type-{ch_type}")
    if ch_type == 4:
        categories[ch_id] = name
        print(f"  📁 {name} (category, ID: {ch_id})")
    else:
        cat_name = categories.get(parent, "No Category")
        print(f"    #{name} ({t}, ID: {ch_id}, category: {cat_name})")

# ─── Step 2: Delete ALL existing channels ─────────────────────────

print(f"\n{'=' * 60}")
print("STEP 2: Deleting all existing channels")
print("=" * 60)

# Sort: delete non-categories first, then categories
non_cats = [ch for ch in channels if ch.get("type") != 4]
cats = [ch for ch in channels if ch.get("type") == 4]

for ch in non_cats + cats:
    name = ch.get("name", "?")
    ch_id = ch.get("id")
    status = api_delete(f"/channels/{ch_id}")
    symbol = "✅" if status in (200, 204) else "❌"
    print(f"  {symbol} Deleted #{name} ({status})")
    time.sleep(0.8)

# ─── Step 3: Create new channel structure ──────────────────────────

print(f"\n{'=' * 60}")
print("STEP 3: Creating new channel structure")
print("=" * 60)

# Channel type constants
TEXT = 0
VOICE = 2
CATEGORY = 4
ANNOUNCEMENT = 5
FORUM = 15

# The full server structure
# Each category has a list of (name, type, topic) tuples
STRUCTURE = {
    # ── Welcome & Info ──
    "━━ WELCOME ━━": [
        ("welcome", ANNOUNCEMENT, "Welcome to Hedge Edge! Read the rules and get started."),
        ("rules", TEXT, "Server rules and guidelines. Read before posting."),
        ("announcements", ANNOUNCEMENT, "Official Hedge Edge announcements and updates."),
        ("roles", TEXT, "React to assign yourself roles and access channels."),
        ("introduce-yourself", TEXT, "New here? Tell us about your trading journey!"),
    ],

    # ── General Community ──
    "━━ COMMUNITY ━━": [
        ("general-chat", TEXT, "Hang out and chat about anything."),
        ("memes-and-fun", TEXT, "Trading memes, jokes, and laughs."),
        ("wins-and-milestones", TEXT, "Share your passes, payouts, and achievements! 🏆"),
        ("suggestions", TEXT, "Ideas to improve Hedge Edge? Drop them here."),
    ],

    # ── Trading Discussion ──
    "━━ TRADING ━━": [
        ("market-discussion", TEXT, "Daily market talk — forex, indices, crypto, commodities."),
        ("trade-ideas", TEXT, "Share setups, analysis, and trade ideas."),
        ("trade-journal", FORUM, "Post your trade journals and track progress over time."),
        ("strategies", TEXT, "Discuss trading strategies, backtesting, and edge development."),
        ("risk-management", TEXT, "Position sizing, drawdown rules, and capital preservation."),
    ],

    # ── Prop Firm Hub ──
    "━━ PROP FIRMS ━━": [
        ("prop-firm-general", TEXT, "General prop firm discussion — which ones, experiences, tips."),
        ("challenge-updates", TEXT, "Live updates on your prop firm challenges."),
        ("payout-proofs", TEXT, "Post your payout screenshots and certificates. 💰"),
        ("prop-firm-reviews", FORUM, "In-depth reviews of prop firms. Help the community choose."),
        ("broker-discussion", TEXT, "Broker comparisons, execution quality, spreads."),
    ],

    # ── Hedge Edge Product ──
    "━━ HEDGE EDGE ━━": [
        ("how-it-works", TEXT, "Learn how Hedge Edge protects your challenges and recovers fees."),
        ("setup-guide", TEXT, "Step-by-step setup instructions for the hedging tool."),
        ("feature-requests", FORUM, "Request features and vote on what gets built next."),
        ("bug-reports", TEXT, "Found an issue? Report it here."),
        ("beta-testing", TEXT, "Early access to new features for beta testers."),
    ],

    # ── Education ──
    "━━ EDUCATION ━━": [
        ("learning-resources", TEXT, "Free guides, videos, and educational content."),
        ("hedge-guide", TEXT, "The free Hedge Edge guide — everything about challenge hedging."),
        ("ask-questions", TEXT, "No dumb questions. Ask anything about trading or hedging."),
        ("book-recommendations", TEXT, "Trading books that changed your perspective."),
    ],

    # ── Premium / Members Only ──
    "━━ PREMIUM ━━": [
        ("premium-chat", TEXT, "Exclusive chat for Challenge Shield subscribers. 🛡️"),
        ("premium-signals", TEXT, "Premium trade signals and hedging alerts."),
        ("premium-resources", TEXT, "Subscriber-only guides, tools, and templates."),
    ],

    # ── Voice Channels ──
    "━━ VOICE ━━": [
        ("Trading Lounge", VOICE, None),
        ("Market Hours", VOICE, None),
        ("Study Room", VOICE, None),
        ("AMA Stage", VOICE, None),
    ],

    # ── Staff / Admin ──
    "━━ STAFF ━━": [
        ("staff-chat", TEXT, "Internal staff communication."),
        ("mod-logs", TEXT, "Moderation actions and logs."),
        ("bot-commands", TEXT, "Bot testing and admin commands."),
    ],
}

created_channels = {}

for category_name, channel_list in STRUCTURE.items():
    # Create the category
    status, cat_data = api_post(f"/guilds/{GUILD_ID}/channels", {
        "name": category_name,
        "type": CATEGORY,
    })
    cat_id = cat_data.get("id")
    print(f"\n📁 {category_name} (ID: {cat_id})")
    time.sleep(0.8)

    # Create channels within category
    for ch_name, ch_type, ch_topic in channel_list:
        payload = {
            "name": ch_name,
            "type": ch_type,
            "parent_id": cat_id,
        }
        if ch_topic:
            payload["topic"] = ch_topic

        status, ch_data = api_post(f"/guilds/{GUILD_ID}/channels", payload)
        ch_id = ch_data.get("id", "?")
        type_label = {0: "text", 2: "voice", 5: "announce", 15: "forum"}.get(ch_type, "?")
        symbol = "✅" if status in (200, 201) else "❌"
        print(f"  {symbol} #{ch_name} ({type_label}, ID: {ch_id})")
        created_channels[ch_name] = ch_id
        time.sleep(0.8)


# ─── Step 4: Summary ──────────────────────────────────────────────

print(f"\n{'=' * 60}")
print("STEP 4: Summary")
print("=" * 60)

# Re-fetch to confirm
final_channels = api_get(f"/guilds/{GUILD_ID}/channels")
cats_count = sum(1 for c in final_channels if c.get("type") == 4)
text_count = sum(1 for c in final_channels if c.get("type") in (0, 5, 15))
voice_count = sum(1 for c in final_channels if c.get("type") == 2)

print(f"Categories: {cats_count}")
print(f"Text/Announcement/Forum channels: {text_count}")
print(f"Voice channels: {voice_count}")
print(f"Total: {len(final_channels)}")

# Output key channel IDs for .env
print("\n--- Key Channel IDs for .env ---")
important = [
    "welcome", "announcements", "general-chat", "rules",
    "market-discussion", "challenge-updates", "premium-chat",
    "staff-chat", "bot-commands", "introduce-yourself"
]
for name in important:
    if name in created_channels:
        print(f"  {name}: {created_channels[name]}")
