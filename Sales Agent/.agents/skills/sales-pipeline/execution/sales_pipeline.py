#!/usr/bin/env python3
"""
sales_pipeline.py — Sales Agent Pipeline Management

Full sales pipeline with stage tracking, velocity metrics, and
revenue forecasting for Hedge Edge prop-firm hedging software.

Usage:
    python sales_pipeline.py --action stage-update --email john@trader.com --stage demo-scheduled
    python sales_pipeline.py --action pipeline-view
    python sales_pipeline.py --action velocity
    python sales_pipeline.py --action forecast
    python sales_pipeline.py --action stale-deals
    python sales_pipeline.py --action stale-deals --days 7
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Sales"

PIPELINE_STAGES = [
    "prospect",
    "qualified",
    "demo-scheduled",
    "demo-completed",
    "proposal-sent",
    "negotiation",
    "closed-won",
    "closed-lost",
]

# Display-friendly labels
STAGE_LABELS = {
    "prospect": "Prospect",
    "qualified": "Qualified",
    "demo-scheduled": "Demo Scheduled",
    "demo-completed": "Demo Completed",
    "proposal-sent": "Proposal Sent",
    "negotiation": "Negotiation",
    "closed-won": "Closed Won ✅",
    "closed-lost": "Closed Lost ❌",
}

# Historical conversion rates by stage (industry baseline for SaaS + prop-firm)
STAGE_CONVERSION_RATES = {
    "prospect": 0.30,
    "qualified": 0.50,
    "demo-scheduled": 0.60,
    "demo-completed": 0.70,
    "proposal-sent": 0.80,
    "negotiation": 0.90,
    "closed-won": 1.00,
    "closed-lost": 0.00,
}

# Plan-based MRR for forecasting (monthly values)
PLAN_MRR = {
    "Free": 0,
    "Hedge Guide": 0,
    "Challenge Shield": 29,
    "Starter": 29,
    "Multi-Challenge": 59,
    "Pro": 59,
    "Unlimited": 99,
    "Hedger": 99,
}


def _normalize_stage(stage_str: str) -> str:
    """Normalize a stage string to our canonical pipeline stages."""
    if not stage_str:
        return "prospect"
    s = stage_str.lower().strip().replace(" ", "-")
    # Map common CRM stages to pipeline stages
    stage_map = {
        "new-lead": "prospect", "new": "prospect", "lead": "prospect",
        "contacted": "qualified", "discovery": "qualified",
        "mql": "qualified", "sql": "qualified",
        "demo": "demo-scheduled", "demo-booked": "demo-scheduled",
        "proposal": "proposal-sent", "sent": "proposal-sent",
        "won": "closed-won", "converted": "closed-won",
        "lost": "closed-lost", "churned": "closed-lost",
        "opportunity": "negotiation",
    }
    return stage_map.get(s, s) if s not in PIPELINE_STAGES else s


def _estimate_mrr(lead: dict) -> float:
    """Estimate MRR from a lead's plan interest or deal value."""
    plan = lead.get("Plan Interest") or ""
    deal_val = lead.get("Deal Value") or 0
    if deal_val > 0:
        return deal_val if deal_val < 200 else deal_val / 12  # assume yearly if >$200
    return PLAN_MRR.get(plan, 29)  # default to Challenge Shield


def stage_update(args):
    """Move a lead to a new pipeline stage."""
    leads = query_db("leads_crm", filter={
        "property": "Email", "email": {"equals": args.email}
    })
    if not leads:
        print(f"❌ Lead not found: {args.email}")
        return

    lead = leads[0]
    old_stage = lead.get("Stage", "Unknown")
    new_label = STAGE_LABELS.get(args.stage, args.stage.title())

    update_row(lead["_id"], "leads_crm", {
        "Stage": new_label.replace(" ✅", "").replace(" ❌", ""),
    })

    # If closed-won, also log to proposals
    if args.stage == "closed-won":
        mrr = _estimate_mrr(lead)
        add_row("proposals", {
            "Name":       f"Won — {lead.get('Name', args.email)}",
            "Email":      args.email,
            "Status":     "Accepted",
            "Deal Value": mrr,
            "Date":       datetime.now().strftime("%Y-%m-%d"),
            "Notes":      f"Converted from pipeline. Plan: {lead.get('Plan Interest', '?')}",
        })
        print(f"  📝 Proposal marked as Accepted (${mrr:.0f}/mo)")

    print("=" * 60)
    print("  🔄 STAGE UPDATE")
    print("=" * 60)
    print(f"  Lead:     {lead.get('Name', '?')} ({args.email})")
    print(f"  Previous: {old_stage}")
    print(f"  Current:  {new_label}")

    # Show stage progression
    old_idx = PIPELINE_STAGES.index(_normalize_stage(old_stage)) if _normalize_stage(old_stage) in PIPELINE_STAGES else -1
    new_idx = PIPELINE_STAGES.index(args.stage) if args.stage in PIPELINE_STAGES else -1
    if old_idx >= 0 and new_idx >= 0:
        direction = "▲ Advanced" if new_idx > old_idx else "▼ Moved back" if new_idx < old_idx else "─ Same"
        print(f"  Movement: {direction} ({new_idx - old_idx:+d} stages)")
    print("─" * 60)

    log_task(AGENT, f"Stage update: {args.email}",
             "Complete", "P2", f"{old_stage} → {new_label}")


def pipeline_view(args):
    """Visualize the full pipeline as a stage-by-stage funnel."""
    leads = query_db("leads_crm")

    # Bucket leads by normalized stage
    buckets = {s: [] for s in PIPELINE_STAGES}
    for lead in leads:
        stage = _normalize_stage(lead.get("Stage", ""))
        if stage in buckets:
            buckets[stage].append(lead)
        else:
            buckets["prospect"].append(lead)

    print("=" * 60)
    print("  🔮 SALES PIPELINE")
    print("=" * 60)

    if not leads:
        print("\n  Pipeline empty — add leads via crm_sync.py")
        print("─" * 60)
        log_task(AGENT, "Pipeline view", "Complete", "P3", "Empty pipeline")
        return

    total_value = 0
    max_count = max((len(v) for v in buckets.values()), default=1) or 1

    for stage in PIPELINE_STAGES:
        bucket = buckets[stage]
        count = len(bucket)
        value = sum(_estimate_mrr(l) for l in bucket)
        total_value += value
        label = STAGE_LABELS.get(stage, stage)

        bar_len = int(count / max_count * 30) if count > 0 else 0
        bar = "█" * bar_len

        print(f"\n  {label:<20} {count:>3} leads  ${value:>8,.0f}/mo")
        if bar:
            print(f"    {bar}")
        for lead in bucket[:3]:
            name = lead.get("Name", "?")
            mrr = _estimate_mrr(lead)
            print(f"      • {name} (${mrr:.0f}/mo)")
        if count > 3:
            print(f"      ... and {count - 3} more")

    active = sum(len(buckets[s]) for s in PIPELINE_STAGES if s not in ("closed-won", "closed-lost"))
    won = len(buckets["closed-won"])
    lost = len(buckets["closed-lost"])
    win_rate = won / (won + lost) * 100 if (won + lost) > 0 else 0

    print(f"\n{'─' * 60}")
    print(f"  Active Pipeline: {active} leads | ${total_value:,.0f}/mo potential")
    print(f"  Won: {won} | Lost: {lost} | Win Rate: {win_rate:.0f}%")
    print("─" * 60)

    log_task(AGENT, "Pipeline view", "Complete", "P3",
             f"{active} active, {won} won, {lost} lost, ${total_value:,.0f}/mo")


def velocity(args):
    """Calculate pipeline velocity: avg days per stage, bottlenecks."""
    leads = query_db("leads_crm")

    print("=" * 60)
    print("  ⚡ PIPELINE VELOCITY")
    print("=" * 60)

    if not leads:
        print("\n  No leads to analyze.")
        print("─" * 60)
        log_task(AGENT, "Velocity report", "Complete", "P3", "No data")
        return

    # Analyze stage distribution for bottleneck detection
    buckets = {s: [] for s in PIPELINE_STAGES}
    for lead in leads:
        stage = _normalize_stage(lead.get("Stage", ""))
        if stage in buckets:
            buckets[stage].append(lead)

    # Calculate days since contact for each lead (Contact Date → now)
    now = datetime.now()
    stage_ages = {}
    for stage in PIPELINE_STAGES:
        ages = []
        for lead in buckets[stage]:
            contact = lead.get("Contact Date")
            if contact:
                try:
                    dt = datetime.strptime(contact[:10], "%Y-%m-%d")
                    ages.append((now - dt).days)
                except ValueError:
                    pass
        if ages:
            stage_ages[stage] = {
                "avg": sum(ages) / len(ages),
                "max": max(ages),
                "min": min(ages),
                "count": len(ages),
            }

    # Pipeline velocity = (# deals × avg deal value × win rate) / avg cycle length
    total_leads = len(leads)
    won = len(buckets.get("closed-won", []))
    lost = len(buckets.get("closed-lost", []))
    win_rate = won / (won + lost) if (won + lost) > 0 else 0.25  # assume 25% if no data
    avg_deal = sum(_estimate_mrr(l) for l in leads) / total_leads if total_leads else 29
    all_ages = [a for s in stage_ages.values() for _ in range(s["count"]) for a in [s["avg"]]]
    avg_cycle = sum(all_ages) / len(all_ages) if all_ages else 21  # default 3 weeks

    velocity_value = (total_leads * avg_deal * win_rate) / max(avg_cycle, 1) * 30

    print(f"\n  Pipeline Velocity:     ${velocity_value:,.0f}/mo expected")
    print(f"  Active Deals:          {total_leads}")
    print(f"  Avg Deal Value:        ${avg_deal:,.0f}/mo")
    print(f"  Win Rate:              {win_rate * 100:.0f}%")
    print(f"  Avg Cycle (est):       {avg_cycle:.0f} days")

    # Stage-by-stage breakdown
    print(f"\n  {'─' * 44}")
    print("  Stage Duration (days):")
    print(f"    {'Stage':<20} {'Avg':>5} {'Min':>5} {'Max':>5} {'#':>4}")
    print(f"    {'─' * 39}")

    bottleneck_stage, bottleneck_avg = None, 0
    for stage in PIPELINE_STAGES:
        if stage in stage_ages:
            s = stage_ages[stage]
            label = STAGE_LABELS.get(stage, stage)[:18]
            flag = ""
            if s["avg"] > bottleneck_avg and stage not in ("closed-won", "closed-lost"):
                bottleneck_avg = s["avg"]
                bottleneck_stage = stage
                flag = " ⚠️"
            print(f"    {label:<20} {s['avg']:>5.1f} {s['min']:>5} {s['max']:>5} {s['count']:>4}{flag}")

    if bottleneck_stage:
        print(f"\n  🚨 Bottleneck: {STAGE_LABELS.get(bottleneck_stage, bottleneck_stage)}")
        print(f"     Avg {bottleneck_avg:.0f} days — consider process improvements here")
    print("─" * 60)

    log_task(AGENT, "Velocity report", "Complete", "P3",
             f"Velocity ${velocity_value:,.0f}/mo, cycle {avg_cycle:.0f}d")


def forecast(args):
    """Revenue forecast based on pipeline stages and conversion rates."""
    leads = query_db("leads_crm")

    # Also pull MRR tracker for historical context
    try:
        mrr_data = query_db("mrr_tracker", sorts=[
            {"property": "Date", "direction": "descending"}
        ])
        current_mrr = mrr_data[0].get("MRR", 0) if mrr_data else 0
    except Exception:
        current_mrr = 0

    print("=" * 60)
    print("  💰 REVENUE FORECAST")
    print("=" * 60)

    if not leads:
        print(f"\n  Current MRR: ${current_mrr:,.0f}")
        print("  No pipeline leads to forecast.")
        print("─" * 60)
        log_task(AGENT, "Revenue forecast", "Complete", "P3", "No pipeline data")
        return

    # Calculate weighted pipeline value
    buckets = {s: [] for s in PIPELINE_STAGES}
    for lead in leads:
        stage = _normalize_stage(lead.get("Stage", ""))
        if stage in buckets:
            buckets[stage].append(lead)

    print(f"\n  Current MRR:           ${current_mrr:,.0f}")
    print(f"\n  {'─' * 44}")
    print("  Weighted Pipeline Forecast:")
    print(f"    {'Stage':<20} {'Leads':>5} {'Raw MRR':>9} {'Conv%':>6} {'Weighted':>9}")
    print(f"    {'─' * 50}")

    total_raw, total_weighted = 0, 0
    for stage in PIPELINE_STAGES:
        if stage in ("closed-won", "closed-lost"):
            continue
        bucket = buckets[stage]
        if not bucket:
            continue
        raw = sum(_estimate_mrr(l) for l in bucket)
        conv = STAGE_CONVERSION_RATES.get(stage, 0.5)
        weighted = raw * conv
        total_raw += raw
        total_weighted += weighted
        label = STAGE_LABELS.get(stage, stage)[:18]
        print(f"    {label:<20} {len(bucket):>5} ${raw:>7,.0f} {conv * 100:>5.0f}% ${weighted:>7,.0f}")

    won_mrr = sum(_estimate_mrr(l) for l in buckets.get("closed-won", []))

    print(f"    {'─' * 50}")
    print(f"    {'TOTAL':<20} {'':>5} ${total_raw:>7,.0f} {'':>6} ${total_weighted:>7,.0f}")

    # 30/60/90 day projections (assume 30% close within 30d, 50% within 60d, 70% within 90d)
    print(f"\n  {'─' * 44}")
    print("  MRR Projections:")
    print(f"    Current MRR:          ${current_mrr:>8,.0f}")
    print(f"    Won Pipeline:       + ${won_mrr:>8,.0f}")
    print(f"    30-day (est):       + ${total_weighted * 0.30:>8,.0f}  →  ${current_mrr + won_mrr + total_weighted * 0.30:>8,.0f}")
    print(f"    60-day (est):       + ${total_weighted * 0.50:>8,.0f}  →  ${current_mrr + won_mrr + total_weighted * 0.50:>8,.0f}")
    print(f"    90-day (est):       + ${total_weighted * 0.70:>8,.0f}  →  ${current_mrr + won_mrr + total_weighted * 0.70:>8,.0f}")
    print(f"\n  ARR Potential:          ${(current_mrr + won_mrr + total_weighted) * 12:>8,.0f}")
    print("─" * 60)

    summary = (f"Current ${current_mrr:,.0f} MRR, "
               f"weighted pipeline ${total_weighted:,.0f}/mo, "
               f"90d forecast ${current_mrr + won_mrr + total_weighted * 0.70:,.0f}")
    log_task(AGENT, "Revenue forecast", "Complete", "P2", summary)


def stale_deals(args):
    """List deals stuck in a stage for more than N days."""
    threshold = args.days
    leads = query_db("leads_crm")
    now = datetime.now()

    print("=" * 60)
    print(f"  ⏰ STALE DEALS (>{threshold} days in stage)")
    print("=" * 60)

    stale = []
    for lead in leads:
        stage = _normalize_stage(lead.get("Stage", ""))
        if stage in ("closed-won", "closed-lost"):
            continue
        contact = lead.get("Contact Date") or lead.get("Follow Up")
        if not contact:
            continue
        try:
            dt = datetime.strptime(contact[:10], "%Y-%m-%d")
            days_in = (now - dt).days
        except ValueError:
            continue
        if days_in > threshold:
            stale.append({**lead, "_days": days_in, "_norm_stage": stage})

    stale.sort(key=lambda l: l["_days"], reverse=True)

    if not stale:
        print(f"\n  ✅ No deals stale for >{threshold} days!")
        print("─" * 60)
        log_task(AGENT, "Stale deals", "Complete", "P3", "No stale deals")
        return

    for deal in stale:
        name = deal.get("Name", "?")
        email = deal.get("Email", "?")
        stage = STAGE_LABELS.get(deal["_norm_stage"], deal["_norm_stage"])
        days = deal["_days"]
        mrr = _estimate_mrr(deal)

        urgency = "🔴" if days > threshold * 2 else "🟡"
        print(f"\n  {urgency} {name} — {days} days")
        print(f"    Email: {email}")
        print(f"    Stage: {stage} | Est MRR: ${mrr:.0f}/mo")
        if deal.get("Notes"):
            print(f"    Notes: {deal['Notes'][:70]}")

        # Suggest action based on stage
        suggestions = {
            "prospect": "Schedule a discovery call",
            "qualified": "Book a demo via Cal.com",
            "demo-scheduled": "Confirm the demo date or reschedule",
            "demo-completed": "Send a proposal",
            "proposal-sent": "Follow up on proposal — ask for objections",
            "negotiation": "Push for close or identify blocker",
        }
        suggestion = suggestions.get(deal["_norm_stage"], "Follow up")
        print(f"    💡 Suggested: {suggestion}")

    at_risk_value = sum(_estimate_mrr(d) for d in stale)
    print(f"\n{'─' * 60}")
    print(f"  Stale Deals: {len(stale)} | At-Risk MRR: ${at_risk_value:,.0f}/mo")
    print("─" * 60)

    log_task(AGENT, "Stale deals", "Complete", "P2",
             f"{len(stale)} stale deals, ${at_risk_value:,.0f}/mo at risk")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sales Pipeline Manager")
    parser.add_argument("--action", required=True,
                        choices=["stage-update", "pipeline-view", "velocity",
                                 "forecast", "stale-deals"])
    parser.add_argument("--email", help="Lead email for stage update")
    parser.add_argument("--stage", choices=PIPELINE_STAGES, help="Target pipeline stage")
    parser.add_argument("--days", type=int, default=14, help="Stale threshold in days (default: 14)")
    args = parser.parse_args()

    dispatch = {
        "stage-update": stage_update,
        "pipeline-view": pipeline_view,
        "velocity": velocity,
        "forecast": forecast,
        "stale-deals": stale_deals,
    }
    dispatch[args.action](args)
