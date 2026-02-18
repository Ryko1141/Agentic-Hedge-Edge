#!/usr/bin/env python3
"""
release_tracker.py — Product Agent Release Management

Track releases through staging → QA → production with changelogs.

Usage:
    python release_tracker.py --action create-release --version "v0.4.0" --title "Multi-broker dashboard"
    python release_tracker.py --action update-status --version "v0.4.0" --status "In QA" --notes "Smoke tests passing"
    python release_tracker.py --action release-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def create_release(args):
    row = {
        "Version":    args.version,
        "Title":      args.title or "",
        "Status":     "Planning",
        "Created":    datetime.now().strftime("%Y-%m-%d"),
        "Changelog":  args.changelog or "",
        "Features":   args.features or "",
        "Bugs Fixed": args.bugs_fixed or "",
    }
    add_row("release_log", row)
    print(f"🚀 Release created: {args.version}")
    if args.title: print(f"   Title: {args.title}")
    print(f"   Status: Planning")
    log_task("Product", f"Release {args.version}", "Complete", "P1")


def update_status(args):
    items = query_db("release_log", filter={
        "property": "Version", "title": {"equals": args.version}
    })
    if not items:
        print(f"❌ Release not found: {args.version}"); return
    item = items[0]
    old = item.get("Status", "?")
    updates = {"Status": args.status}
    if args.notes:
        existing = item.get("Changelog", "") or ""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        updates["Changelog"] = f"{existing}\n[{ts}] {args.notes}".strip()
    if args.status == "Released":
        updates["Release Date"] = datetime.now().strftime("%Y-%m-%d")
    update_row(item["_id"], "release_log", updates)
    print(f"✅ {args.version}: {old} → {args.status}")
    if args.notes: print(f"   Note: {args.notes}")
    log_task("Product", f"Release update {args.version}", "Complete", "P2")


def release_report(args):
    items = query_db("release_log")
    print("=" * 65)
    print("  🚀 RELEASE TRACKER")
    print("=" * 65)
    if not items:
        print("\n  No releases tracked."); return

    items.sort(key=lambda x: x.get("Created", ""), reverse=True)
    for item in items:
        icon = "✅" if item.get("Status") == "Released" else "🔵" if "QA" in (item.get("Status") or "") else "⬜"
        print(f"\n  {icon} {item.get('Version', '?')} — {item.get('Title', '')}")
        print(f"    Status: {item.get('Status', '?')} | Created: {item.get('Created', '?')}")
        if item.get("Release Date"):
            print(f"    Released: {item.get('Release Date')}")
        if item.get("Changelog"):
            lines = item["Changelog"].strip().split("\n")[-2:]
            for line in lines:
                print(f"    📝 {line}")

    print(f"\n{'─' * 65}")
    released = sum(1 for r in items if r.get("Status") == "Released")
    print(f"  Total: {len(items)} releases | {released} shipped")
    log_task("Product", "Release report", "Complete", "P3",
             f"{len(items)} releases, {released} shipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Release Management")
    parser.add_argument("--action", required=True,
                        choices=["create-release", "update-status", "release-report"])
    parser.add_argument("--version")
    parser.add_argument("--title", default="")
    parser.add_argument("--status")
    parser.add_argument("--changelog", default="")
    parser.add_argument("--features", default="")
    parser.add_argument("--bugs-fixed", default="", dest="bugs_fixed")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    {"create-release": create_release, "update-status": update_status,
     "release-report": release_report}[args.action](args)
