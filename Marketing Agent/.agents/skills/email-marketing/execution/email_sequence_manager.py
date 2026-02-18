#!/usr/bin/env python3
"""
email_sequence_manager.py — Marketing Agent Email Marketing

Manage email drip sequences and track engagement metrics.

Usage:
    python email_sequence_manager.py --action create-sequence --name "Welcome Flow" --type Welcome --emails 5
    python email_sequence_manager.py --action update-metrics --name "Welcome Flow" --open-rate 0.42 --click-rate 0.12 --conversion-rate 0.05
    python email_sequence_manager.py --action sequence-report
"""

import sys, os, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def create_sequence(args):
    """Create a new email sequence."""
    row = {
        "Sequence Name":  args.name,
        "Type":           args.type or "Nurture",
        "Status":         "Draft",
        "Emails Count":   args.emails or 5,
        "Open Rate":      0,
        "Click Rate":     0,
        "Conversion Rate":0,
        "Subscribers":    0,
        "Last Updated":   datetime.now().strftime("%Y-%m-%d"),
    }
    add_row("email_sequences", row)
    print(f"✅ Sequence created: {args.name} ({row['Type']}, {row['Emails Count']} emails)")
    log_task("Marketing", f"Email sequence: {args.name}", "Complete", "P2",
             f"Type: {row['Type']}, {row['Emails Count']} emails")


def update_metrics(args):
    """Update sequence engagement metrics."""
    seqs = query_db("email_sequences", filter={
        "property": "Sequence Name", "title": {"equals": args.name}
    })
    if not seqs:
        print(f"❌ Sequence not found: {args.name}")
        return
    s = seqs[0]
    updates = {"Last Updated": datetime.now().strftime("%Y-%m-%d"), "Status": "Active"}
    if args.open_rate: updates["Open Rate"] = args.open_rate
    if args.click_rate: updates["Click Rate"] = args.click_rate
    if args.conversion_rate: updates["Conversion Rate"] = args.conversion_rate
    if args.subscribers: updates["Subscribers"] = args.subscribers

    update_row(s["_id"], "email_sequences", updates)
    print(f"✅ {args.name} metrics updated")
    print(f"   Open: {args.open_rate or 0:.0%} | Click: {args.click_rate or 0:.0%} | Conv: {args.conversion_rate or 0:.0%}")
    log_task("Marketing", f"Email metrics: {args.name}", "Complete", "P3")


def sequence_report(args):
    """Print all email sequences with performance."""
    seqs = query_db("email_sequences")
    print("=" * 65)
    print("  📧 EMAIL SEQUENCE REPORT")
    print("=" * 65)
    if not seqs:
        print("\n  No sequences recorded.")
        return
    for s in seqs:
        o = s.get("Open Rate") or 0
        c = s.get("Click Rate") or 0
        cv = s.get("Conversion Rate") or 0
        status = s.get("Status", "?")
        print(f"\n  {s.get('Sequence Name', '?')} [{status}]")
        print(f"    Type: {s.get('Type', '?')} | Emails: {s.get('Emails Count', '?')} | Subs: {s.get('Subscribers', 0)}")
        print(f"    Open: {o:.0%} | Click: {c:.0%} | Conv: {cv:.0%}")
    log_task("Marketing", "Email sequence report", "Complete", "P3",
             f"{len(seqs)} sequences tracked")


def send_nurture(args):
    """Process new signups + send drip emails via Resend."""
    from shared.email_nurture import setup_audience, process_new_signups, send_drips, show_stats
    # Always ensure audience exists
    setup_audience()
    # Process new signups from last 24h
    process_new_signups(since_minutes=1440)
    # Send any pending drip emails
    send_drips()
    # Show stats
    show_stats()
    log_task("Marketing", "Waitlist nurture run", "Complete", "P1",
             "Processed new signups and sent drip emails via Resend")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Email Sequence Management")
    parser.add_argument("--action", required=True,
                        choices=["create-sequence", "update-metrics", "sequence-report", "send-nurture"])
    parser.add_argument("--name")
    parser.add_argument("--type", choices=["Welcome", "Nurture", "Re-engagement", "Onboarding", "Launch"])
    parser.add_argument("--emails", type=int, default=5)
    parser.add_argument("--open-rate", type=float, dest="open_rate")
    parser.add_argument("--click-rate", type=float, dest="click_rate")
    parser.add_argument("--conversion-rate", type=float, dest="conversion_rate")
    parser.add_argument("--subscribers", type=int)
    args = parser.parse_args()
    {"create-sequence": create_sequence, "update-metrics": update_metrics,
     "sequence-report": sequence_report, "send-nurture": send_nurture}[args.action](args)
