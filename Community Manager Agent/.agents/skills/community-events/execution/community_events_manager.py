#!/usr/bin/env python3
"""
community_events_manager.py — Community Manager Agent: Community Events

Plan, schedule, and manage community events (Discord AMAs, trading workshops,
webinars, product demos, challenges).

Usage:
    python community_events_manager.py --action create-event --name "Friday AMA: Hedging 101" --type ama --date 2026-02-28 --platform discord --description "Live Q\u0026A on basic hedging strategies"
    python community_events_manager.py --action upcoming
    python community_events_manager.py --action record-attendance --event-name "Friday AMA: Hedging 101" --attendees 42 --new-members 8 --feedback-score 4
    python community_events_manager.py --action event-stats
    python community_events_manager.py --action plan-monthly --month 2026-03
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

# ───────── helpers ─────────
EVENT_TYPES = ("ama", "workshop", "webinar", "demo", "challenge", "meetup")
PLATFORMS = ("discord", "zoom", "twitter-spaces")
DISCORD_INVITE = "https://discord.gg/jVFVc2pQWE"

TYPE_TEMPLATES = {
    "ama":       {"duration": "60 min", "cadence": "weekly",  "ideal_day": "Friday"},
    "workshop":  {"duration": "90 min", "cadence": "biweekly","ideal_day": "Wednesday"},
    "webinar":   {"duration": "45 min", "cadence": "monthly", "ideal_day": "Tuesday"},
    "demo":      {"duration": "30 min", "cadence": "on-release", "ideal_day": "Thursday"},
    "challenge": {"duration": "7 days", "cadence": "monthly", "ideal_day": "Monday"},
    "meetup":    {"duration": "60 min", "cadence": "monthly", "ideal_day": "Saturday"},
}


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ───────── actions ─────────
def create_event(args):
    etype = args.type or "ama"
    platform = args.platform or "discord"
    row = {
        "Event":       args.name,
        "Type":        etype.capitalize(),
        "Date":        args.date or _today(),
        "Platform":    platform.capitalize(),
        "Status":      "Scheduled",
        "Description": args.description or "",
        "Attendees":   0,
        "NewMembers":  0,
        "Score":       0,
    }
    add_row("community_events", row)

    tmpl = TYPE_TEMPLATES.get(etype, {})
    print("=" * 65)
    print("  📅 COMMUNITY EVENT CREATED")
    print("=" * 65)
    print(f"\n  Name:        {args.name}")
    print(f"  Type:        {etype.capitalize()} ({tmpl.get('duration', '?')})")
    print(f"  Date:        {row['Date']}")
    print(f"  Platform:    {platform.capitalize()}")
    if platform == "discord":
        print(f"  Invite:      {DISCORD_INVITE}")
    if args.description:
        print(f"  Description: {args.description}")
    print(f"\n{'─' * 65}")
    print(f"  ✅ Event added to community_events DB")
    log_task("Community", f"Event created: {args.name}", "Complete", "P2")


def upcoming(args):
    items = query_db("community_events")
    today = _today()
    future = [e for e in items if e.get("Date", "") >= today and e.get("Status") != "Completed"]
    future.sort(key=lambda e: e.get("Date", "9999"))

    print("=" * 65)
    print("  📅 UPCOMING COMMUNITY EVENTS")
    print("=" * 65)

    if not future:
        print("\n  No upcoming events scheduled.")
        print("  Run --action create-event to add one.\n")
        return

    for e in future:
        days_until = (datetime.strptime(e["Date"], "%Y-%m-%d") - datetime.strptime(today, "%Y-%m-%d")).days
        urgency = "🔴" if days_until <= 2 else ("🟡" if days_until <= 7 else "🟢")
        print(f"\n  {urgency} {e.get('Event', '?')}")
        print(f"     Date: {e.get('Date', '?')} ({days_until}d away) | Type: {e.get('Type', '?')} | Platform: {e.get('Platform', '?')}")
        desc = e.get("Description", "")
        if desc:
            print(f"     {desc[:80]}")

    print(f"\n{'─' * 65}")
    print(f"  {len(future)} upcoming event(s)")
    log_task("Community", "Listed upcoming events", "Complete", "P3",
             f"{len(future)} upcoming")


def record_attendance(args):
    items = query_db("community_events", filter={
        "property": "Event", "title": {"equals": args.event_name}
    })
    if not items:
        print(f"❌ Event not found: {args.event_name}"); return

    item = items[0]
    updates = {
        "Status":     "Completed",
        "Attendees":  args.attendees or 0,
        "NewMembers": args.new_members or 0,
        "Score":      args.feedback_score or 0,
    }
    update_row(item["_id"], "community_events", updates)

    conversion = (args.new_members / args.attendees * 100) if args.attendees else 0
    print("=" * 65)
    print("  📊 EVENT ATTENDANCE RECORDED")
    print("=" * 65)
    print(f"\n  Event:          {args.event_name}")
    print(f"  Attendees:      {args.attendees}")
    print(f"  New members:    {args.new_members}")
    print(f"  Conversion:     {conversion:.1f}%")
    print(f"  Feedback score: {'⭐' * (args.feedback_score or 0)} ({args.feedback_score}/5)")
    print(f"\n{'─' * 65}")
    rating = "Excellent" if (args.feedback_score or 0) >= 4 else ("Good" if (args.feedback_score or 0) >= 3 else "Needs improvement")
    print(f"  Overall: {rating}")
    log_task("Community", f"Attendance: {args.event_name}", "Complete", "P2",
             f"{args.attendees} attendees, score {args.feedback_score}")


def event_stats(args):
    items = query_db("community_events")
    completed = [e for e in items if e.get("Status") == "Completed"]

    print("=" * 65)
    print("  📊 COMMUNITY EVENT STATISTICS")
    print("=" * 65)

    if not completed:
        print("\n  No completed events yet. Record attendance first.\n"); return

    total_attendees = sum(int(e.get("Attendees", 0) or 0) for e in completed)
    total_new = sum(int(e.get("NewMembers", 0) or 0) for e in completed)
    scores = [int(e.get("Score", 0) or 0) for e in completed if int(e.get("Score", 0) or 0) > 0]
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_attendance = total_attendees / len(completed) if completed else 0

    # Best performing type
    type_stats = {}
    for e in completed:
        t = e.get("Type", "Unknown")
        if t not in type_stats:
            type_stats[t] = {"count": 0, "attendees": 0, "score_sum": 0, "score_n": 0}
        type_stats[t]["count"] += 1
        type_stats[t]["attendees"] += int(e.get("Attendees", 0) or 0)
        s = int(e.get("Score", 0) or 0)
        if s > 0:
            type_stats[t]["score_sum"] += s
            type_stats[t]["score_n"] += 1

    best_type = max(type_stats, key=lambda t: type_stats[t]["attendees"]) if type_stats else "N/A"

    print(f"\n  Total events completed: {len(completed)}")
    print(f"  Total attendees:        {total_attendees}")
    print(f"  Avg attendance:         {avg_attendance:.0f}")
    print(f"  New members from events:{total_new}")
    print(f"  Avg feedback score:     {avg_score:.1f}/5")
    print(f"  Best performing type:   {best_type}")

    print(f"\n  BY TYPE:")
    for t, s in sorted(type_stats.items(), key=lambda x: x[1]["attendees"], reverse=True):
        avg_s = s["score_sum"] / s["score_n"] if s["score_n"] else 0
        print(f"    {t:<12} {s['count']} events | {s['attendees']} attendees | avg score {avg_s:.1f}")

    # Month-over-month
    monthly = {}
    for e in completed:
        mo = e.get("Date", "")[:7]
        if mo:
            monthly[mo] = monthly.get(mo, 0) + 1
    if len(monthly) >= 2:
        months_sorted = sorted(monthly.keys())
        prev, curr = months_sorted[-2], months_sorted[-1]
        growth = ((monthly[curr] - monthly[prev]) / monthly[prev] * 100) if monthly[prev] else 0
        print(f"\n  Month-over-month: {monthly[prev]} → {monthly[curr]} ({growth:+.0f}%)")

    print(f"\n{'─' * 65}")
    log_task("Community", "Event stats", "Complete", "P3",
             f"{len(completed)} events, avg {avg_attendance:.0f} attendees")


def plan_monthly(args):
    month = args.month or datetime.now(timezone.utc).strftime("%Y-%m")
    year, mo = int(month.split("-")[0]), int(month.split("-")[1])

    # Pull content calendar and release log for coordination
    content_items = query_db("content_calendar")
    release_items = query_db("release_log")

    month_content = [c for c in content_items if c.get("Date", "").startswith(month)]
    month_releases = [r for r in release_items if r.get("Date", "").startswith(month)]

    print("=" * 65)
    print(f"  📅 SUGGESTED MONTHLY EVENT PLAN — {month}")
    print("=" * 65)

    suggestions = []
    # Weekly AMAs
    for week in range(1, 5):
        day = datetime(year, mo, 1) + timedelta(days=(4 - datetime(year, mo, 1).weekday()) % 7 + 7 * (week - 1))
        if day.month == mo:
            suggestions.append({
                "name": f"Friday AMA Week {week}",
                "type": "AMA", "date": day.strftime("%Y-%m-%d"),
                "platform": "Discord", "reason": "Weekly community engagement"
            })

    # Coordinate demo with releases
    for r in month_releases[:2]:
        suggestions.append({
            "name": f"Product Demo: {r.get('Release', r.get('Name', 'New Feature'))}",
            "type": "Demo", "date": r.get("Date", month + "-15"),
            "platform": "Discord", "reason": f"Aligns with release: {r.get('Release', '?')}"
        })

    # Biweekly workshop
    w1 = datetime(year, mo, 1) + timedelta(days=(2 - datetime(year, mo, 1).weekday()) % 7 + 7)
    if w1.month == mo:
        suggestions.append({
            "name": "Hedging Workshop: Drawdown Protection",
            "type": "Workshop", "date": w1.strftime("%Y-%m-%d"),
            "platform": "Zoom", "reason": "Core educational content"
        })

    # Monthly challenge
    suggestions.append({
        "name": f"{month} Trading Challenge",
        "type": "Challenge", "date": f"{month}-01",
        "platform": "Discord", "reason": "Monthly engagement driver"
    })

    suggestions.sort(key=lambda s: s["date"])
    for i, s in enumerate(suggestions, 1):
        print(f"\n  {i}. {s['name']}")
        print(f"     Type: {s['type']} | Date: {s['date']} | Platform: {s['platform']}")
        print(f"     Reason: {s['reason']}")

    if month_content:
        print(f"\n  CONTENT TO COORDINATE ({len(month_content)} items):")
        for c in month_content[:5]:
            print(f"    📝 {c.get('Title', c.get('Name', '?'))} — {c.get('Date', '?')}")

    print(f"\n{'─' * 65}")
    print(f"  {len(suggestions)} events suggested for {month}")
    log_task("Community", f"Monthly plan: {month}", "Complete", "P3",
             f"{len(suggestions)} events planned")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Community Events Manager")
    parser.add_argument("--action", required=True,
                        choices=["create-event", "upcoming", "record-attendance",
                                 "event-stats", "plan-monthly"])
    parser.add_argument("--name")
    parser.add_argument("--event-name")
    parser.add_argument("--type", choices=EVENT_TYPES)
    parser.add_argument("--date")
    parser.add_argument("--platform", choices=PLATFORMS)
    parser.add_argument("--description", default="")
    parser.add_argument("--attendees", type=int, default=0)
    parser.add_argument("--new-members", type=int, default=0)
    parser.add_argument("--feedback-score", type=int, choices=range(1, 6))
    parser.add_argument("--month")
    args = parser.parse_args()
    {
        "create-event":      create_event,
        "upcoming":          upcoming,
        "record-attendance": record_attendance,
        "event-stats":       event_stats,
        "plan-monthly":      plan_monthly,
    }[args.action](args)
