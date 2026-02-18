#!/usr/bin/env python3
"""
proposal_manager.py — Sales Agent Proposal Generation

Creates and tracks proposals with ROI projections.

Usage:
    python proposal_manager.py --action create-proposal --name "John Doe" --plan Pro --value 360
    python proposal_manager.py --action track-proposals
"""

import sys, os, argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, log_task


PLAN_PRICES = {"Starter": 29, "Pro": 30, "Hedger": 75, "Custom": 0}


def create_proposal(args):
    """Create a proposal with ROI calculation."""
    monthly = PLAN_PRICES.get(args.plan, 0) or args.value
    annual = monthly * 12
    # Avg challenge fee $200, 3 challenges/mo, hedge saves ~85% of losses
    avg_savings = 200 * 3 * 0.85  # $510/mo
    roi_pct = ((avg_savings - monthly) / monthly * 100) if monthly > 0 else 0
    roi_text = f"Monthly cost: ${monthly} | Avg hedge savings: ${avg_savings:.0f}/mo | ROI: {roi_pct:.0f}%"

    row = {
        "Title":          f"Proposal — {args.name} ({args.plan})",
        "Lead Name":      args.name,
        "Plan":           args.plan,
        "Value":          annual,
        "Status":         "Draft",
        "Sent Date":      datetime.now().strftime("%Y-%m-%d"),
        "Expiry Date":    (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        "ROI Projection": roi_text,
    }
    add_row("proposals", row)
    print(f"✅ Proposal created: {args.name}")
    print(f"   Plan: {args.plan} | Annual value: ${annual}")
    print(f"   {roi_text}")
    log_task("Sales", f"Proposal: {args.name}", "Complete", "P2", roi_text)


def track_proposals(args):
    """Track all proposals by status."""
    proposals = query_db("proposals")
    by_status = {}
    for p in proposals:
        s = p.get("Status", "Unknown")
        if s not in by_status:
            by_status[s] = []
        by_status[s].append(p)

    print("=" * 60)
    print("  📝 PROPOSAL TRACKER")
    print("=" * 60)
    total_value = sum(p.get("Value") or 0 for p in proposals)
    for status in ["Draft", "Sent", "Accepted", "Rejected"]:
        items = by_status.get(status, [])
        if items:
            val = sum(p.get("Value") or 0 for p in items)
            print(f"\n  {status} ({len(items)} | ${val:,.0f})")
            for p in items:
                print(f"    • {p.get('Lead Name', '?')} — {p.get('Plan', '?')} (${p.get('Value', 0):,.0f})")
    accepted = sum(p.get("Value") or 0 for p in by_status.get("Accepted", []))
    print(f"\n{'─' * 60}")
    print(f"  Total pipeline: ${total_value:,.0f} | Won: ${accepted:,.0f}")
    log_task("Sales", "Proposal tracking", "Complete", "P3",
             f"{len(proposals)} proposals, ${total_value:,.0f} pipeline")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proposal Management")
    parser.add_argument("--action", required=True, choices=["create-proposal", "track-proposals"])
    parser.add_argument("--name", help="Lead name")
    parser.add_argument("--plan", choices=["Starter", "Pro", "Hedger", "Custom"], default="Pro")
    parser.add_argument("--value", type=float, default=0)
    args = parser.parse_args()
    {"create-proposal": create_proposal, "track-proposals": track_proposals}[args.action](args)
