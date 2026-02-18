#!/usr/bin/env python3
"""
attribution_modeler.py — Analytics Agent Attribution Modeling

Model marketing attribution to understand which channels drive
conversions for Hedge Edge prop-firm hedging software.

Usage:
    python attribution_modeler.py --action first-touch
    python attribution_modeler.py --action last-touch
    python attribution_modeler.py --action linear
    python attribution_modeler.py --action channel-roi
    python attribution_modeler.py --action attribution-report
"""

import sys, os, argparse, json
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Analytics"

KNOWN_CHANNELS = [
    "Organic Search", "Paid Search", "Social Media", "Discord",
    "Email", "Referral", "Direct", "YouTube", "LinkedIn",
    "Twitter/X", "Reddit", "Partner", "Content Marketing",
]

# Plan-based MRR for revenue attribution
PLAN_MRR = {
    "Free": 0, "Hedge Guide": 0,
    "Challenge Shield": 29, "Starter": 29,
    "Multi-Challenge": 59, "Pro": 59,
    "Unlimited": 99, "Hedger": 99,
}


def _extract_channel(lead: dict) -> str:
    """Extract marketing channel from lead source field."""
    source = (lead.get("Source") or lead.get("Channel") or "Direct").strip()
    for ch in KNOWN_CHANNELS:
        if ch.lower() in source.lower():
            return ch
    return source if source else "Direct"


def _extract_touchpoints(lead: dict) -> list:
    """Extract multi-touch journey from lead data."""
    touchpoints = []
    source = _extract_channel(lead)
    touchpoints.append(source)

    # Parse touchpoint history from Notes if available
    notes = lead.get("Notes", "") or ""
    for ch in KNOWN_CHANNELS:
        if ch.lower() in notes.lower() and ch != source:
            touchpoints.append(ch)

    # If lead has referral info, add it
    referral = lead.get("Referral Source", "") or ""
    if referral and referral != source:
        touchpoints.append(referral)

    return touchpoints if touchpoints else ["Direct"]


def _is_converted(lead: dict) -> bool:
    """Check if a lead has converted (paying or demo-completed)."""
    stage = (lead.get("Stage") or "").lower()
    status = (lead.get("Status") or "").lower()
    return any(kw in stage or kw in status for kw in
               ["won", "converted", "paid", "active", "customer", "demo-completed"])


def _lead_revenue(lead: dict) -> float:
    """Estimate revenue from a lead based on plan."""
    plan = lead.get("Plan Interest") or ""
    deal_val = lead.get("Deal Value") or 0
    if deal_val and float(deal_val) > 0:
        v = float(deal_val)
        return v if v < 200 else v / 12
    return PLAN_MRR.get(plan, 29)


def first_touch(args):
    """First-touch attribution: credit the channel that first brought the lead."""
    leads = query_db("leads_crm")

    channel_stats = defaultdict(lambda: {"leads": 0, "conversions": 0, "revenue": 0.0})
    for lead in leads:
        channel = _extract_channel(lead)
        channel_stats[channel]["leads"] += 1
        if _is_converted(lead):
            channel_stats[channel]["conversions"] += 1
            channel_stats[channel]["revenue"] += _lead_revenue(lead)

    print("=" * 70)
    print("  📍 FIRST-TOUCH ATTRIBUTION")
    print("=" * 70)

    if not channel_stats:
        print("\n  No lead data available.")
        print("─" * 70)
        return

    sorted_ch = sorted(channel_stats.items(), key=lambda x: x[1]["conversions"], reverse=True)
    total_conv = sum(s["conversions"] for _, s in sorted_ch)

    print(f"\n  {'Channel':<20} {'Leads':>7} {'Conv':>6} {'Rate':>7} {'Revenue':>10} {'Share':>7}")
    print(f"  {'─' * 62}")

    for ch, stats in sorted_ch:
        rate = stats["conversions"] / stats["leads"] * 100 if stats["leads"] > 0 else 0
        share = stats["conversions"] / total_conv * 100 if total_conv > 0 else 0
        print(f"  {ch:<20} {stats['leads']:>7,} {stats['conversions']:>6,} "
              f"{rate:>6.1f}% ${stats['revenue']:>8,.0f} {share:>6.1f}%")

    total_leads = sum(s["leads"] for _, s in sorted_ch)
    total_rev = sum(s["revenue"] for _, s in sorted_ch)
    print(f"\n{'─' * 70}")
    print(f"  Total: {total_leads:,} leads → {total_conv:,} conversions (${total_rev:,.0f}/mo)")
    print("─" * 70)

    log_task(AGENT, "First-touch attribution report",
             "Complete", "P2", f"{len(sorted_ch)} channels, {total_conv} conversions")


def last_touch(args):
    """Last-touch attribution: credit the last interaction channel before conversion."""
    leads = query_db("leads_crm")

    channel_stats = defaultdict(lambda: {"leads": 0, "conversions": 0, "revenue": 0.0})
    for lead in leads:
        touchpoints = _extract_touchpoints(lead)
        last_ch = touchpoints[-1]  # Last touchpoint = last-touch credit
        channel_stats[last_ch]["leads"] += 1
        if _is_converted(lead):
            channel_stats[last_ch]["conversions"] += 1
            channel_stats[last_ch]["revenue"] += _lead_revenue(lead)

    print("=" * 70)
    print("  📍 LAST-TOUCH ATTRIBUTION")
    print("=" * 70)

    if not channel_stats:
        print("\n  No lead data available.")
        print("─" * 70)
        return

    sorted_ch = sorted(channel_stats.items(), key=lambda x: x[1]["conversions"], reverse=True)
    total_conv = sum(s["conversions"] for _, s in sorted_ch)

    print(f"\n  {'Channel':<20} {'Leads':>7} {'Conv':>6} {'Rate':>7} {'Revenue':>10} {'Share':>7}")
    print(f"  {'─' * 62}")

    for ch, stats in sorted_ch:
        rate = stats["conversions"] / stats["leads"] * 100 if stats["leads"] > 0 else 0
        share = stats["conversions"] / total_conv * 100 if total_conv > 0 else 0
        print(f"  {ch:<20} {stats['leads']:>7,} {stats['conversions']:>6,} "
              f"{rate:>6.1f}% ${stats['revenue']:>8,.0f} {share:>6.1f}%")

    total_leads = sum(s["leads"] for _, s in sorted_ch)
    total_rev = sum(s["revenue"] for _, s in sorted_ch)
    print(f"\n{'─' * 70}")
    print(f"  Total: {total_leads:,} leads → {total_conv:,} conversions (${total_rev:,.0f}/mo)")
    print("─" * 70)

    log_task(AGENT, "Last-touch attribution report",
             "Complete", "P2", f"{len(sorted_ch)} channels, {total_conv} conversions")


def linear(args):
    """Linear attribution: divide credit equally across all touchpoints."""
    leads = query_db("leads_crm")

    channel_credit = defaultdict(lambda: {"credit": 0.0, "revenue": 0.0, "touches": 0})
    total_conversions = 0

    for lead in leads:
        touchpoints = _extract_touchpoints(lead)
        for tp in touchpoints:
            channel_credit[tp]["touches"] += 1

        if _is_converted(lead):
            total_conversions += 1
            credit_each = 1.0 / len(touchpoints)
            rev_each = _lead_revenue(lead) / len(touchpoints)
            for tp in touchpoints:
                channel_credit[tp]["credit"] += credit_each
                channel_credit[tp]["revenue"] += rev_each

    print("=" * 70)
    print("  📍 LINEAR ATTRIBUTION (Equal Credit)")
    print("=" * 70)

    if not channel_credit:
        print("\n  No lead data available.")
        print("─" * 70)
        return

    sorted_ch = sorted(channel_credit.items(), key=lambda x: x[1]["credit"], reverse=True)

    print(f"\n  {'Channel':<20} {'Touches':>8} {'Credit':>8} {'Revenue':>10} {'Share':>7}")
    print(f"  {'─' * 58}")

    total_credit = sum(s["credit"] for _, s in sorted_ch)
    for ch, stats in sorted_ch:
        share = stats["credit"] / total_credit * 100 if total_credit > 0 else 0
        print(f"  {ch:<20} {stats['touches']:>8,} {stats['credit']:>8.1f} "
              f"${stats['revenue']:>8,.0f} {share:>6.1f}%")

    total_rev = sum(s["revenue"] for _, s in sorted_ch)
    print(f"\n{'─' * 70}")
    print(f"  Total conversions: {total_conversions} | "
          f"Total attributed revenue: ${total_rev:,.0f}/mo")
    print("─" * 70)

    log_task(AGENT, "Linear attribution report",
             "Complete", "P2", f"{len(sorted_ch)} channels, {total_conversions} convs")


def channel_roi(args):
    """Calculate ROI per marketing channel: spend vs conversions."""
    leads = query_db("leads_crm")
    campaigns = query_db("campaigns")

    # Aggregate campaign spend by channel
    channel_spend = defaultdict(float)
    for camp in campaigns:
        ch = camp.get("Channel") or camp.get("Source") or "Unknown"
        budget = float(camp.get("Budget") or camp.get("Spend") or 0)
        channel_spend[ch] += budget

    # Count conversions per channel
    channel_conv = defaultdict(lambda: {"leads": 0, "conversions": 0, "revenue": 0.0})
    for lead in leads:
        ch = _extract_channel(lead)
        channel_conv[ch]["leads"] += 1
        if _is_converted(lead):
            channel_conv[ch]["conversions"] += 1
            channel_conv[ch]["revenue"] += _lead_revenue(lead)

    all_channels = set(list(channel_spend.keys()) + list(channel_conv.keys()))

    print("=" * 75)
    print("  💰 CHANNEL ROI ANALYSIS")
    print("=" * 75)

    if not all_channels:
        print("\n  No channel data found.")
        print("─" * 75)
        return

    print(f"\n  {'Channel':<18} {'Spend':>9} {'Leads':>6} {'Conv':>5} {'CPL':>8} {'CPA':>8} {'ROI':>8}")
    print(f"  {'─' * 68}")

    rows = []
    for ch in sorted(all_channels):
        spend = channel_spend.get(ch, 0)
        data = channel_conv.get(ch, {"leads": 0, "conversions": 0, "revenue": 0.0})
        cpl = spend / data["leads"] if data["leads"] > 0 else 0
        cpa = spend / data["conversions"] if data["conversions"] > 0 else 0
        # ROI = (revenue - spend) / spend, annualized from monthly
        annual_rev = data["revenue"] * 12
        roi = (annual_rev - spend) / spend * 100 if spend > 0 else float('inf') if data["revenue"] > 0 else 0
        rows.append((ch, spend, data, cpl, cpa, roi))

    rows.sort(key=lambda x: x[5], reverse=True)

    for ch, spend, data, cpl, cpa, roi in rows:
        roi_str = f"{roi:>7.0f}%" if roi != float('inf') else "    ∞%"
        cpl_str = f"${cpl:>6,.0f}" if cpl > 0 else "     $0"
        cpa_str = f"${cpa:>6,.0f}" if cpa > 0 else "     $0"
        print(f"  {ch:<18} ${spend:>7,.0f} {data['leads']:>6,} {data['conversions']:>5,} "
              f"{cpl_str} {cpa_str} {roi_str}")

    total_spend = sum(r[1] for r in rows)
    total_leads = sum(r[2]["leads"] for r in rows)
    total_conv = sum(r[2]["conversions"] for r in rows)
    total_rev = sum(r[2]["revenue"] for r in rows)
    avg_cpl = total_spend / total_leads if total_leads > 0 else 0
    avg_cpa = total_spend / total_conv if total_conv > 0 else 0

    print(f"\n{'─' * 75}")
    print(f"  Total Spend: ${total_spend:,.0f} | Leads: {total_leads:,} | Conversions: {total_conv:,}")
    print(f"  Avg CPL: ${avg_cpl:,.0f} | Avg CPA: ${avg_cpa:,.0f} | MRR: ${total_rev:,.0f}/mo")
    print("─" * 75)

    log_task(AGENT, "Channel ROI analysis",
             "Complete", "P1",
             f"${total_spend:,.0f} spend, {total_conv} conv, CPL=${avg_cpl:.0f}")


def attribution_report(args):
    """Full multi-model attribution comparison side by side."""
    leads = query_db("leads_crm")

    # Build all three models simultaneously
    ft = defaultdict(float)   # first-touch
    lt = defaultdict(float)   # last-touch
    ln = defaultdict(float)   # linear

    total_conversions = 0
    for lead in leads:
        if not _is_converted(lead):
            continue
        total_conversions += 1
        touchpoints = _extract_touchpoints(lead)

        ft[touchpoints[0]] += 1.0
        lt[touchpoints[-1]] += 1.0
        credit_each = 1.0 / len(touchpoints)
        for tp in touchpoints:
            ln[tp] += credit_each

    all_channels = sorted(set(list(ft.keys()) + list(lt.keys()) + list(ln.keys())))

    print("=" * 75)
    print("  📊 MULTI-MODEL ATTRIBUTION COMPARISON")
    print("=" * 75)

    if not all_channels:
        print("\n  No conversions to attribute.")
        print("─" * 75)
        return

    print(f"\n  {'Channel':<20} {'First-Touch':>12} {'Last-Touch':>12} {'Linear':>12} {'Avg':>8}")
    print(f"  {'─' * 68}")

    for ch in all_channels:
        f = ft.get(ch, 0)
        l = lt.get(ch, 0)
        n = ln.get(ch, 0)
        avg = (f + l + n) / 3
        print(f"  {ch:<20} {f:>12.1f} {l:>12.1f} {n:>12.1f} {avg:>8.1f}")

    # Show model agreement/divergence
    print(f"\n{'─' * 75}")
    print(f"  Total Conversions: {total_conversions}")
    print(f"  Channels Tracked:  {len(all_channels)}")

    # Highlight biggest discrepancy between models
    max_delta = 0
    delta_ch = ""
    for ch in all_channels:
        vals = [ft.get(ch, 0), lt.get(ch, 0), ln.get(ch, 0)]
        delta = max(vals) - min(vals)
        if delta > max_delta:
            max_delta = delta
            delta_ch = ch

    if delta_ch:
        print(f"  Biggest Model Divergence: {delta_ch} (Δ {max_delta:.1f} conversions)")
        print(f"  → Consider investigating {delta_ch}'s role in the funnel")
    print("─" * 75)

    log_task(AGENT, "Multi-model attribution report",
             "Complete", "P1",
             f"{len(all_channels)} channels, {total_conversions} conversions compared")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Attribution Modeler — Analytics Agent")
    p.add_argument("--action", required=True,
                   choices=["first-touch", "last-touch", "linear",
                            "channel-roi", "attribution-report"])

    args = p.parse_args()
    actions = {
        "first-touch": first_touch,
        "last-touch": last_touch,
        "linear": linear,
        "channel-roi": channel_roi,
        "attribution-report": attribution_report,
    }
    actions[args.action](args)
