#!/usr/bin/env python3
"""
funnel_calculator.py — Analytics Agent Funnel Analytics

Record and analyze conversion funnel stages (Visit → Signup → Demo → Trial → Paid).

Usage:
    python funnel_calculator.py --action record-funnel --period 2025-W24 --visits 1200 --signups 84 --demos 12 --trials 6 --paid 2
    python funnel_calculator.py --action funnel-report --period 2025-W24
    python funnel_calculator.py --action compare-periods --period1 2025-W23 --period2 2025-W24
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, log_task

STAGES = ["Visits", "Signups", "Demos", "Trials", "Paid"]


def record_funnel(args):
    row = {
        "Period":   args.period or datetime.now().strftime("%Y-W%W"),
        "Visits":   args.visits or 0,
        "Signups":  args.signups or 0,
        "Demos":    args.demos or 0,
        "Trials":   args.trials or 0,
        "Paid":     args.paid or 0,
        "Date":     datetime.now().strftime("%Y-%m-%d"),
    }
    add_row("funnel_metrics", row)
    print(f"🔄 Funnel recorded for {row['Period']}")
    prev = None
    for stage in STAGES:
        val = row[stage]
        conv = f" ({val/prev*100:.1f}%)" if prev and prev > 0 else ""
        print(f"   {stage}: {val}{conv}")
        prev = val
    log_task("Analytics", f"Funnel: {row['Period']}", "Complete", "P2",
             f"V:{row['Visits']} S:{row['Signups']} D:{row['Demos']} T:{row['Trials']} P:{row['Paid']}")


def funnel_report(args):
    period = args.period or datetime.now().strftime("%Y-W%W")
    items = query_db("funnel_metrics", filter={
        "property": "Period", "title": {"equals": period}
    })
    print("=" * 65)
    print(f"  🔄 FUNNEL REPORT — {period}")
    print("=" * 65)
    if not items:
        print(f"\n  No funnel data for {period}."); return
    item = items[0]

    prev = None
    for stage in STAGES:
        val = int(item.get(stage, 0) or 0)
        conv = f" ({val/prev*100:.1f}% conversion)" if prev and prev > 0 else ""
        bar = "█" * max(1, int(val / max(int(item.get("Visits", 1) or 1), 1) * 40))
        print(f"\n  {stage:>8}: {val:>6}{conv}")
        print(f"           {bar}")
        prev = val

    visits = int(item.get("Visits", 0) or 0)
    paid = int(item.get("Paid", 0) or 0)
    overall = (paid / visits * 100) if visits > 0 else 0
    print(f"\n{'─' * 65}")
    print(f"  Overall conversion (Visit → Paid): {overall:.2f}%")
    log_task("Analytics", f"Funnel report {period}", "Complete", "P2")


def compare_periods(args):
    periods = [args.period1, args.period2]
    data = {}
    for p in periods:
        items = query_db("funnel_metrics", filter={
            "property": "Period", "title": {"equals": p}
        })
        if items:
            data[p] = items[0]

    print("=" * 65)
    print(f"  🔄 FUNNEL COMPARISON: {args.period1} vs {args.period2}")
    print("=" * 65)
    if len(data) < 2:
        missing = [p for p in periods if p not in data]
        print(f"\n  Missing data for: {', '.join(missing)}"); return

    a, b = data[args.period1], data[args.period2]
    print(f"\n  {'Stage':>8} | {args.period1:>10} | {args.period2:>10} | {'Change':>10}")
    print(f"  {'-' * 50}")
    for stage in STAGES:
        va = int(a.get(stage, 0) or 0)
        vb = int(b.get(stage, 0) or 0)
        diff = vb - va
        pct = (diff / va * 100) if va > 0 else 0
        icon = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        print(f"  {stage:>8} | {va:>10} | {vb:>10} | {icon} {diff:+d} ({pct:+.1f}%)")

    print(f"\n{'─' * 65}")
    log_task("Analytics", f"Funnel compare {args.period1} vs {args.period2}", "Complete", "P3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Funnel Analytics")
    parser.add_argument("--action", required=True,
                        choices=["record-funnel", "funnel-report", "compare-periods"])
    parser.add_argument("--period")
    parser.add_argument("--period1")
    parser.add_argument("--period2")
    parser.add_argument("--visits", type=int, default=0)
    parser.add_argument("--signups", type=int, default=0)
    parser.add_argument("--demos", type=int, default=0)
    parser.add_argument("--trials", type=int, default=0)
    parser.add_argument("--paid", type=int, default=0)
    args = parser.parse_args()
    {"record-funnel": record_funnel, "funnel-report": funnel_report,
     "compare-periods": compare_periods}[args.action](args)
