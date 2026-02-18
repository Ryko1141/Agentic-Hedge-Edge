#!/usr/bin/env python3
"""
campaign_tracker.py — Marketing Agent Ad Campaign Management

Track marketing campaigns, update metrics, and generate performance reports.

Usage:
    python campaign_tracker.py --action create-campaign --name "Q1 Reddit Ads" --channel Reddit --budget 500
    python campaign_tracker.py --action update-metrics --name "Q1 Reddit Ads" --impressions 50000 --clicks 1200 --leads 45 --conversions 8
    python campaign_tracker.py --action campaign-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def create_campaign(args):
    """Create a new marketing campaign."""
    row = {
        "Campaign Name": args.name,
        "Channel":       args.channel or "Meta Ads",
        "Status":        "Planning",
        "Budget":        args.budget or 0,
        "Spend":         0,
        "Impressions":   0,
        "Clicks":        0,
        "Leads":         0,
        "Conversions":   0,
        "CAC":           0,
        "Start Date":    datetime.now().strftime("%Y-%m-%d"),
    }
    add_row("campaigns", row)
    print(f"✅ Campaign created: {args.name}")
    print(f"   Channel: {row['Channel']} | Budget: ${row['Budget']:,.0f}")
    log_task("Marketing", f"Campaign created: {args.name}", "Complete", "P2",
             f"Channel: {row['Channel']}, Budget: ${row['Budget']}")


def update_metrics(args):
    """Update campaign performance metrics."""
    campaigns = query_db("campaigns", filter={
        "property": "Campaign Name", "title": {"equals": args.name}
    })
    if not campaigns:
        print(f"❌ Campaign not found: {args.name}")
        return
    c = campaigns[0]
    spend = args.spend or c.get("Spend") or 0
    conversions = args.conversions or 0
    cac = spend / conversions if conversions > 0 else 0

    updates = {}
    if args.impressions: updates["Impressions"] = args.impressions
    if args.clicks: updates["Clicks"] = args.clicks
    if args.leads: updates["Leads"] = args.leads
    if args.conversions: updates["Conversions"] = conversions
    if args.spend: updates["Spend"] = spend
    if conversions > 0: updates["CAC"] = round(cac, 2)
    updates["Status"] = "Active"

    update_row(c["_id"], "campaigns", updates)
    ctr = (args.clicks / args.impressions * 100) if args.impressions and args.clicks else 0
    print(f"✅ {args.name} metrics updated")
    print(f"   Impressions: {args.impressions or '–'} | Clicks: {args.clicks or '–'} | CTR: {ctr:.2f}%")
    print(f"   Leads: {args.leads or '–'} | Conversions: {conversions} | CAC: ${cac:.2f}")
    log_task("Marketing", f"Metrics update: {args.name}", "Complete", "P2",
             f"Conversions: {conversions}, CAC: ${cac:.2f}")


def campaign_report(args):
    """Generate campaign performance report."""
    campaigns = query_db("campaigns")
    print("=" * 70)
    print("  📢 CAMPAIGN PERFORMANCE REPORT")
    print("=" * 70)
    if not campaigns:
        print("\n  No campaigns recorded.")
        return

    total_spend, total_conv = 0, 0
    for c in sorted(campaigns, key=lambda x: -(x.get("Conversions") or 0)):
        imp = c.get("Impressions") or 0
        clicks = c.get("Clicks") or 0
        leads = c.get("Leads") or 0
        conv = c.get("Conversions") or 0
        spend = c.get("Spend") or 0
        ctr = clicks / imp * 100 if imp else 0
        cac = spend / conv if conv else 0
        status = c.get("Status", "?")
        print(f"\n  {c.get('Campaign Name', '?')} [{status}]")
        print(f"    Channel: {c.get('Channel', '?')} | Budget: ${c.get('Budget', 0):,.0f} | Spend: ${spend:,.0f}")
        print(f"    {imp:,} imp → {clicks:,} clicks ({ctr:.1f}%) → {leads} leads → {conv} conversions")
        if conv > 0:
            print(f"    CAC: ${cac:.2f}")
        total_spend += spend
        total_conv += conv

    avg_cac = total_spend / total_conv if total_conv else 0
    print(f"\n{'─' * 70}")
    print(f"  Total spend: ${total_spend:,.0f} | Conversions: {total_conv} | Avg CAC: ${avg_cac:.2f}")
    log_task("Marketing", "Campaign report", "Complete", "P3",
             f"${total_spend:,.0f} spent, {total_conv} conversions, ${avg_cac:.2f} CAC")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campaign Management")
    parser.add_argument("--action", required=True,
                        choices=["create-campaign", "update-metrics", "campaign-report"])
    parser.add_argument("--name", help="Campaign name")
    parser.add_argument("--channel", default="Meta Ads")
    parser.add_argument("--budget", type=float, default=0)
    parser.add_argument("--spend", type=float, default=0)
    parser.add_argument("--impressions", type=int)
    parser.add_argument("--clicks", type=int)
    parser.add_argument("--leads", type=int)
    parser.add_argument("--conversions", type=int)
    args = parser.parse_args()
    {"create-campaign": create_campaign, "update-metrics": update_metrics,
     "campaign-report": campaign_report}[args.action](args)
