#!/usr/bin/env python3
"""
report_automator.py — Analytics Agent Reporting Automation

Automate recurring reports (daily digest, weekly report, monthly review)
for Hedge Edge prop-firm hedging software.

Usage:
    python report_automator.py --action daily-digest
    python report_automator.py --action weekly-report
    python report_automator.py --action monthly-review
    python report_automator.py --action schedule-report --type weekly --recipients "ceo@hedge-edge.com,growth@hedge-edge.com"
    python report_automator.py --action export --type weekly --period 2026-02
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Analytics"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..',
                          'scripts', 'output')

PLAN_MRR = {
    "Free": 0, "Hedge Guide": 0,
    "Challenge Shield": 29, "Starter": 29,
    "Multi-Challenge": 59, "Pro": 59,
    "Unlimited": 99, "Hedger": 99,
}


def _safe_int(val) -> int:
    try:
        return int(val or 0)
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _this_week_start() -> str:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=now.weekday())
    return start.strftime("%Y-%m-%d")


def _this_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def daily_digest(args):
    """Generate daily metrics digest from multiple Notion databases."""
    today = _today()

    # Pull from multiple databases
    leads = query_db("leads_crm")
    kpis = query_db("kpi_snapshots")
    emails = query_db("email_sends")
    mrr_rows = query_db("mrr_tracker")

    # Today's signups
    today_leads = [l for l in leads if (l.get("Date") or "").startswith(today)]
    new_signups = len(today_leads)

    # MRR calculation
    total_mrr = 0
    for row in mrr_rows:
        total_mrr += _safe_float(row.get("MRR") or row.get("Value") or 0)
    if total_mrr == 0:
        # Fallback: estimate from leads
        for l in leads:
            plan = l.get("Plan Interest") or "Free"
            stage = (l.get("Stage") or "").lower()
            if any(kw in stage for kw in ["won", "active", "paid", "customer"]):
                total_mrr += PLAN_MRR.get(plan, 29)

    # Active users estimate
    active_users = sum(1 for l in leads if not any(
        kw in (l.get("Stage") or "").lower() for kw in ["lost", "churned", "inactive"]))

    # Today's emails
    today_emails = [e for e in emails if (e.get("Date") or "").startswith(today)]
    emails_sent = len(today_emails)
    opens = sum(_safe_int(e.get("Opens") or 0) for e in today_emails)
    clicks = sum(_safe_int(e.get("Clicks") or 0) for e in today_emails)

    print("=" * 60)
    print(f"  📋 DAILY DIGEST — {today}")
    print("=" * 60)

    print(f"\n  🆕 New Signups:      {new_signups}")
    print(f"  👥 Active Users:     {active_users}")
    print(f"  💰 Current MRR:      ${total_mrr:,.0f}")
    print(f"  📧 Emails Sent:      {emails_sent}")
    if emails_sent > 0:
        open_rate = opens / emails_sent * 100
        click_rate = clicks / emails_sent * 100
        print(f"     Open Rate:        {open_rate:.1f}%")
        print(f"     Click Rate:       {click_rate:.1f}%")

    # Support / KPI highlights
    recent_kpis = [k for k in kpis if (k.get("Date") or "").startswith(today)]
    if recent_kpis:
        print(f"\n  📊 KPI Updates Today:")
        for kpi in recent_kpis[:5]:
            name = kpi.get("Name") or kpi.get("Metric") or "?"
            val = kpi.get("Value", "?")
            print(f"    • {name}: {val}")

    print(f"\n{'─' * 60}")
    print(f"  Generated at {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
    print("─" * 60)

    log_task(AGENT, f"Daily digest: {today}", "Complete", "P3",
             f"Signups={new_signups}, MRR=${total_mrr:,.0f}, Active={active_users}")


def weekly_report(args):
    """Comprehensive weekly report with KPIs, funnel, and content metrics."""
    week_start = _this_week_start()
    today = _today()

    leads = query_db("leads_crm")
    kpis = query_db("kpi_snapshots")
    funnels = query_db("funnel_metrics")
    campaigns = query_db("campaigns")
    emails = query_db("email_sends")
    mrr_rows = query_db("mrr_tracker")

    # Leads this week
    week_leads = [l for l in leads if (l.get("Date") or "") >= week_start]
    new_signups = len(week_leads)
    total_leads = len(leads)

    # MRR
    total_mrr = sum(_safe_float(r.get("MRR") or r.get("Value") or 0) for r in mrr_rows)
    if total_mrr == 0:
        for l in leads:
            stage = (l.get("Stage") or "").lower()
            if any(kw in stage for kw in ["won", "active", "paid"]):
                total_mrr += PLAN_MRR.get(l.get("Plan Interest") or "Free", 29)

    # Funnel
    stage_counts = defaultdict(int)
    for l in leads:
        stage_counts[(l.get("Stage") or "Unknown")] += 1

    # Email performance
    week_emails = [e for e in emails if (e.get("Date") or "") >= week_start]
    total_sent = len(week_emails)
    total_opens = sum(_safe_int(e.get("Opens") or 0) for e in week_emails)
    total_clicks = sum(_safe_int(e.get("Clicks") or 0) for e in week_emails)

    # Campaign activity
    active_campaigns = [c for c in campaigns if (c.get("Status") or "").lower() in
                        ["active", "running", "live"]]

    print("=" * 65)
    print(f"  📊 WEEKLY REPORT — Week of {week_start}")
    print("=" * 65)

    print(f"\n  ── KPI SNAPSHOT ──")
    print(f"  MRR:             ${total_mrr:,.0f}")
    print(f"  Total Leads:     {total_leads:,}")
    print(f"  New This Week:   {new_signups}")
    active = sum(1 for l in leads if not any(
        kw in (l.get("Stage") or "").lower() for kw in ["lost", "churned"]))
    print(f"  Active Users:    {active}")

    print(f"\n  ── FUNNEL METRICS ──")
    for stage, count in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True)[:6]:
        pct = count / total_leads * 100 if total_leads > 0 else 0
        print(f"  {stage:<25} {count:>5} ({pct:.1f}%)")

    print(f"\n  ── EMAIL PERFORMANCE ──")
    print(f"  Sent:            {total_sent}")
    if total_sent > 0:
        print(f"  Open Rate:       {total_opens / total_sent * 100:.1f}%")
        print(f"  Click Rate:      {total_clicks / total_sent * 100:.1f}%")

    print(f"\n  ── CAMPAIGNS ──")
    print(f"  Active Campaigns: {len(active_campaigns)}")
    for c in active_campaigns[:5]:
        name = c.get("Name", "?")
        channel = c.get("Channel", "?")
        budget = _safe_float(c.get("Budget") or c.get("Spend") or 0)
        print(f"    • {name} ({channel}) — ${budget:,.0f}")

    week_kpis = [k for k in kpis if (k.get("Date") or "") >= week_start]
    if week_kpis:
        print(f"\n  ── KPI UPDATES THIS WEEK ({len(week_kpis)}) ──")
        for k in week_kpis[:5]:
            print(f"    • {k.get('Name', '?')}: {k.get('Value', '?')}")

    print(f"\n{'─' * 65}")
    print(f"  Report: {week_start} → {today}")
    print("─" * 65)

    log_task(AGENT, f"Weekly report: {week_start}", "Complete", "P2",
             f"MRR=${total_mrr:,.0f}, +{new_signups} leads, {total_sent} emails")


def monthly_review(args):
    """Full monthly business review with trends and OKR progress."""
    month = _this_month()

    leads = query_db("leads_crm")
    kpis = query_db("kpi_snapshots")
    funnels = query_db("funnel_metrics")
    campaigns = query_db("campaigns")
    mrr_rows = query_db("mrr_tracker")
    emails = query_db("email_sends")

    # Monthly leads
    month_leads = [l for l in leads if (l.get("Date") or "").startswith(month)]
    total_leads = len(leads)

    # MRR trend (current month)
    total_mrr = sum(_safe_float(r.get("MRR") or r.get("Value") or 0) for r in mrr_rows)
    if total_mrr == 0:
        for l in leads:
            stage = (l.get("Stage") or "").lower()
            if any(kw in stage for kw in ["won", "active", "paid"]):
                total_mrr += PLAN_MRR.get(l.get("Plan Interest") or "Free", 29)

    # Active / churned
    active = sum(1 for l in leads if not any(
        kw in (l.get("Stage") or "").lower() for kw in ["lost", "churned", "inactive"]))
    churned = total_leads - active
    churn_rate = churned / total_leads * 100 if total_leads > 0 else 0

    # Channel breakdown
    channels = defaultdict(int)
    for l in month_leads:
        ch = l.get("Source") or l.get("Channel") or "Direct"
        channels[ch] += 1

    # Campaign spend
    month_campaigns = [c for c in campaigns if (c.get("Date") or "").startswith(month)]
    total_spend = sum(_safe_float(c.get("Budget") or c.get("Spend") or 0) for c in month_campaigns)

    # Email performance this month
    month_emails = [e for e in emails if (e.get("Date") or "").startswith(month)]

    print("=" * 70)
    print(f"  📈 MONTHLY BUSINESS REVIEW — {month}")
    print("=" * 70)

    print(f"\n  ── REVENUE ──")
    print(f"  Monthly Recurring Revenue:   ${total_mrr:,.0f}")
    # Growth rate placeholder (compare to previous month if data exists)
    print(f"  Total Customers (Active):    {active}")
    arr = total_mrr * 12
    print(f"  Annualized Run Rate:         ${arr:,.0f}")

    print(f"\n  ── GROWTH ──")
    print(f"  New Leads This Month:        {len(month_leads)}")
    print(f"  Total Leads (All Time):      {total_leads}")
    print(f"  Churn Rate:                  {churn_rate:.1f}%")
    if total_leads > 0:
        conversion_rate = active / total_leads * 100
        print(f"  Lead-to-Active Rate:         {conversion_rate:.1f}%")

    print(f"\n  ── CHANNEL PERFORMANCE ──")
    for ch, count in sorted(channels.items(), key=lambda x: x[1], reverse=True)[:8]:
        pct = count / len(month_leads) * 100 if month_leads else 0
        print(f"    {ch:<22} {count:>4} leads ({pct:.0f}%)")

    print(f"\n  ── MARKETING SPEND ──")
    print(f"  Total Spend:                 ${total_spend:,.0f}")
    cac = total_spend / len(month_leads) if month_leads else 0
    print(f"  CAC (this month):            ${cac:,.0f}")
    ltv_cac = (29 * 12) / cac if cac > 0 else 0  # Simple LTV:CAC using base plan
    print(f"  LTV:CAC Ratio (est):         {ltv_cac:.1f}x")

    print(f"\n  ── EMAIL MARKETING ──")
    print(f"  Emails Sent:                 {len(month_emails)}")
    if month_emails:
        opens = sum(_safe_int(e.get("Opens") or 0) for e in month_emails)
        clicks = sum(_safe_int(e.get("Clicks") or 0) for e in month_emails)
        print(f"  Avg Open Rate:               {opens / len(month_emails) * 100:.1f}%")
        print(f"  Avg Click Rate:              {clicks / len(month_emails) * 100:.1f}%")

    # OKR progress (from KPI snapshots)
    month_kpis = [k for k in kpis if (k.get("Date") or "").startswith(month)]
    if month_kpis:
        print(f"\n  ── OKR / KPI TRACKING ({len(month_kpis)} updates) ──")
        for k in month_kpis[:8]:
            name = k.get("Name") or k.get("Metric") or "?"
            val = k.get("Value", "?")
            target = k.get("Target", "")
            status = "✅" if target and _safe_float(val) >= _safe_float(target) else "🔵"
            line = f"    {status} {name}: {val}"
            if target:
                line += f" (target: {target})"
            print(line)

    print(f"\n{'─' * 70}")
    print(f"  Review Period: {month}")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("─" * 70)

    log_task(AGENT, f"Monthly review: {month}", "Complete", "P1",
             f"MRR=${total_mrr:,.0f}, +{len(month_leads)} leads, churn={churn_rate:.1f}%")


def schedule_report(args):
    """Set up a recurring report schedule."""
    report_type = args.type
    recipients = args.recipients or "team@hedge-edge.com"

    schedule_map = {
        "daily": "Every day at 08:00 UTC",
        "weekly": "Every Monday at 08:00 UTC",
        "monthly": "1st of each month at 08:00 UTC",
    }

    config = {
        "report_type": report_type,
        "recipients": [r.strip() for r in recipients.split(",")],
        "schedule": schedule_map.get(report_type, "?"),
        "created": _today(),
        "status": "active",
    }

    add_row("kpi_snapshots", {
        "Name": f"Scheduled Report: {report_type.title()}",
        "Metric": "report_schedule",
        "Value": 1,
        "Notes": json.dumps(config),
        "Date": _today(),
    })

    print("=" * 60)
    print("  📅 REPORT SCHEDULE CONFIGURED")
    print("=" * 60)
    print(f"\n  Type:       {report_type.title()} Report")
    print(f"  Schedule:   {schedule_map.get(report_type, '?')}")
    print(f"  Recipients: {recipients}")
    print(f"  Status:     ✅ Active")
    print(f"\n  The {report_type} report will be generated automatically")
    print(f"  and delivered to the specified recipients.")
    print(f"\n{'─' * 60}")
    print(f"  Configuration saved to kpi_snapshots")
    print("─" * 60)

    log_task(AGENT, f"Scheduled {report_type} report", "Complete", "P2",
             f"Recipients: {recipients}")


def export(args):
    """Export a report to JSON file."""
    report_type = args.type
    period = args.period or _this_month()

    # Gather data based on report type
    report_data = {
        "report_type": report_type,
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {},
    }

    leads = query_db("leads_crm")
    kpis = query_db("kpi_snapshots")
    mrr_rows = query_db("mrr_tracker")

    period_leads = [l for l in leads if (l.get("Date") or "").startswith(period)]

    total_mrr = sum(_safe_float(r.get("MRR") or r.get("Value") or 0) for r in mrr_rows)
    active = sum(1 for l in leads if not any(
        kw in (l.get("Stage") or "").lower() for kw in ["lost", "churned"]))

    report_data["data"] = {
        "total_leads": len(leads),
        "period_leads": len(period_leads),
        "active_users": active,
        "mrr": total_mrr,
        "arr": total_mrr * 12,
        "kpi_count": len(kpis),
        "leads_sample": [
            {"name": l.get("Name", "?"), "stage": l.get("Stage", "?"),
             "source": l.get("Source", "?")}
            for l in period_leads[:20]
        ],
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{report_type}_report_{period.replace('-', '_')}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, default=str)

    print("=" * 60)
    print("  📤 REPORT EXPORTED")
    print("=" * 60)
    print(f"\n  Type:     {report_type.title()} Report")
    print(f"  Period:   {period}")
    print(f"  File:     {filename}")
    print(f"  Path:     {filepath}")
    print(f"\n  Contents:")
    print(f"    • {len(leads)} total leads ({len(period_leads)} in period)")
    print(f"    • {active} active users")
    print(f"    • ${total_mrr:,.0f} MRR")
    print(f"    • {len(kpis)} KPI snapshots")
    print(f"\n{'─' * 60}")
    size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    print(f"  File size: {size:,} bytes")
    print("─" * 60)

    log_task(AGENT, f"Exported {report_type} report: {period}", "Complete", "P3",
             f"File: {filename}, {size:,} bytes")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Report Automator — Analytics Agent")
    p.add_argument("--action", required=True,
                   choices=["daily-digest", "weekly-report", "monthly-review",
                            "schedule-report", "export"])
    p.add_argument("--type", choices=["daily", "weekly", "monthly"],
                   help="Report type for schedule/export")
    p.add_argument("--recipients", help="Comma-separated email recipients")
    p.add_argument("--period", help="Period for export (YYYY-MM or YYYY-MM-DD)")

    args = p.parse_args()
    actions = {
        "daily-digest": daily_digest,
        "weekly-report": weekly_report,
        "monthly-review": monthly_review,
        "schedule-report": schedule_report,
        "export": export,
    }
    actions[args.action](args)
