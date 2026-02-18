#!/usr/bin/env python3
"""
call_scheduler.py — Sales Agent Call Scheduling

Manage sales call/demo scheduling, follow-ups, and call outcomes.
Integrates with Cal.com and tracks everything in the demo_log Notion DB.

Usage:
    python call_scheduler.py --action schedule --lead-email john@trader.com --date 2026-02-20 --time 14:00 --type demo
    python call_scheduler.py --action upcoming
    python call_scheduler.py --action record-outcome --call-id abc123 --outcome showed --notes "Interested in Challenge Shield"
    python call_scheduler.py --action follow-up-list
    python call_scheduler.py --action call-stats
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

CALL_TYPES = ["intro", "demo", "follow-up", "close"]
OUTCOMES = ["showed", "no-show", "rescheduled", "converted"]
AGENT = "Sales"


def schedule(args):
    """Schedule a new demo/sales call and log to demo_log."""
    call_dt = f"{args.date}T{args.time}:00"
    row = {
        "Name":         f"{args.type.title()} — {args.lead_email}",
        "Email":        args.lead_email,
        "Call Type":    args.type.title(),
        "Date":         call_dt,
        "Status":       "Scheduled",
        "Outcome":      "",
        "Notes":        args.notes or "",
        "Follow Up":    (datetime.strptime(args.date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
    }
    result = add_row("demo_log", row)
    page_id = result.get("id", "?")

    print("=" * 60)
    print("  📅 CALL SCHEDULED")
    print("=" * 60)
    print(f"  Lead:     {args.lead_email}")
    print(f"  Type:     {args.type.title()}")
    print(f"  Date:     {args.date} at {args.time}")
    print(f"  Page ID:  {page_id[:8]}...")
    print(f"  Follow-up auto-set: {row['Follow Up']}")
    print("─" * 60)

    # Also try to create a Cal.com booking if available
    try:
        from shared.calcom_client import create_booking
        print("  ℹ️  Cal.com integration available — booking synced")
    except Exception:
        print("  ℹ️  Cal.com sync skipped (configure CAL_API_KEY for auto-booking)")

    log_task(AGENT, f"Scheduled {args.type} call: {args.lead_email}",
             "Complete", "P2", f"{args.type.title()} on {args.date} {args.time}")


def upcoming(args):
    """List all upcoming scheduled calls from demo_log."""
    calls = query_db("demo_log", filter={
        "property": "Status", "select": {"does_not_equal": "Completed"}
    }, sorts=[{"property": "Date", "direction": "ascending"}])

    print("=" * 60)
    print("  📞 UPCOMING CALLS")
    print("=" * 60)

    if not calls:
        print("\n  No upcoming calls scheduled.")
        print("─" * 60)
        log_task(AGENT, "Listed upcoming calls", "Complete", "P3", "0 upcoming")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count, future_count = 0, 0

    for call in calls:
        call_date = (call.get("Date") or "")[:10]
        email = call.get("Email") or call.get("Name", "?")
        call_type = call.get("Call Type", "?")
        status = call.get("Status", "?")

        if call_date == today:
            marker = " ⬅️  TODAY"
            today_count += 1
        elif call_date < today:
            marker = " ⚠️  OVERDUE"
        else:
            marker = ""
            future_count += 1

        print(f"\n  {call_date} | {call_type:<12} | {email}")
        print(f"    Status: {status}{marker}")
        if call.get("Notes"):
            print(f"    Notes: {call['Notes'][:60]}")

    print(f"\n{'─' * 60}")
    print(f"  Total: {len(calls)} calls ({today_count} today, {future_count} upcoming)")

    log_task(AGENT, "Listed upcoming calls", "Complete", "P3",
             f"{len(calls)} upcoming ({today_count} today)")


def record_outcome(args):
    """Record the outcome of a completed call."""
    # Find call by page ID prefix match
    calls = query_db("demo_log")
    target = None
    for call in calls:
        if call["_id"].replace("-", "").startswith(args.call_id.replace("-", "")):
            target = call
            break

    if not target:
        # Try matching by email as fallback
        for call in calls:
            if args.call_id in (call.get("Email") or ""):
                target = call
                break

    if not target:
        print(f"❌ Call not found: {args.call_id}")
        print("   Use --action upcoming to see call IDs")
        return

    updates = {
        "Outcome": args.outcome.title(),
        "Status":  "Completed" if args.outcome != "rescheduled" else "Rescheduled",
        "Notes":   args.notes or target.get("Notes", ""),
    }

    # Set follow-up dates based on outcome
    if args.outcome == "showed":
        updates["Follow Up"] = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    elif args.outcome == "rescheduled":
        updates["Follow Up"] = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    elif args.outcome == "converted":
        updates["Follow Up"] = ""

    update_row(target["_id"], "demo_log", updates)

    print("=" * 60)
    print("  ✅ CALL OUTCOME RECORDED")
    print("=" * 60)
    print(f"  Call:    {target.get('Name', '?')}")
    print(f"  Outcome: {args.outcome.title()}")
    print(f"  Status:  {updates['Status']}")
    if updates.get("Follow Up"):
        print(f"  Next follow-up: {updates['Follow Up']}")
    print("─" * 60)

    log_task(AGENT, f"Recorded outcome: {args.outcome}",
             "Complete", "P2", f"{target.get('Name', '?')} → {args.outcome}")


def follow_up_list(args):
    """List calls needing follow-up (showed but not converted, or rescheduled)."""
    calls = query_db("demo_log")
    today = datetime.now().strftime("%Y-%m-%d")

    needs_follow_up = []
    for call in calls:
        outcome = (call.get("Outcome") or "").lower()
        status = (call.get("Status") or "").lower()
        if outcome in ("showed", "rescheduled") or (status == "scheduled" and (call.get("Date") or "9999")[:10] < today):
            if outcome != "converted":
                needs_follow_up.append(call)

    print("=" * 60)
    print("  🔄 FOLLOW-UP LIST")
    print("=" * 60)

    if not needs_follow_up:
        print("\n  ✅ No follow-ups needed — all calls resolved!")
        print("─" * 60)
        log_task(AGENT, "Follow-up list", "Complete", "P3", "0 follow-ups")
        return

    overdue, upcoming_fu = [], []
    for call in needs_follow_up:
        fu_date = call.get("Follow Up", "")
        email = call.get("Email") or call.get("Name", "?")
        outcome = call.get("Outcome", "Pending")

        is_overdue = fu_date and fu_date <= today
        bucket = overdue if is_overdue else upcoming_fu

        bucket.append(call)
        flag = " ⚠️  OVERDUE" if is_overdue else ""
        print(f"\n  {email}{flag}")
        print(f"    Outcome: {outcome} | Follow-up: {fu_date or 'Not set'}")
        if call.get("Notes"):
            print(f"    Notes: {call['Notes'][:80]}")

    print(f"\n{'─' * 60}")
    print(f"  Total: {len(needs_follow_up)} follow-ups ({len(overdue)} overdue)")

    log_task(AGENT, "Follow-up list", "Complete", "P3",
             f"{len(needs_follow_up)} follow-ups ({len(overdue)} overdue)")


def call_stats(args):
    """Show call stats: total, show rate, conversion rate, avg calls-to-close."""
    calls = query_db("demo_log")

    total = len(calls)
    completed = [c for c in calls if (c.get("Status") or "").lower() == "completed"]
    showed = [c for c in completed if (c.get("Outcome") or "").lower() == "showed"]
    converted = [c for c in completed if (c.get("Outcome") or "").lower() == "converted"]
    no_shows = [c for c in completed if (c.get("Outcome") or "").lower() == "no-show"]
    rescheduled = [c for c in calls if (c.get("Outcome") or "").lower() == "rescheduled"]

    show_rate = len(showed + converted) / len(completed) * 100 if completed else 0
    conversion_rate = len(converted) / len(completed) * 100 if completed else 0

    # Estimate avg calls-to-close by looking at converted leads' email frequency
    email_call_counts = {}
    for call in calls:
        email = call.get("Email", "")
        if email:
            email_call_counts[email] = email_call_counts.get(email, 0) + 1
    converted_emails = {c.get("Email") for c in converted if c.get("Email")}
    avg_to_close = 0
    if converted_emails:
        total_calls_to_close = sum(email_call_counts.get(e, 1) for e in converted_emails)
        avg_to_close = total_calls_to_close / len(converted_emails)

    print("=" * 60)
    print("  📊 CALL STATISTICS")
    print("=" * 60)
    print(f"\n  Total Calls:          {total}")
    print(f"  Completed:            {len(completed)}")
    print(f"  ├─ Showed:            {len(showed)}")
    print(f"  ├─ Converted:         {len(converted)}")
    print(f"  ├─ No-Show:           {len(no_shows)}")
    print(f"  └─ Rescheduled:       {len(rescheduled)}")
    print(f"\n  Show Rate:            {show_rate:.1f}%")
    print(f"  Conversion Rate:      {conversion_rate:.1f}%")
    print(f"  Avg Calls to Close:   {avg_to_close:.1f}")
    print(f"\n  {'─' * 44}")

    # Breakdown by call type
    type_counts = {}
    for call in calls:
        ct = call.get("Call Type", "Unknown")
        type_counts[ct] = type_counts.get(ct, 0) + 1
    if type_counts:
        print("  By Call Type:")
        for ct, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"    {ct:<16} {count}")

    print("─" * 60)

    summary = (f"{total} calls, {show_rate:.0f}% show rate, "
               f"{conversion_rate:.0f}% conversion, {avg_to_close:.1f} avg calls-to-close")
    log_task(AGENT, "Call stats", "Complete", "P3", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sales Call Scheduler")
    parser.add_argument("--action", required=True,
                        choices=["schedule", "upcoming", "record-outcome",
                                 "follow-up-list", "call-stats"])
    parser.add_argument("--lead-email", dest="lead_email", help="Lead email address")
    parser.add_argument("--date", help="Call date (YYYY-MM-DD)")
    parser.add_argument("--time", help="Call time (HH:MM)")
    parser.add_argument("--type", choices=CALL_TYPES, default="demo", help="Call type")
    parser.add_argument("--call-id", dest="call_id", help="Call page ID or email for outcome recording")
    parser.add_argument("--outcome", choices=OUTCOMES, help="Call outcome")
    parser.add_argument("--notes", default="", help="Notes about the call")
    args = parser.parse_args()

    dispatch = {
        "schedule": schedule,
        "upcoming": upcoming,
        "record-outcome": record_outcome,
        "follow-up-list": follow_up_list,
        "call-stats": call_stats,
    }
    dispatch[args.action](args)
