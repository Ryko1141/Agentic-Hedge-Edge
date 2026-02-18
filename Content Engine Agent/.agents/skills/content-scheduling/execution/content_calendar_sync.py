#!/usr/bin/env python3
"""
content_calendar_sync.py — Content Engine Agent Scheduling

Manage the content calendar: add content, track status, and view upcoming publishes.

Usage:
    python content_calendar_sync.py --action add-content --title "How Hedge Edge Saves Prop Traders $500/mo" --platform YouTube --format Video
    python content_calendar_sync.py --action update-status --title "How Hedge Edge..." --status Published --url "https://youtube.com/..."
    python content_calendar_sync.py --action calendar-report
    python content_calendar_sync.py --action next-publish
"""

import sys, os, argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def add_content(args):
    """Add content to the calendar."""
    row = {
        "Title":           args.title,
        "Platform":        args.platform or "YouTube",
        "Format":          args.format or "Video",
        "Status":          "Idea",
        "Publish Date":    args.publish_date or (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "Topic":           args.topic or "",
        "SEO Keyword":     args.seo_keyword or "",
        "Repurposed From": args.repurposed or "",
    }
    add_row("content_calendar", row)
    print(f"✅ Content added: {args.title}")
    print(f"   Platform: {row['Platform']} | Format: {row['Format']} | Publish: {row['Publish Date']}")
    log_task("Content Engine", f"Content: {args.title}", "Complete", "P2",
             f"{row['Platform']} {row['Format']}")


def update_status(args):
    """Update content piece status."""
    items = query_db("content_calendar", filter={
        "property": "Title", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Content not found: {args.title}")
        return
    item = items[0]
    old = item.get("Status", "?")
    updates = {"Status": args.status}
    if args.url:
        updates["URL"] = args.url
    update_row(item["_id"], "content_calendar", updates)
    print(f"✅ {args.title}: {old} → {args.status}")
    log_task("Content Engine", f"Status update: {args.title}", "Complete", "P3")


def calendar_report(args):
    """Show content organized by status and platform."""
    items = query_db("content_calendar")
    print("=" * 65)
    print("  📅 CONTENT CALENDAR REPORT")
    print("=" * 65)
    if not items:
        print("\n  No content in calendar.")
        return

    by_status = {}
    for item in items:
        s = item.get("Status", "Unknown")
        if s not in by_status:
            by_status[s] = []
        by_status[s].append(item)

    for status in ["Idea", "Scripted", "In Production", "Review", "Scheduled", "Published"]:
        group = by_status.get(status, [])
        if group:
            print(f"\n  {status} ({len(group)})")
            for item in group:
                print(f"    • [{item.get('Platform', '?')}] {item.get('Title', '?')} — {item.get('Publish Date', '?')}")
    print(f"\n{'─' * 65}")
    print(f"  Total: {len(items)} content pieces")
    log_task("Content Engine", "Calendar report", "Complete", "P3",
             f"{len(items)} pieces across statuses")


def next_publish(args):
    """Show next 7 days of scheduled content."""
    today = datetime.now().strftime("%Y-%m-%d")
    week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    items = query_db("content_calendar", filter={
        "and": [
            {"property": "Publish Date", "date": {"on_or_after": today}},
            {"property": "Publish Date", "date": {"on_or_before": week}},
        ]
    })
    print("=" * 65)
    print("  📆 NEXT 7 DAYS — PUBLISHING SCHEDULE")
    print("=" * 65)
    if not items:
        print("\n  No content scheduled for the next 7 days.")
    else:
        items.sort(key=lambda x: x.get("Publish Date", ""))
        for item in items:
            print(f"\n  {item.get('Publish Date', '?')} | [{item.get('Platform', '?')}] {item.get('Title', '?')}")
            print(f"    Status: {item.get('Status', '?')} | Format: {item.get('Format', '?')}")
    log_task("Content Engine", "Next publish check", "Complete", "P3",
             f"{len(items)} pieces in next 7 days")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content Calendar Management")
    parser.add_argument("--action", required=True,
                        choices=["add-content", "update-status", "calendar-report", "next-publish"])
    parser.add_argument("--title")
    parser.add_argument("--platform", default="YouTube")
    parser.add_argument("--format", default="Video")
    parser.add_argument("--status")
    parser.add_argument("--publish-date", dest="publish_date")
    parser.add_argument("--topic", default="")
    parser.add_argument("--seo-keyword", default="", dest="seo_keyword")
    parser.add_argument("--url", default="")
    parser.add_argument("--repurposed", default="")
    args = parser.parse_args()
    {"add-content": add_content, "update-status": update_status,
     "calendar-report": calendar_report, "next-publish": next_publish}[args.action](args)
