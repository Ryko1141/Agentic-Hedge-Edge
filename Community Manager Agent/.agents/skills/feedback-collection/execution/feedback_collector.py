#!/usr/bin/env python3
"""
feedback_collector.py — Community Manager Agent Feedback

Collect, categorize, and surface user/community feedback for product decisions.

Usage:
    python feedback_collector.py --action add-feedback --title "Need mobile app" --source Discord --category Feature --votes 12
    python feedback_collector.py --action update-status --title "Need mobile app" --status "Acknowledged"
    python feedback_collector.py --action feedback-report
    python feedback_collector.py --action top-requests --limit 10
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def add_feedback(args):
    row = {
        "Feedback":  args.title,
        "Source":    args.source or "Discord",
        "Category":  args.category or "General",
        "Status":    "New",
        "Votes":     args.votes or 1,
        "Submitted": datetime.now().strftime("%Y-%m-%d"),
        "User":      args.user or "",
    }
    add_row("feedback", row)
    print(f"💬 Feedback logged: {args.title}")
    print(f"   Source: {row['Source']} | Category: {row['Category']} | Votes: {row['Votes']}")
    log_task("Community", f"Feedback: {args.title}", "Complete", "P2")


def update_status(args):
    items = query_db("feedback", filter={
        "property": "Feedback", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Feedback not found: {args.title}"); return
    item = items[0]
    old = item.get("Status", "?")
    updates = {"Status": args.status}
    if args.votes:
        updates["Votes"] = args.votes
    update_row(item["_id"], "feedback", updates)
    print(f"✅ {args.title}: {old} → {args.status}")
    log_task("Community", f"Feedback update: {args.title}", "Complete", "P3")


def feedback_report(args):
    items = query_db("feedback")
    print("=" * 65)
    print("  💬 COMMUNITY FEEDBACK REPORT")
    print("=" * 65)
    if not items:
        print("\n  No feedback collected."); return

    by_category = {}
    for item in items:
        cat = item.get("Category", "General")
        by_category.setdefault(cat, []).append(item)

    for cat, group in sorted(by_category.items()):
        print(f"\n  {cat} ({len(group)})")
        group.sort(key=lambda x: int(x.get("Votes", 0) or 0), reverse=True)
        for item in group[:5]:
            status_icon = "🟢" if item.get("Status") == "Implemented" else "🟡" if item.get("Status") == "Acknowledged" else "⬜"
            print(f"    {status_icon} {item.get('Feedback', '?')} — {item.get('Votes', 0)} votes [{item.get('Source', '?')}]")

    print(f"\n{'─' * 65}")
    new = sum(1 for f in items if f.get("Status") == "New")
    print(f"  Total: {len(items)} feedback items | New/unprocessed: {new}")
    log_task("Community", "Feedback report", "Complete", "P3",
             f"{len(items)} items, {new} new")


def top_requests(args):
    items = query_db("feedback", filter={
        "property": "Status", "select": {"does_not_equal": "Implemented"}
    })
    print("=" * 65)
    print("  🏆 TOP COMMUNITY REQUESTS")
    print("=" * 65)
    if not items:
        print("\n  No open requests."); return

    items.sort(key=lambda x: int(x.get("Votes", 0) or 0), reverse=True)
    limit = args.limit or 10
    for i, item in enumerate(items[:limit], 1):
        print(f"\n  #{i}  {item.get('Feedback', '?')}")
        print(f"      Votes: {item.get('Votes', 0)} | Source: {item.get('Source', '?')} | Status: {item.get('Status', '?')}")

    print(f"\n{'─' * 65}")
    total_votes = sum(int(f.get("Votes", 0) or 0) for f in items)
    print(f"  Showing top {min(limit, len(items))} of {len(items)} open requests | Total votes: {total_votes}")
    log_task("Community", "Top requests", "Complete", "P3",
             f"Top {min(limit, len(items))} of {len(items)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Community Feedback Management")
    parser.add_argument("--action", required=True,
                        choices=["add-feedback", "update-status", "feedback-report", "top-requests"])
    parser.add_argument("--title")
    parser.add_argument("--source", default="Discord")
    parser.add_argument("--category", default="General")
    parser.add_argument("--status")
    parser.add_argument("--votes", type=int)
    parser.add_argument("--user", default="")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    {"add-feedback": add_feedback, "update-status": update_status,
     "feedback-report": feedback_report, "top-requests": top_requests}[args.action](args)
