#!/usr/bin/env python3
"""
discord_manager.py — Community Manager Agent: Discord Management

Manage Discord server operations, moderation tracking, and community health
metrics for the Hedge Edge trading community.

Usage:
    python discord_manager.py --action server-health
    python discord_manager.py --action moderation-log --user "TraderX#1234" --mod-action warn --reason "Spam in #general"
    python discord_manager.py --action channel-activity
    python discord_manager.py --action growth-report
    python discord_manager.py --action welcome-config
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

GUILD_ID = "1101229154386579468"
DISCORD_INVITE = "https://discord.gg/jVFVc2pQWE"
MOD_ACTIONS = ("warn", "mute", "kick", "ban")

# Channel structure for the Hedge Edge Discord
CHANNELS = {
    "welcome":           {"category": "Start Here",  "purpose": "onboarding"},
    "announcements":     {"category": "Start Here",  "purpose": "updates"},
    "general":           {"category": "Community",    "purpose": "chat"},
    "trading-chat":      {"category": "Community",    "purpose": "discussion"},
    "hedging-strategies":{"category": "Trading",      "purpose": "education"},
    "prop-firm-talk":    {"category": "Trading",      "purpose": "discussion"},
    "drawdown-alerts":   {"category": "Trading",      "purpose": "alerts"},
    "ea-setup-help":     {"category": "Support",      "purpose": "help"},
    "broker-connections":{"category": "Support",      "purpose": "help"},
    "bug-reports":       {"category": "Support",      "purpose": "feedback"},
    "feature-requests":  {"category": "Feedback",     "purpose": "feedback"},
    "wins-and-payouts":  {"category": "Social Proof", "purpose": "engagement"},
    "memes":             {"category": "Social Proof", "purpose": "engagement"},
}


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def server_health(args):
    """Pull Discord server stats and log health snapshot."""
    # Query recent community events for activity proxies
    events = query_db("community_events")
    feedback = query_db("feedback")

    recent_events = [e for e in events if e.get("Date", "") >= (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")]
    recent_feedback = [f for f in feedback if f.get("Date", "") >= (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")]
    mod_actions = [f for f in feedback if f.get("Type") == "Moderation"]

    print("=" * 65)
    print("  🏠 DISCORD SERVER HEALTH")
    print("=" * 65)
    print(f"\n  Guild ID:    {GUILD_ID}")
    print(f"  Invite:      {DISCORD_INVITE}")
    print(f"  Snapshot:    {_today()}")
    print(f"\n  ACTIVITY (last 7 days):")
    print(f"    Events held:          {len(recent_events)}")
    print(f"    Feedback received:    {len(recent_feedback)}")
    print(f"    Moderation actions:   {len(mod_actions)}")
    print(f"\n  CHANNELS: {len(CHANNELS)} configured")
    categories = {}
    for ch, info in CHANNELS.items():
        categories.setdefault(info["category"], []).append(ch)
    for cat, chs in categories.items():
        print(f"    {cat}: {', '.join(chs)}")

    # Health assessment
    health = "🟢 Healthy" if len(mod_actions) < 5 else ("🟡 Monitor" if len(mod_actions) < 15 else "🔴 Action needed")
    print(f"\n  Health status: {health}")
    print(f"{'─' * 65}")

    # Log health snapshot as event
    add_row("community_events", {
        "Event":       f"Health Snapshot {_today()}",
        "Type":        "Metric",
        "Date":        _today(),
        "Platform":    "Discord",
        "Status":      "Completed",
        "Description": f"Events: {len(recent_events)}, Feedback: {len(recent_feedback)}, Mod: {len(mod_actions)}",
    })
    log_task("Community", "Discord health check", "Complete", "P3")


def moderation_log(args):
    """Log a moderation action to feedback DB."""
    action = args.mod_action or "warn"
    severity_map = {"warn": "P3", "mute": "P2", "kick": "P1", "ban": "P0"}
    row = {
        "Feedback":  f"[Mod] {action.upper()}: {args.user}",
        "Type":      "Moderation",
        "Source":    "Discord",
        "Date":      _today(),
        "User":      args.user or "Unknown",
        "Status":    "Logged",
        "Category":  action.capitalize(),
        "Notes":     args.reason or "",
    }
    add_row("feedback", row)

    icon = {"warn": "⚠️", "mute": "🔇", "kick": "👢", "ban": "🔨"}.get(action, "❓")
    print("=" * 65)
    print("  🛡️ MODERATION ACTION LOGGED")
    print("=" * 65)
    print(f"\n  {icon} Action: {action.upper()}")
    print(f"  User:    {args.user}")
    print(f"  Reason:  {args.reason or 'No reason given'}")
    print(f"  Date:    {_today()}")
    print(f"  Severity:{severity_map.get(action, 'P2')}")
    print(f"\n{'─' * 65}")
    log_task("Community", f"Mod: {action} {args.user}", "Complete", severity_map.get(action, "P2"))


def channel_activity(args):
    """Report on channel activity levels with recommendations."""
    feedback = query_db("feedback")

    # Estimate channel activity from feedback sources
    channel_mentions = {}
    for f in feedback:
        notes = (f.get("Notes") or "") + " " + (f.get("Feedback") or "")
        for ch in CHANNELS:
            if ch.replace("-", " ") in notes.lower() or ch in notes.lower():
                channel_mentions[ch] = channel_mentions.get(ch, 0) + 1

    print("=" * 65)
    print("  📊 CHANNEL ACTIVITY REPORT")
    print("=" * 65)

    # Categorize channels
    active = {ch: n for ch, n in channel_mentions.items() if n >= 5}
    moderate = {ch: n for ch, n in channel_mentions.items() if 1 <= n < 5}
    inactive = [ch for ch in CHANNELS if ch not in channel_mentions]

    if active:
        print(f"\n  🟢 ACTIVE ({len(active)})")
        for ch, n in sorted(active.items(), key=lambda x: -x[1]):
            print(f"    #{ch:<25} {n} mentions")

    if moderate:
        print(f"\n  🟡 MODERATE ({len(moderate)})")
        for ch, n in sorted(moderate.items(), key=lambda x: -x[1]):
            print(f"    #{ch:<25} {n} mentions")

    if inactive:
        print(f"\n  🔴 LOW ACTIVITY ({len(inactive)})")
        for ch in inactive:
            info = CHANNELS[ch]
            print(f"    #{ch:<25} ({info['category']})")

    print(f"\n  RECOMMENDATIONS:")
    if inactive:
        print(f"    • Consider seeding content in {len(inactive)} low-activity channels")
        help_chs = [ch for ch in inactive if CHANNELS[ch]["purpose"] == "help"]
        if help_chs:
            print(f"    • Support channels quiet — may indicate good docs or low traffic")
    if len(active) < 3:
        print(f"    • Run targeted events to boost engagement in key channels")
    print(f"    • Pin weekly discussion prompts in #trading-chat and #hedging-strategies")

    print(f"\n{'─' * 65}")
    log_task("Community", "Channel activity report", "Complete", "P3")


def growth_report(args):
    """Member growth metrics and invite source analysis."""
    feedback = query_db("feedback")
    events = query_db("community_events")

    # Aggregate from data
    onboarding = [f for f in feedback if f.get("Type") == "Onboarding"]
    sources = {}
    for f in onboarding:
        src = f.get("Source") or f.get("Category") or "Unknown"
        sources[src] = sources.get(src, 0) + 1

    # New members from events
    total_event_new = sum(int(e.get("NewMembers", 0) or 0) for e in events)

    print("=" * 65)
    print("  📈 DISCORD GROWTH REPORT")
    print("=" * 65)
    print(f"\n  Period:   All time → {_today()}")
    print(f"  Guild:    {GUILD_ID}")

    print(f"\n  SIGNUP SOURCES:")
    if sources:
        total_signups = sum(sources.values())
        for src, count in sorted(sources.items(), key=lambda x: -x[1]):
            pct = count / total_signups * 100 if total_signups else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {src:<20} {count:>4} ({pct:5.1f}%) {bar}")
    else:
        print("    No signup source data yet. Use user-onboarding track-signup.")

    print(f"\n  EVENT-DRIVEN GROWTH:")
    print(f"    New members from events: {total_event_new}")

    completed_events = [e for e in events if e.get("Status") == "Completed"]
    if completed_events:
        avg_new = total_event_new / len(completed_events)
        print(f"    Avg new members/event:   {avg_new:.1f}")
        best = max(completed_events, key=lambda e: int(e.get("NewMembers", 0) or 0))
        print(f"    Best event:              {best.get('Event', '?')} ({best.get('NewMembers', 0)} new)")

    print(f"\n  GROWTH ACTIONS:")
    print(f"    • Post in r/proptrading and prop-firm Discord servers")
    print(f"    • Run referral program with challenge-shield trial rewards")
    print(f"    • Host weekly AMAs to maintain engagement momentum")
    print(f"\n{'─' * 65}")
    log_task("Community", "Growth report", "Complete", "P3")


def welcome_config(args):
    """Show welcome message and onboarding flow configuration."""
    print("=" * 65)
    print("  👋 WELCOME & ONBOARDING CONFIG")
    print("=" * 65)

    print(f"\n  WELCOME MESSAGE:")
    print(f"  ─────────────────────────────────────────")
    print(f"  Welcome to Hedge Edge! 🛡️")
    print(f"  The smartest way to protect your prop-firm accounts.")
    print(f"")
    print(f"  🚀 Get started:")
    print(f"    1. Read #welcome for community rules")
    print(f"    2. Grab your role in #roles")
    print(f"    3. Introduce yourself in #general")
    print(f"    4. Check #hedging-strategies for tips")
    print(f"  ─────────────────────────────────────────")

    print(f"\n  ONBOARDING FLOW:")
    steps = [
        ("Join server",           "#welcome",            "Auto"),
        ("Accept rules",          "#rules",              "Reaction role"),
        ("Select role",           "#roles",              "Reaction role"),
        ("Intro post",            "#general",            "Prompted"),
        ("First strategy read",   "#hedging-strategies", "Nudge after 24h"),
        ("EA setup help",         "#ea-setup-help",      "If subscribed"),
    ]
    for i, (step, channel, trigger) in enumerate(steps, 1):
        print(f"    {i}. {step:<25} {channel:<25} [{trigger}]")

    print(f"\n  AUTO-MESSAGES:")
    print(f"    DM on join:       Enabled — welcome + quick-start link")
    print(f"    24h nudge:        Enabled — if no messages posted")
    print(f"    7d check-in:      Enabled — ask for feedback")
    print(f"\n  Invite URL: {DISCORD_INVITE}")
    print(f"\n{'─' * 65}")
    log_task("Community", "Welcome config review", "Complete", "P3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discord Server Management")
    parser.add_argument("--action", required=True,
                        choices=["server-health", "moderation-log", "channel-activity",
                                 "growth-report", "welcome-config"])
    parser.add_argument("--user", default="")
    parser.add_argument("--mod-action", choices=MOD_ACTIONS)
    parser.add_argument("--reason", default="")
    args = parser.parse_args()
    {
        "server-health":   server_health,
        "moderation-log":  moderation_log,
        "channel-activity":channel_activity,
        "growth-report":   growth_report,
        "welcome-config":  welcome_config,
    }[args.action](args)
