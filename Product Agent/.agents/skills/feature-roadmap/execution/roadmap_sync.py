#!/usr/bin/env python3
"""
roadmap_sync.py — Product Agent Feature Roadmap

Manage the product roadmap: add features, prioritize, and track progress.

Usage:
    python roadmap_sync.py --action add-feature --title "Multi-broker payout split view" --priority P1 --quarter Q3-2025
    python roadmap_sync.py --action update-status --title "Multi-broker..." --status "In Development"
    python roadmap_sync.py --action prioritize
    python roadmap_sync.py --action roadmap-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def add_feature(args):
    row = {
        "Feature":       args.title,
        "Status":        "Backlog",
        "Priority":      args.priority or "P2",
        "Quarter":       args.quarter or "",
        "Owner":         args.owner or "",
        "Category":      args.category or "Platform",
        "User Story":    args.story or "",
        "Effort (days)": args.effort or 0,
    }
    add_row("feature_roadmap", row)
    print(f"✅ Feature added: {args.title}")
    print(f"   Priority: {row['Priority']} | Quarter: {row['Quarter'] or 'TBD'} | Effort: {row['Effort (days)'] or '?'} days")
    log_task("Product", f"Feature: {args.title}", "Complete", "P2")


def update_status(args):
    items = query_db("feature_roadmap", filter={
        "property": "Feature", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Feature not found: {args.title}"); return
    item = items[0]
    old = item.get("Status", "?")
    updates = {"Status": args.status}
    if args.status == "Shipped":
        updates["Ship Date"] = datetime.now().strftime("%Y-%m-%d")
    update_row(item["_id"], "feature_roadmap", updates)
    print(f"✅ {args.title}: {old} → {args.status}")
    log_task("Product", f"Feature update: {args.title}", "Complete", "P3")


def prioritize(args):
    """Show features sorted by priority and effort."""
    items = query_db("feature_roadmap", filter={
        "property": "Status", "select": {"does_not_equal": "Shipped"}
    })
    print("=" * 65)
    print("  🎯 PRIORITIZED BACKLOG")
    print("=" * 65)
    if not items:
        print("\n  No open features."); return
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(key=lambda x: (priority_order.get(x.get("Priority", "P2"), 9), int(x.get("Effort (days)", 99) or 99)))
    for item in items:
        print(f"\n  [{item.get('Priority', '?')}] {item.get('Feature', '?')}")
        print(f"    Status: {item.get('Status', '?')} | Quarter: {item.get('Quarter', 'TBD')} | Effort: {item.get('Effort (days)', '?')}d")
    print(f"\n{'─' * 65}")
    print(f"  Total open features: {len(items)}")
    log_task("Product", "Prioritization review", "Complete", "P2",
             f"{len(items)} features ranked")


def roadmap_report(args):
    items = query_db("feature_roadmap")
    print("=" * 65)
    print("  🗺️ PRODUCT ROADMAP REPORT")
    print("=" * 65)
    if not items:
        print("\n  No features on roadmap."); return

    by_quarter = {}
    for item in items:
        q = item.get("Quarter", "Unscheduled") or "Unscheduled"
        by_quarter.setdefault(q, []).append(item)

    for quarter in sorted(by_quarter.keys()):
        group = by_quarter[quarter]
        shipped = sum(1 for f in group if f.get("Status") == "Shipped")
        print(f"\n  {quarter} ({shipped}/{len(group)} shipped)")
        for item in group:
            status_icon = "✅" if item.get("Status") == "Shipped" else "🔵" if item.get("Status") == "In Development" else "⬜"
            print(f"    {status_icon} [{item.get('Priority', '?')}] {item.get('Feature', '?')}")
    print(f"\n{'─' * 65}")
    total_shipped = sum(1 for f in items if f.get("Status") == "Shipped")
    print(f"  Total: {len(items)} features | Shipped: {total_shipped}")
    log_task("Product", "Roadmap report", "Complete", "P3",
             f"{len(items)} features, {total_shipped} shipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Roadmap Management")
    parser.add_argument("--action", required=True,
                        choices=["add-feature", "update-status", "prioritize", "roadmap-report"])
    parser.add_argument("--title")
    parser.add_argument("--priority")
    parser.add_argument("--quarter")
    parser.add_argument("--status")
    parser.add_argument("--owner", default="")
    parser.add_argument("--category", default="Platform")
    parser.add_argument("--story", default="")
    parser.add_argument("--effort", type=int, default=0)
    args = parser.parse_args()
    {"add-feature": add_feature, "update-status": update_status,
     "prioritize": prioritize, "roadmap-report": roadmap_report}[args.action](args)
