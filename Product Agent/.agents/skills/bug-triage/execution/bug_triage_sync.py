#!/usr/bin/env python3
"""
bug_triage_sync.py — Product Agent Bug Tracking

Report, triage, and track bugs to resolution.

Usage:
    python bug_triage_sync.py --action report-bug --title "Dashboard not loading on Safari" --severity P1 --area Frontend
    python bug_triage_sync.py --action update-status --title "Dashboard..." --status "In Progress" --assignee "Dev Team"
    python bug_triage_sync.py --action triage-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def report_bug(args):
    row = {
        "Bug":         args.title,
        "Severity":    args.severity or "P2",
        "Status":      "Open",
        "Area":        args.area or "Platform",
        "Reported By": args.reporter or "Agent",
        "Steps":       args.steps or "",
        "Reported":    datetime.now().strftime("%Y-%m-%d"),
    }
    add_row("bug_tracker", row)
    print(f"🐛 Bug reported: {args.title}")
    print(f"   Severity: {row['Severity']} | Area: {row['Area']}")
    log_task("Product", f"Bug: {args.title}", "Complete", "P1")


def update_status(args):
    items = query_db("bug_tracker", filter={
        "property": "Bug", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Bug not found: {args.title}"); return
    item = items[0]
    old = item.get("Status", "?")
    updates = {"Status": args.status}
    if args.assignee:
        updates["Assignee"] = args.assignee
    if args.status in ("Resolved", "Closed"):
        updates["Resolved"] = datetime.now().strftime("%Y-%m-%d")
    update_row(item["_id"], "bug_tracker", updates)
    print(f"✅ {args.title}: {old} → {args.status}")
    log_task("Product", f"Bug update: {args.title}", "Complete", "P2")


def triage_report(args):
    items = query_db("bug_tracker")
    print("=" * 65)
    print("  🐛 BUG TRIAGE REPORT")
    print("=" * 65)
    if not items:
        print("\n  No bugs tracked."); return

    open_bugs = [b for b in items if b.get("Status") not in ("Resolved", "Closed")]
    resolved  = [b for b in items if b.get("Status") in ("Resolved", "Closed")]

    severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    open_bugs.sort(key=lambda x: severity_order.get(x.get("Severity", "P2"), 9))

    if open_bugs:
        print(f"\n  OPEN ({len(open_bugs)})")
        for bug in open_bugs:
            icon = "🔴" if bug.get("Severity") in ("P0", "P1") else "🟡"
            print(f"    {icon} [{bug.get('Severity', '?')}] {bug.get('Bug', '?')}")
            print(f"       Area: {bug.get('Area', '?')} | Status: {bug.get('Status', '?')} | Reported: {bug.get('Reported', '?')}")

    if resolved:
        print(f"\n  RESOLVED ({len(resolved)})")
        for bug in resolved[:5]:
            print(f"    ✅ {bug.get('Bug', '?')} — {bug.get('Resolved', '?')}")
        if len(resolved) > 5:
            print(f"    ... and {len(resolved) - 5} more")

    print(f"\n{'─' * 65}")
    critical = sum(1 for b in open_bugs if b.get("Severity") in ("P0", "P1"))
    print(f"  Total: {len(items)} bugs | Open: {len(open_bugs)} | Critical open: {critical}")
    log_task("Product", "Triage report", "Complete", "P2",
             f"{len(open_bugs)} open, {critical} critical")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bug Triage Management")
    parser.add_argument("--action", required=True,
                        choices=["report-bug", "update-status", "triage-report"])
    parser.add_argument("--title")
    parser.add_argument("--severity", default="P2")
    parser.add_argument("--status")
    parser.add_argument("--area", default="Platform")
    parser.add_argument("--assignee", default="")
    parser.add_argument("--reporter", default="Agent")
    parser.add_argument("--steps", default="")
    args = parser.parse_args()
    {"report-bug": report_bug, "update-status": update_status,
     "triage-report": triage_report}[args.action](args)
