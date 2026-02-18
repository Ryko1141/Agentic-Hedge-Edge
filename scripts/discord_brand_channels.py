"""
Update all Hedge Edge Discord channels with emoji names and branded descriptions.
Uses PATCH /channels/{id} to update name + topic for each channel.
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


# ─── Fetch current channels ───────────────────────────────────────

r = requests.get(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS, timeout=15)
channels = r.json()

# Build lookup: name → channel object
by_name = {}
for ch in channels:
    by_name[ch["name"]] = ch

print(f"Found {len(channels)} channels on server\n")

# ─── Define updates: old_name → (new_name, new_topic) ─────────────
# Categories get emoji dividers, channels get relevant emojis
# Topics use Hedge Edge brand voice: direct, helpful, trading-community focused

UPDATES = {
    # ━━ CATEGORIES ━━
    "━━ WELCOME ━━":    ("🏠 ━━ WELCOME ━━", None),
    "━━ COMMUNITY ━━":  ("💬 ━━ COMMUNITY ━━", None),
    "━━ TRADING ━━":    ("📈 ━━ TRADING ━━", None),
    "━━ PROP FIRMS ━━":  ("🏦 ━━ PROP FIRMS ━━", None),
    "━━ HEDGE EDGE ━━": ("🛡️ ━━ HEDGE EDGE ━━", None),
    "━━ EDUCATION ━━":  ("📚 ━━ EDUCATION ━━", None),
    "━━ PREMIUM ━━":    ("👑 ━━ PREMIUM ━━", None),
    "━━ VOICE ━━":      ("🎙️ ━━ VOICE ━━", None),
    "━━ STAFF ━━":      ("🔒 ━━ STAFF ━━", None),

    # ━━ WELCOME channels ━━
    "welcome": (
        "👋・welcome",
        "Welcome to the Hedge Edge community! We protect prop firm traders from losing challenge fees. Grab your roles in #🎭・roles and introduce yourself!"
    ),
    "rules": (
        "📜・rules",
        "Server rules & guidelines — respect the community, no financial advice, keep it professional. Breaking rules = timeout or ban."
    ),
    "announcements": (
        "📢・announcements",
        "Official Hedge Edge updates, product launches, feature drops, and partnership news. Stay in the loop."
    ),
    "roles": (
        "🎭・roles",
        "React below to grab your roles — Prop Firm Trader, Hedger, Beta Tester, and more. Roles unlock access to specific channels."
    ),
    "introduce-yourself": (
        "👤・introductions",
        "New to Hedge Edge? Drop a quick intro — what do you trade, which prop firms you're with, and what brought you here."
    ),

    # ━━ COMMUNITY channels ━━
    "general-chat": (
        "💬・general-chat",
        "The main hangout. Talk about anything — markets, life, strategies, or just vibe with the community."
    ),
    "memes-and-fun": (
        "😂・memes",
        "Trading memes, prop firm pain, blown accounts, and the occasional W. Keep it fun, keep it clean."
    ),
    "wins-and-milestones": (
        "🏆・wins",
        "Passed a challenge? Got a payout? Hit a milestone? Post the proof and celebrate with the community."
    ),
    "suggestions": (
        "💡・suggestions",
        "Got ideas to make Hedge Edge or this server better? Drop them here. We actually read these."
    ),

    # ━━ TRADING channels ━━
    "market-discussion": (
        "📊・market-talk",
        "Daily market discussion — forex, indices, gold, crypto, oil. What are you watching today?"
    ),
    "trade-ideas": (
        "🎯・trade-ideas",
        "Share your setups, chart analysis, and trade ideas. Include your reasoning — help others learn too."
    ),
    "trade-journal": (
        "📓・trade-journal",
        "Post your trading journal entries. Track your progress, document your edge, and stay accountable."
    ),
    "strategies": (
        "🧠・strategies",
        "Discuss trading strategies, backtesting results, and edge development. What's working for you?"
    ),
    "risk-management": (
        "🛡️・risk-management",
        "Position sizing, drawdown rules, daily loss limits, and capital preservation. The boring stuff that keeps you funded."
    ),

    # ━━ PROP FIRMS channels ━━
    "prop-firm-general": (
        "🏦・prop-firms",
        "General prop firm discussion — which firms are legit, rule changes, experiences, and tips for passing."
    ),
    "challenge-updates": (
        "⚡・challenge-updates",
        "Live updates on your prop firm challenges. Day 3 of Phase 1? Share the journey. We're rooting for you."
    ),
    "payout-proofs": (
        "💰・payouts",
        "Post your payout screenshots and funded certificates. Nothing hits harder than proof of concept."
    ),
    "prop-firm-reviews": (
        "⭐・firm-reviews",
        "In-depth reviews of prop firms — spreads, rules, payout speed, support quality. Help the community choose wisely."
    ),
    "broker-discussion": (
        "🔗・brokers",
        "Broker comparisons, execution quality, spreads, and platform discussion. MT4, MT5, cTrader, and more."
    ),

    # ━━ HEDGE EDGE channels ━━
    "how-it-works": (
        "❓・how-it-works",
        "Learn how Hedge Edge protects your challenges and recovers failed fees. The math, the strategy, the edge."
    ),
    "setup-guide": (
        "🔧・setup-guide",
        "Step-by-step instructions to get Hedge Edge running on your accounts. From zero to hedged in 10 minutes."
    ),
    "feature-requests": (
        "✨・feature-requests",
        "Request new features and vote on what gets built next. Your input shapes the product roadmap."
    ),
    "bug-reports": (
        "🐛・bug-reports",
        "Found a bug or something not working right? Report it here with details and we'll squash it fast."
    ),
    "beta-testing": (
        "🧪・beta-testing",
        "Early access to upcoming features. Test, break things, and give feedback before public release."
    ),

    # ━━ EDUCATION channels ━━
    "learning-resources": (
        "📚・resources",
        "Free guides, video tutorials, PDFs, and tools to level up your trading. Community-curated."
    ),
    "hedge-guide": (
        "📖・hedge-guide",
        "The free Hedge Edge guide — everything you need to know about challenge hedging, fee recovery, and risk offsets."
    ),
    "ask-questions": (
        "🙋・ask-questions",
        "No dumb questions here. Whether you're brand new or a funded trader, ask anything about trading or hedging."
    ),
    "book-recommendations": (
        "📕・books",
        "Trading books that changed your perspective. Drop your must-reads and find your next one."
    ),

    # ━━ PREMIUM channels ━━
    "premium-chat": (
        "👑・premium-chat",
        "Exclusive chat for Challenge Shield subscribers. Direct access to the Hedge Edge team and premium community."
    ),
    "premium-signals": (
        "📡・premium-signals",
        "Subscriber-only hedging alerts, trade signals, and market insights. The edge behind the edge."
    ),
    "premium-resources": (
        "🔐・premium-resources",
        "Subscriber-only guides, templates, EA configs, and tools. Constantly updated with new material."
    ),

    # ━━ VOICE channels ━━
    "Trading Lounge": ("🎧・Trading Lounge", None),
    "Market Hours":   ("📻・Market Hours", None),
    "Study Room":     ("📖・Study Room", None),
    "AMA Stage":      ("🎤・AMA Stage", None),

    # ━━ STAFF channels ━━
    "staff-chat": (
        "🔒・staff-chat",
        "Internal staff communication. Strategy, operations, and coordination."
    ),
    "mod-logs": (
        "📋・mod-logs",
        "Automated moderation logs — bans, timeouts, deleted messages, and audit trail."
    ),
    "bot-commands": (
        "🤖・bot-commands",
        "Bot testing and admin commands. Keep the noise here, not in public channels."
    ),
}


# ─── Apply updates ─────────────────────────────────────────────────

print("Updating channels with emojis and branded descriptions...\n")

success = 0
failed = 0
not_found = 0

for old_name, (new_name, new_topic) in UPDATES.items():
    ch = by_name.get(old_name)
    if not ch:
        print(f"  ⚠️  '{old_name}' — not found on server, skipping")
        not_found += 1
        continue

    ch_id = ch["id"]
    payload = {"name": new_name}
    if new_topic is not None:
        payload["topic"] = new_topic

    status, resp = api_patch(f"/channels/{ch_id}", payload)

    if status == 200:
        print(f"  ✅ {new_name}")
        success += 1
    else:
        err = resp.get("message", resp)
        print(f"  ❌ {new_name} — Error: {err}")
        failed += 1

    time.sleep(1.2)  # stay well under rate limits


# ─── Summary ───────────────────────────────────────────────────────

print(f"\n{'=' * 50}")
print(f"Done! {success} updated, {failed} failed, {not_found} not found.")
print(f"Total channels with emojis + descriptions: {success}")
