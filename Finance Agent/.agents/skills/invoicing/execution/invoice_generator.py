#!/usr/bin/env python3
"""
invoice_generator.py — Finance Agent Invoice Management

Generate and track invoices for enterprise clients and IB commission
payouts for Hedge Edge Ltd.

Usage:
    python invoice_generator.py --action create --client "Acme Corp" --amount 990.00 --description "Enterprise annual" --due-date 2026-03-15 --type enterprise
    python invoice_generator.py --action outstanding
    python invoice_generator.py --action mark-paid --invoice-id INV-2026-001 --payment-date 2026-03-10
    python invoice_generator.py --action overdue
    python invoice_generator.py --action invoice-stats
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Finance"

INVOICE_TYPES = ["subscription", "enterprise", "ib-payout", "consulting"]


def _parse_amount(row):
    val = row.get("Amount") or row.get("Value") or 0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _parse_date(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _generate_invoice_id():
    """Generate next sequential invoice ID: INV-YYYY-NNN."""
    now = datetime.now(timezone.utc)
    rows = query_db("expense_log")
    year_prefix = f"INV-{now.year}-"
    existing = [r.get("Name", "") for r in rows if (r.get("Name") or "").startswith(year_prefix)]
    seq = len(existing) + 1
    return f"{year_prefix}{seq:03d}"


def _get_invoices():
    """Get all invoice rows from expense_log (Type=Invoice or has INV- prefix)."""
    rows = query_db("expense_log")
    return [r for r in rows
            if (r.get("Type") or "").lower() == "invoice"
            or (r.get("Name") or "").startswith("INV-")]


def create(args):
    """Create a new invoice and add to expense_log as a receivable."""
    inv_id = _generate_invoice_id()
    now = datetime.now(timezone.utc)

    row = {
        "Name": inv_id,
        "Category": "Invoice",
        "Type": "Invoice",
        "Amount": -abs(args.amount),  # Negative = receivable
        "Vendor": args.client,
        "Description": args.description or "",
        "Status": "Unpaid",
        "Due_Date": args.due_date,
        "Invoice_Type": args.type,
        "Date": now.strftime("%Y-%m-%d"),
        "Notes": json.dumps({
            "client": args.client,
            "invoice_type": args.type,
            "created_at": now.isoformat(),
        }),
    }
    add_row("expense_log", row)

    print("=" * 60)
    print("  🧾 INVOICE CREATED")
    print("=" * 60)
    print(f"\n  Invoice ID:     {inv_id}")
    print(f"  Client:         {args.client}")
    print(f"  Amount:         £{args.amount:,.2f}")
    print(f"  Description:    {args.description or '—'}")
    print(f"  Type:           {args.type}")
    print(f"  Issue Date:     {now.strftime('%Y-%m-%d')}")
    print(f"  Due Date:       {args.due_date}")
    days_until = (_parse_date(args.due_date) - now.date()).days if _parse_date(args.due_date) else 0
    print(f"  Payment Terms:  Net {days_until} days")
    print(f"\n  ✅ Added to expense_log as receivable")
    print("─" * 60)

    log_task(AGENT, f"Created invoice {inv_id} for {args.client}",
             "Complete", "P1",
             f"amount=£{args.amount:,.2f}, type={args.type}, due={args.due_date}")


def outstanding(args):
    """List all unpaid invoices."""
    invoices = _get_invoices()
    unpaid = [r for r in invoices if (r.get("Status") or "").lower() in ("unpaid", "pending", "")]
    total = sum(abs(_parse_amount(r)) for r in unpaid)

    print("=" * 60)
    print("  📋 OUTSTANDING INVOICES")
    print("=" * 60)
    print(f"\n  {'ID':<16} {'Client':<18} {'Amount':>10} {'Due Date':>12} {'Days':>6}")
    print(f"  {'─' * 66}")

    today = datetime.now(timezone.utc).date()
    for r in sorted(unpaid, key=lambda x: x.get("Due_Date") or "9999"):
        inv_id = (r.get("Name") or "?")[:15]
        client = (r.get("Vendor") or "?")[:17]
        amt = abs(_parse_amount(r))
        due = r.get("Due_Date") or "—"
        due_date = _parse_date(due)
        days_left = (due_date - today).days if due_date else "?"
        overdue = "🔴" if isinstance(days_left, int) and days_left < 0 else ""
        print(f"  {inv_id:<16} {client:<18} £{amt:>8,.2f} {due:>12} {days_left:>5} {overdue}")

    print(f"  {'─' * 66}")
    print(f"  Total Outstanding: £{total:,.2f} across {len(unpaid)} invoice(s)")
    print("─" * 60)

    log_task(AGENT, f"Listed {len(unpaid)} outstanding invoices",
             "Complete", "P2",
             f"total=£{total:,.2f}")


def mark_paid(args):
    """Mark an invoice as paid."""
    invoices = _get_invoices()
    match = [r for r in invoices if args.invoice_id in (r.get("Name") or "")]

    if not match:
        print("=" * 60)
        print(f"  ❌ Invoice '{args.invoice_id}' not found")
        print("─" * 60)
        return

    row = match[0]
    page_id = row.get("id") or row.get("page_id")
    if page_id:
        update_row(page_id, {
            "Status": "Paid",
            "Notes": json.dumps({
                "paid_date": args.payment_date,
                "marked_at": datetime.now(timezone.utc).isoformat(),
            }),
        })

    amt = abs(_parse_amount(row))
    client = row.get("Vendor") or "?"

    print("=" * 60)
    print("  ✅ INVOICE MARKED PAID")
    print("=" * 60)
    print(f"\n  Invoice ID:    {args.invoice_id}")
    print(f"  Client:        {client}")
    print(f"  Amount:        £{amt:,.2f}")
    print(f"  Payment Date:  {args.payment_date}")

    due = row.get("Due_Date")
    if due and args.payment_date:
        due_d = _parse_date(due)
        pay_d = _parse_date(args.payment_date)
        if due_d and pay_d:
            days_diff = (pay_d - due_d).days
            if days_diff <= 0:
                print(f"  ✅ Paid {abs(days_diff)} day(s) early")
            else:
                print(f"  ⚠️  Paid {days_diff} day(s) late")
    print("─" * 60)

    log_task(AGENT, f"Marked {args.invoice_id} as paid",
             "Complete", "P1",
             f"amount=£{amt:,.2f}, client={client}, paid={args.payment_date}")


def overdue(args):
    """List overdue invoices with aging buckets (30/60/90 days)."""
    invoices = _get_invoices()
    unpaid = [r for r in invoices if (r.get("Status") or "").lower() in ("unpaid", "pending", "")]
    today = datetime.now(timezone.utc).date()

    buckets = {"0-30": [], "31-60": [], "61-90": [], "90+": []}
    total_overdue = 0.0

    for r in unpaid:
        due = _parse_date(r.get("Due_Date") or "")
        if not due or due >= today:
            continue
        days_past = (today - due).days
        amt = abs(_parse_amount(r))
        total_overdue += amt

        entry = {**r, "_days_past": days_past, "_amount": amt}
        if days_past <= 30:
            buckets["0-30"].append(entry)
        elif days_past <= 60:
            buckets["31-60"].append(entry)
        elif days_past <= 90:
            buckets["61-90"].append(entry)
        else:
            buckets["90+"].append(entry)

    print("=" * 60)
    print("  ⏰ OVERDUE INVOICES — AGING REPORT")
    print("=" * 60)

    for bucket_label, items in buckets.items():
        bucket_total = sum(i["_amount"] for i in items)
        icon = {"0-30": "🟡", "31-60": "🟠", "61-90": "🔴", "90+": "🚨"}[bucket_label]
        print(f"\n  {icon} {bucket_label} DAYS OVERDUE — £{bucket_total:,.2f}")
        if items:
            print(f"  {'─' * 50}")
            for i in items:
                inv_id = (i.get("Name") or "?")[:15]
                client = (i.get("Vendor") or "?")[:17]
                print(f"    {inv_id:<16} {client:<18} £{i['_amount']:>8,.2f}  ({i['_days_past']}d)")
        else:
            print(f"    None")

    print(f"\n  {'─' * 50}")
    total_items = sum(len(v) for v in buckets.values())
    print(f"  Total Overdue: £{total_overdue:,.2f} across {total_items} invoice(s)")

    if total_items > 0 and total_overdue > 0:
        severe = len(buckets["61-90"]) + len(buckets["90+"])
        if severe > 0:
            print(f"\n  🚨 {severe} invoice(s) critically overdue (60+ days)")
            print(f"     Recommend: escalate collection efforts immediately")
    else:
        print(f"\n  ✅ No overdue invoices")
    print("─" * 60)

    log_task(AGENT, f"Overdue invoice report",
             "Complete", "P2",
             f"overdue={total_items}, total=£{total_overdue:,.2f}")


def invoice_stats(args):
    """Invoice statistics: total issued, collected, outstanding, avg payment time."""
    invoices = _get_invoices()
    today = datetime.now(timezone.utc).date()

    total_issued = len(invoices)
    total_issued_amt = sum(abs(_parse_amount(r)) for r in invoices)

    paid = [r for r in invoices if (r.get("Status") or "").lower() == "paid"]
    unpaid = [r for r in invoices if (r.get("Status") or "").lower() != "paid"]

    collected_amt = sum(abs(_parse_amount(r)) for r in paid)
    outstanding_amt = sum(abs(_parse_amount(r)) for r in unpaid)

    # Average days to payment (for paid invoices)
    payment_days = []
    for r in paid:
        issue = _parse_date(r.get("Date") or "")
        notes = r.get("Notes") or ""
        try:
            n = json.loads(notes)
            pay = _parse_date(n.get("paid_date") or "")
        except Exception:
            pay = None
        if issue and pay:
            payment_days.append((pay - issue).days)

    avg_days = sum(payment_days) / len(payment_days) if payment_days else 0
    collection_rate = (collected_amt / total_issued_amt * 100) if total_issued_amt > 0 else 0

    print("=" * 60)
    print("  📊 INVOICE STATISTICS")
    print("=" * 60)

    print(f"\n  VOLUME")
    print(f"  {'─' * 40}")
    print(f"    Total Invoices Issued:    {total_issued:>10}")
    print(f"    Paid:                     {len(paid):>10}")
    print(f"    Outstanding:              {len(unpaid):>10}")

    print(f"\n  AMOUNTS")
    print(f"  {'─' * 40}")
    print(f"    Total Issued:             £{total_issued_amt:>10,.2f}")
    print(f"    Total Collected:          £{collected_amt:>10,.2f}")
    print(f"    Outstanding:              £{outstanding_amt:>10,.2f}")

    print(f"\n  PERFORMANCE")
    print(f"  {'─' * 40}")
    print(f"    Collection Rate:          {collection_rate:>10.1f}%")
    print(f"    Avg Days to Payment:      {avg_days:>10.1f}")
    if avg_days <= 30:
        print(f"    ✅ Within standard Net-30 terms")
    elif avg_days <= 45:
        print(f"    🟡 Slightly above target — consider follow-up process")
    else:
        print(f"    🔴 Slow collections — implement reminders at 7/14/28 days")

    if collection_rate < 85:
        print(f"\n  ⚠️  Collection rate below 85% target")
    else:
        print(f"\n  ✅ Healthy collection rate")
    print("─" * 60)

    log_task(AGENT, "Invoice statistics report",
             "Complete", "P2",
             f"issued={total_issued}, collected=£{collected_amt:,.2f}, "
             f"rate={collection_rate:.1f}%, avg_days={avg_days:.0f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Invoice Generator — Finance Agent")
    p.add_argument("--action", required=True,
                   choices=["create", "outstanding", "mark-paid", "overdue", "invoice-stats"])
    p.add_argument("--client", help="Client / company name")
    p.add_argument("--amount", type=float, help="Invoice amount in GBP")
    p.add_argument("--description", help="Invoice description")
    p.add_argument("--due-date", help="Payment due date (YYYY-MM-DD)")
    p.add_argument("--type", choices=INVOICE_TYPES, help="Invoice type")
    p.add_argument("--invoice-id", help="Invoice ID for mark-paid")
    p.add_argument("--payment-date", help="Date payment received (YYYY-MM-DD)")

    args = p.parse_args()
    actions = {
        "create": create,
        "outstanding": outstanding,
        "mark-paid": mark_paid,
        "overdue": overdue,
        "invoice-stats": invoice_stats,
    }
    actions[args.action](args)
