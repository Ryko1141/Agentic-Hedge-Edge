#!/usr/bin/env python3
"""
demo_tracker.py — Sales Agent Demo Management

Logs demos and tracks conversion rates.

Usage:
    python demo_tracker.py --action log-demo --name "John Doe" --outcome Converted --plan Pro --duration 25
    python demo_tracker.py --action demo-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, log_task


def log_demo(args):
    """Log a completed demo."""
    row = {
        "Lead Name":     args.name,
        "Date":          datetime.now().strftime("%Y-%m-%d"),
        "Duration Min":  args.duration or 30,
        "Outcome":       args.outcome or "Follow Up",
        "Objections":    args.objections or "",
        "Next Steps":    args.next_steps or "",
        "Plan Selected": args.plan or "None",
    }
    add_row("demo_log", row)
    print(f"✅ Demo logged: {args.name}")
    print(f"   Outcome: {row['Outcome']} | Duration: {row['Duration Min']}min | Plan: {row['Plan Selected']}")
    log_task("Sales", f"Demo logged: {args.name}", "Complete", "P2",
             f"Outcome: {row['Outcome']}, Plan: {row['Plan Selected']}")


def demo_report(args):
    """Show demo conversion rates."""
    demos = query_db("demo_log")
    total = len(demos)
    outcomes = {}
    for d in demos:
        o = d.get("Outcome", "Unknown")
        outcomes[o] = outcomes.get(o, 0) + 1

    print("=" * 60)
    print("  🎬 DEMO PERFORMANCE REPORT")
    print("=" * 60)
    if total == 0:
        print("\n  No demos recorded yet.")
        return
    for outcome, count in sorted(outcomes.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "█" * int(pct / 5)
        print(f"\n  {outcome}: {count} ({pct:.0f}%) {bar}")
    conv = outcomes.get("Converted", 0)
    print(f"\n{'─' * 60}")
    print(f"  Total: {total} demos | Conversion rate: {conv/total*100:.1f}%")
    log_task("Sales", "Demo report", "Complete", "P3",
             f"{total} demos, {conv/total*100:.1f}% conversion")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo Management")
    parser.add_argument("--action", required=True, choices=["log-demo", "demo-report"])
    parser.add_argument("--name", help="Lead name")
    parser.add_argument("--outcome", choices=["Converted", "Follow Up", "Not Interested", "No Show"])
    parser.add_argument("--plan", choices=["Starter", "Pro", "Hedger", "None"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--objections", default="")
    parser.add_argument("--next-steps", default="", dest="next_steps")
    args = parser.parse_args()
    {"log-demo": log_demo, "demo-report": demo_report}[args.action](args)
