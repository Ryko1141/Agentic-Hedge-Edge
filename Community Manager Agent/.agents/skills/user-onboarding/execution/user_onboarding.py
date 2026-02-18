#!/usr/bin/env python3
"""
user_onboarding.py — Community Manager Agent: User Onboarding

Manage user onboarding flow for new Hedge Edge signups and Discord community
members. Track signups, monitor completion, and identify stuck users.

Usage:
    python user_onboarding.py --action track-signup --email "trader@example.com" --source discord --plan free-trial
    python user_onboarding.py --action onboarding-status --email "trader@example.com"
    python user_onboarding.py --action completion-report
    python user_onboarding.py --action welcome-sequence --email "trader@example.com"
    python user_onboarding.py --action stuck-users
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

SOURCES = ("discord", "landing-page", "referral", "ads")
PLANS = ("free-trial", "starter", "pro", "enterprise")

ONBOARDING_STEPS = [
    {"key": "account_created",   "label": "Account created",     "order": 1},
    {"key": "email_verified",    "label": "Email verified",       "order": 2},
    {"key": "discord_joined",    "label": "Joined Discord",       "order": 3},
    {"key": "ea_downloaded",     "label": "EA downloaded",        "order": 4},
    {"key": "broker_connected",  "label": "Broker connected",     "order": 5},
    {"key": "first_hedge",       "label": "First hedge executed", "order": 6},
]


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def _parse_steps(notes_str):
    """Parse onboarding step completion from Notes field JSON."""
    try:
        return json.loads(notes_str) if notes_str else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def track_signup(args):
    """Track a new user signup in the feedback DB (Type=Onboarding)."""
    source = args.source or "landing-page"
    plan = args.plan or "free-trial"

    # Initial steps: account created is true, rest false
    steps = {s["key"]: (s["key"] == "account_created") for s in ONBOARDING_STEPS}

    row = {
        "Feedback":  f"[Onboarding] New signup: {args.email}",
        "Type":      "Onboarding",
        "Source":    source.capitalize(),
        "Date":      _today(),
        "User":      args.email,
        "Status":    "In Progress",
        "Category":  plan,
        "Notes":     json.dumps(steps),
    }
    add_row("feedback", row)

    print("=" * 65)
    print("  🆕 NEW USER SIGNUP TRACKED")
    print("=" * 65)
    print(f"\n  Email:   {args.email}")
    print(f"  Source:  {source}")
    print(f"  Plan:    {plan}")
    print(f"  Date:    {_today()}")
    print(f"\n  ONBOARDING STEPS:")
    for s in ONBOARDING_STEPS:
        done = steps.get(s["key"], False)
        icon = "✅" if done else "⬜"
        print(f"    {icon} {s['label']}")
    print(f"\n{'─' * 65}")
    print(f"  Next step: Email verification")
    log_task("Community", f"Signup: {args.email}", "Complete", "P2",
             f"Source: {source}, Plan: {plan}")


def onboarding_status(args):
    """Check onboarding completion for a specific user."""
    items = query_db("feedback", filter={
        "and": [
            {"property": "User", "rich_text": {"equals": args.email}},
            {"property": "Type", "select": {"equals": "Onboarding"}},
        ]
    })

    print("=" * 65)
    print("  📋 ONBOARDING STATUS")
    print("=" * 65)

    if not items:
        print(f"\n  ❌ No onboarding record found for: {args.email}")
        print(f"  Use --action track-signup to register this user.\n")
        return

    item = items[0]
    steps = _parse_steps(item.get("Notes", ""))
    completed = sum(1 for v in steps.values() if v)
    total = len(ONBOARDING_STEPS)
    pct = completed / total * 100 if total else 0

    print(f"\n  User:    {args.email}")
    print(f"  Plan:    {item.get('Category', '?')}")
    print(f"  Signup:  {item.get('Date', '?')}")
    print(f"  Status:  {item.get('Status', '?')}")

    # Progress bar
    filled = int(pct / 5)
    bar = "█" * filled + "░" * (20 - filled)
    print(f"\n  Progress: {bar} {pct:.0f}% ({completed}/{total})")

    print(f"\n  STEPS:")
    next_step = None
    for s in ONBOARDING_STEPS:
        done = steps.get(s["key"], False)
        icon = "✅" if done else "⬜"
        suffix = ""
        if not done and next_step is None:
            next_step = s["label"]
            suffix = " ← NEXT"
        print(f"    {icon} {s['label']}{suffix}")

    if completed == total:
        print(f"\n  🎉 Onboarding complete!")
        signup_date = item.get("Date", "")
        if signup_date:
            try:
                days = (datetime.now(timezone.utc) - datetime.strptime(signup_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
                print(f"  Time to completion: {days} day(s)")
            except ValueError:
                pass
    else:
        print(f"\n  Next step: {next_step}")

    print(f"\n{'─' * 65}")
    log_task("Community", f"Onboarding status: {args.email}", "Complete", "P3")


def completion_report(args):
    """Onboarding funnel analysis: drop-off rates per step."""
    items = query_db("feedback", filter={
        "property": "Type", "select": {"equals": "Onboarding"}
    })

    print("=" * 65)
    print("  📊 ONBOARDING FUNNEL REPORT")
    print("=" * 65)

    if not items:
        print("\n  No onboarding data. Track signups first.\n"); return

    total = len(items)
    step_counts = {s["key"]: 0 for s in ONBOARDING_STEPS}
    completed_all = 0
    time_to_hedge = []

    for item in items:
        steps = _parse_steps(item.get("Notes", ""))
        all_done = True
        for s in ONBOARDING_STEPS:
            if steps.get(s["key"]):
                step_counts[s["key"]] += 1
            else:
                all_done = False
        if all_done:
            completed_all += 1
            signup_date = item.get("Date", "")
            if signup_date:
                try:
                    days = (datetime.now(timezone.utc) - datetime.strptime(signup_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
                    time_to_hedge.append(days)
                except ValueError:
                    pass

    print(f"\n  Total signups: {total}")
    print(f"\n  FUNNEL:")
    prev_count = total
    for s in ONBOARDING_STEPS:
        count = step_counts[s["key"]]
        pct = count / total * 100 if total else 0
        drop = prev_count - count
        drop_pct = drop / prev_count * 100 if prev_count else 0
        bar_len = int(pct / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"    {s['label']:<25} {count:>4} ({pct:5.1f}%) {bar}", end="")
        if drop > 0:
            print(f"  ↓{drop} ({drop_pct:.0f}% drop)")
        else:
            print()
        prev_count = count

    overall_rate = completed_all / total * 100 if total else 0
    print(f"\n  SUMMARY:")
    print(f"    Completion rate:       {overall_rate:.1f}%")
    print(f"    Fully onboarded:       {completed_all}/{total}")
    if time_to_hedge:
        avg_time = sum(time_to_hedge) / len(time_to_hedge)
        print(f"    Avg time to 1st hedge: {avg_time:.1f} days")

    # Biggest drop-off
    max_drop_step = None
    max_drop_val = 0
    prev_count = total
    for s in ONBOARDING_STEPS:
        count = step_counts[s["key"]]
        drop = prev_count - count
        if drop > max_drop_val:
            max_drop_val = drop
            max_drop_step = s["label"]
        prev_count = count

    if max_drop_step:
        print(f"    Biggest drop-off:      {max_drop_step} (-{max_drop_val})")

    # Plan breakdown
    plan_counts = {}
    for item in items:
        plan = item.get("Category", "Unknown")
        plan_counts[plan] = plan_counts.get(plan, 0) + 1
    if plan_counts:
        print(f"\n  BY PLAN:")
        for plan, cnt in sorted(plan_counts.items(), key=lambda x: -x[1]):
            print(f"    {plan:<20} {cnt} signups")

    print(f"\n{'─' * 65}")
    log_task("Community", "Onboarding funnel report", "Complete", "P2",
             f"{total} signups, {overall_rate:.0f}% completion")


def welcome_sequence(args):
    """Trigger the welcome sequence for a new user."""
    sequence_steps = [
        {"day": 0, "subject": "Welcome to Hedge Edge! 🛡️",
         "content": "Account setup guide + EA download link"},
        {"day": 1, "subject": "Connect your broker in 2 minutes",
         "content": "Step-by-step broker connection tutorial"},
        {"day": 2, "subject": "Join our Discord community",
         "content": f"Discord invite: https://discord.gg/jVFVc2pQWE + channel guide"},
        {"day": 3, "subject": "Your first hedge: a walkthrough",
         "content": "Video tutorial: setting up your first hedging strategy"},
        {"day": 5, "subject": "How's it going?",
         "content": "Check-in + link to support channel + FAQ"},
        {"day": 7, "subject": "Pro tips from our community",
         "content": "Top hedging strategies shared by members"},
    ]

    row = {
        "Event":       f"Welcome Sequence: {args.email}",
        "Type":        "Automation",
        "Date":        _today(),
        "Platform":    "Email",
        "Status":      "Active",
        "Description": f"6-step welcome sequence triggered for {args.email}",
    }
    add_row("community_events", row)

    print("=" * 65)
    print("  ✉️ WELCOME SEQUENCE TRIGGERED")
    print("=" * 65)
    print(f"\n  User:     {args.email}")
    print(f"  Started:  {_today()}")
    print(f"  Steps:    {len(sequence_steps)}")

    print(f"\n  SEQUENCE:")
    for step in sequence_steps:
        day_label = "Today" if step["day"] == 0 else f"Day {step['day']}"
        icon = "📧" if step["day"] == 0 else "⏳"
        print(f"    {icon} {day_label:<8} {step['subject']}")
        print(f"                {step['content']}")

    print(f"\n  CHANNELS:")
    print(f"    Email:   Primary delivery")
    print(f"    Discord: Parallel onboarding in #welcome")
    print(f"    In-app:  Checklist widget (if logged in)")
    print(f"\n{'─' * 65}")
    log_task("Community", f"Welcome sequence: {args.email}", "Complete", "P2")


def stuck_users(args):
    """List users stuck in onboarding (signed up >3 days ago, key steps incomplete)."""
    items = query_db("feedback", filter={
        "and": [
            {"property": "Type", "select": {"equals": "Onboarding"}},
            {"property": "Status", "select": {"does_not_equal": "Complete"}},
        ]
    })

    cutoff = _days_ago(3)
    stuck = []
    for item in items:
        signup_date = item.get("Date", "")
        if signup_date and signup_date <= cutoff:
            steps = _parse_steps(item.get("Notes", ""))
            completed = sum(1 for v in steps.values() if v)
            total = len(ONBOARDING_STEPS)
            if completed < total:
                # Find where they're stuck
                stuck_at = "Unknown"
                for s in ONBOARDING_STEPS:
                    if not steps.get(s["key"]):
                        stuck_at = s["label"]
                        break
                days_since = (datetime.now(timezone.utc) - datetime.strptime(signup_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
                stuck.append({
                    "email": item.get("User", "?"),
                    "plan": item.get("Category", "?"),
                    "signup": signup_date,
                    "days": days_since,
                    "completed": completed,
                    "total": total,
                    "stuck_at": stuck_at,
                })

    stuck.sort(key=lambda u: -u["days"])

    print("=" * 65)
    print("  🚧 STUCK USERS (>3 days, incomplete onboarding)")
    print("=" * 65)

    if not stuck:
        print(f"\n  No stuck users! All recent signups are progressing. 🎉\n")
        return

    print(f"\n  {len(stuck)} user(s) need attention:\n")

    # Group by stuck step
    by_step = {}
    for u in stuck:
        by_step.setdefault(u["stuck_at"], []).append(u)

    for step, users in sorted(by_step.items(), key=lambda x: -len(x[1])):
        print(f"  ⚠️ Stuck at: {step} ({len(users)} users)")
        for u in users[:5]:
            pct = u["completed"] / u["total"] * 100 if u["total"] else 0
            severity = "🔴" if u["days"] >= 7 else "🟡"
            print(f"    {severity} {u['email']:<30} {u['plan']:<12} {u['days']}d ago  {pct:.0f}% done")
        if len(users) > 5:
            print(f"    ... and {len(users) - 5} more")

    print(f"\n  INTERVENTION PLAN:")
    print(f"    • Email users stuck at 'EA downloaded' → send setup video")
    print(f"    • Email users stuck at 'Broker connected' → offer 1-on-1 call")
    print(f"    • DM Discord users stuck >7 days → personal outreach")
    print(f"    • Users stuck at 'First hedge' → send strategy template")
    print(f"\n{'─' * 65}")
    log_task("Community", "Stuck users check", "Complete", "P1",
             f"{len(stuck)} users stuck in onboarding")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User Onboarding Manager")
    parser.add_argument("--action", required=True,
                        choices=["track-signup", "onboarding-status", "completion-report",
                                 "welcome-sequence", "stuck-users"])
    parser.add_argument("--email")
    parser.add_argument("--source", choices=SOURCES)
    parser.add_argument("--plan", choices=PLANS)
    args = parser.parse_args()
    {
        "track-signup":      track_signup,
        "onboarding-status": onboarding_status,
        "completion-report": completion_report,
        "welcome-sequence":  welcome_sequence,
        "stuck-users":       stuck_users,
    }[args.action](args)
