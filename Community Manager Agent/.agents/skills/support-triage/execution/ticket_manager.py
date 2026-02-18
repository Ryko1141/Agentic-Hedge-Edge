#!/usr/bin/env python3
"""
ticket_manager.py — Community Manager Agent Support Triage

Create, resolve, and report on support tickets from community channels.

Usage:
    python ticket_manager.py --action create-ticket --title "Can't connect MetaTrader to Hedge Edge" --channel Discord --priority P1
    python ticket_manager.py --action resolve-ticket --title "Can't connect..." --resolution "Updated MT5 bridge docs"
    python ticket_manager.py --action ticket-report
    python ticket_manager.py --action overdue --days 3
"""

import sys, os, argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def create_ticket(args):
    row = {
        "Ticket":     args.title,
        "Status":     "Open",
        "Priority":   args.priority or "P2",
        "Channel":    args.channel or "Discord",
        "Created":    datetime.now().strftime("%Y-%m-%d"),
        "User":       args.user or "",
        "Category":   args.category or "Support",
        "Resolution": "",
    }
    add_row("support_tickets", row)
    print(f"🎫 Ticket created: {args.title}")
    print(f"   Priority: {row['Priority']} | Channel: {row['Channel']}")
    log_task("Community", f"Ticket: {args.title}", "Complete", "P1")


def resolve_ticket(args):
    items = query_db("support_tickets", filter={
        "property": "Ticket", "title": {"equals": args.title}
    })
    if not items:
        print(f"❌ Ticket not found: {args.title}"); return
    item = items[0]
    updates = {
        "Status":     "Resolved",
        "Resolution": args.resolution or "Resolved",
        "Resolved":   datetime.now().strftime("%Y-%m-%d"),
    }
    update_row(item["_id"], "support_tickets", updates)
    print(f"✅ Resolved: {args.title}")
    if args.resolution: print(f"   Resolution: {args.resolution}")
    # Calculate resolution time
    created = item.get("Created", "")
    if created:
        try:
            days = (datetime.now() - datetime.strptime(created, "%Y-%m-%d")).days
            print(f"   Resolution time: {days} day(s)")
        except: pass
    log_task("Community", f"Resolved: {args.title}", "Complete", "P2")


def ticket_report(args):
    items = query_db("support_tickets")
    print("=" * 65)
    print("  🎫 SUPPORT TICKET REPORT")
    print("=" * 65)
    if not items:
        print("\n  No tickets."); return

    open_tickets  = [t for t in items if t.get("Status") != "Resolved"]
    resolved      = [t for t in items if t.get("Status") == "Resolved"]

    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    open_tickets.sort(key=lambda x: priority_order.get(x.get("Priority", "P2"), 9))

    if open_tickets:
        print(f"\n  OPEN ({len(open_tickets)})")
        for t in open_tickets:
            icon = "🔴" if t.get("Priority") in ("P0", "P1") else "🟡"
            print(f"    {icon} [{t.get('Priority', '?')}] {t.get('Ticket', '?')}")
            print(f"       Channel: {t.get('Channel', '?')} | Created: {t.get('Created', '?')}")

    if resolved:
        print(f"\n  RECENTLY RESOLVED ({len(resolved)})")
        resolved.sort(key=lambda x: x.get("Resolved", ""), reverse=True)
        for t in resolved[:5]:
            print(f"    ✅ {t.get('Ticket', '?')} — {t.get('Resolved', '?')}")
        if len(resolved) > 5:
            print(f"    ... and {len(resolved) - 5} more")

    print(f"\n{'─' * 65}")
    critical = sum(1 for t in open_tickets if t.get("Priority") in ("P0", "P1"))
    print(f"  Total: {len(items)} | Open: {len(open_tickets)} | Critical: {critical} | Resolved: {len(resolved)}")
    log_task("Community", "Ticket report", "Complete", "P3",
             f"{len(open_tickets)} open, {critical} critical")


def overdue(args):
    """Show tickets open longer than N days."""
    cutoff = (datetime.now() - timedelta(days=args.days or 3)).strftime("%Y-%m-%d")
    items = query_db("support_tickets", filter={
        "and": [
            {"property": "Status", "select": {"does_not_equal": "Resolved"}},
            {"property": "Created", "date": {"on_or_before": cutoff}},
        ]
    })
    print("=" * 65)
    print(f"  ⏰ OVERDUE TICKETS (>{args.days or 3} days)")
    print("=" * 65)
    if not items:
        print(f"\n  No tickets overdue beyond {args.days or 3} days. 🎉"); return

    for t in items:
        try:
            age = (datetime.now() - datetime.strptime(t.get("Created", ""), "%Y-%m-%d")).days
        except:
            age = "?"
        print(f"\n  🔴 [{t.get('Priority', '?')}] {t.get('Ticket', '?')}")
        print(f"     Age: {age} days | Channel: {t.get('Channel', '?')}")

    print(f"\n{'─' * 65}")
    print(f"  {len(items)} overdue ticket(s)")
    log_task("Community", "Overdue check", "Complete", "P2",
             f"{len(items)} overdue tickets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Support Ticket Management")
    parser.add_argument("--action", required=True,
                        choices=["create-ticket", "resolve-ticket", "ticket-report", "overdue"])
    parser.add_argument("--title")
    parser.add_argument("--priority", default="P2")
    parser.add_argument("--channel", default="Discord")
    parser.add_argument("--status")
    parser.add_argument("--resolution", default="")
    parser.add_argument("--user", default="")
    parser.add_argument("--category", default="Support")
    parser.add_argument("--days", type=int, default=3)
    args = parser.parse_args()
    {"create-ticket": create_ticket, "resolve-ticket": resolve_ticket,
     "ticket-report": ticket_report, "overdue": overdue}[args.action](args)
