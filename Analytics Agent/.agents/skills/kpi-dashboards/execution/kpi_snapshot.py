#!/usr/bin/env python3
"""
kpi_snapshot.py — Analytics Agent KPI Dashboards

Take weekly/monthly KPI snapshots and surface trends for executive review.

Usage:
    python kpi_snapshot.py --action take-snapshot --metric MRR --value 2400 --period 2025-W24
    python kpi_snapshot.py --action weekly-report --period 2025-W24
    python kpi_snapshot.py --action trend --metric MRR --periods 8
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, log_task


def take_snapshot(args):
    row = {
        "Metric":  args.metric,
        "Value":   args.value,
        "Period":  args.period or datetime.now().strftime("%Y-W%W"),
        "Agent":   args.agent or "Analytics",
        "Notes":   args.notes or "",
        "Date":    datetime.now().strftime("%Y-%m-%d"),
    }
    add_row("kpi_snapshots", row)
    print(f"📊 KPI Snapshot: {args.metric} = {args.value}")
    print(f"   Period: {row['Period']}")
    log_task("Analytics", f"KPI: {args.metric} = {args.value}", "Complete", "P2")


def weekly_report(args):
    period = args.period or datetime.now().strftime("%Y-W%W")
    items = query_db("kpi_snapshots", filter={
        "property": "Period", "rich_text": {"equals": period}
    })
    print("=" * 65)
    print(f"  📊 KPI REPORT — {period}")
    print("=" * 65)
    if not items:
        print(f"\n  No KPI data for period {period}."); return

    for item in sorted(items, key=lambda x: x.get("Metric", "")):
        print(f"\n  {item.get('Metric', '?')}: {item.get('Value', '?')}")
        if item.get("Notes"):
            print(f"    📝 {item['Notes']}")

    print(f"\n{'─' * 65}")
    print(f"  {len(items)} metrics captured for {period}")
    log_task("Analytics", f"Weekly report {period}", "Complete", "P2",
             f"{len(items)} KPIs")


def trend(args):
    """Show KPI trend over the last N periods."""
    items = query_db("kpi_snapshots", filter={
        "property": "Metric", "rich_text": {"equals": args.metric}
    })
    print("=" * 65)
    print(f"  📈 TREND: {args.metric}")
    print("=" * 65)
    if not items:
        print(f"\n  No data for metric: {args.metric}"); return

    items.sort(key=lambda x: x.get("Period", ""))
    limited = items[-(args.periods or 8):]

    values = []
    for item in limited:
        val = item.get("Value", 0)
        try:
            val = float(val)
            values.append(val)
        except:
            values.append(0)
        print(f"\n  {item.get('Period', '?')}: {item.get('Value', '?')}")

    if len(values) >= 2:
        change = values[-1] - values[0]
        pct = (change / values[0] * 100) if values[0] != 0 else 0
        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        print(f"\n{'─' * 65}")
        print(f"  {direction} Change: {change:+.2f} ({pct:+.1f}%) over {len(values)} periods")
    else:
        print(f"\n  Need at least 2 data points for trend analysis.")

    log_task("Analytics", f"Trend: {args.metric}", "Complete", "P3",
             f"{len(limited)} periods")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KPI Snapshot Management")
    parser.add_argument("--action", required=True,
                        choices=["take-snapshot", "weekly-report", "trend"])
    parser.add_argument("--metric")
    parser.add_argument("--value", type=float)
    parser.add_argument("--period")
    parser.add_argument("--agent", default="Analytics")
    parser.add_argument("--notes", default="")
    parser.add_argument("--periods", type=int, default=8)
    args = parser.parse_args()
    {"take-snapshot": take_snapshot, "weekly-report": weekly_report,
     "trend": trend}[args.action](args)
