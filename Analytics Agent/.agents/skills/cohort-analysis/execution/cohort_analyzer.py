#!/usr/bin/env python3
"""
cohort_analyzer.py — Analytics Agent Cohort Analysis

Analyze user cohorts for retention, LTV, and behavior patterns
for Hedge Edge prop-firm hedging software.

Usage:
    python cohort_analyzer.py --action build-cohorts
    python cohort_analyzer.py --action retention-matrix
    python cohort_analyzer.py --action ltv-estimate
    python cohort_analyzer.py --action churn-analysis
    python cohort_analyzer.py --action cohort-comparison --cohort-a 2026-01 --cohort-b 2026-02
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Analytics"

# Hedge Edge pricing tiers (monthly)
PLAN_MRR = {
    "Free": 0, "Hedge Guide": 0,
    "Challenge Shield": 29, "Starter": 29,
    "Multi-Challenge": 59, "Pro": 59,
    "Unlimited": 99, "Hedger": 99,
}

DEFAULT_ARPU = 29  # Weighted avg for early-stage (most users on Challenge Shield)


def _parse_date(date_str: str) -> datetime | None:
    """Parse a date string to datetime, tolerant of formats."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S%z", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str.split("T")[0] if "T" in date_str else date_str,
                                     fmt.split("T")[0])
        except ValueError:
            continue
    return None


def _cohort_key(dt: datetime) -> str:
    """Return YYYY-MM cohort key from a datetime."""
    return dt.strftime("%Y-%m")


def _is_active(lead: dict) -> bool:
    """Check if a lead is currently active (not churned)."""
    stage = (lead.get("Stage") or lead.get("Status") or "").lower()
    return not any(kw in stage for kw in ["lost", "churned", "inactive", "cancelled"])


def _months_between(d1: datetime, d2: datetime) -> int:
    """Calculate months between two dates."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def build_cohorts(args):
    """Build monthly signup cohorts from leads_crm."""
    leads = query_db("leads_crm")

    cohorts = defaultdict(list)
    skipped = 0
    for lead in leads:
        signup_date = _parse_date(lead.get("Date") or lead.get("Created") or "")
        if not signup_date:
            skipped += 1
            continue
        key = _cohort_key(signup_date)
        cohorts[key].append(lead)

    print("=" * 65)
    print("  👥 COHORT BUILD — Monthly Signup Cohorts")
    print("=" * 65)

    if not cohorts:
        print("\n  No datable leads found in CRM.")
        print("─" * 65)
        return

    sorted_cohorts = sorted(cohorts.items())
    for key, members in sorted_cohorts:
        active = sum(1 for m in members if _is_active(m))
        churned = len(members) - active
        retention = active / len(members) * 100 if members else 0

        plans = defaultdict(int)
        for m in members:
            plan = m.get("Plan Interest") or "Free"
            plans[plan] += 1
        top_plan = max(plans.items(), key=lambda x: x[1])[0] if plans else "?"

        print(f"\n  📅 {key}:  {len(members):>4} signups  |  "
              f"Active: {active}  Churned: {churned}  Ret: {retention:.0f}%")
        print(f"    Top plan: {top_plan} ({plans[top_plan]})")

    # Log cohort build to funnel_metrics
    total = sum(len(m) for m in cohorts.values())
    add_row("funnel_metrics", {
        "Name": f"Cohort Build {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "Stage": "Cohort Analysis",
        "Value": total,
        "Notes": f"{len(cohorts)} cohorts, {total} total leads, {skipped} skipped (no date)",
        "Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })

    print(f"\n{'─' * 65}")
    print(f"  Total: {total} leads across {len(cohorts)} monthly cohorts")
    if skipped:
        print(f"  ⚠️  {skipped} leads skipped (missing date)")
    print("─" * 65)

    log_task(AGENT, "Built monthly cohorts", "Complete", "P2",
             f"{len(cohorts)} cohorts, {total} leads")


def retention_matrix(args):
    """Generate Month-0 through Month-6 retention matrix."""
    leads = query_db("leads_crm")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    cohorts = defaultdict(list)
    for lead in leads:
        signup_date = _parse_date(lead.get("Date") or lead.get("Created") or "")
        if signup_date:
            cohorts[_cohort_key(signup_date)].append({
                "signup": signup_date,
                "active": _is_active(lead),
                "last_seen": _parse_date(lead.get("Last Activity") or lead.get("Updated") or ""),
            })

    print("=" * 75)
    print("  📊 RETENTION MATRIX (Month 0 – Month 6)")
    print("=" * 75)

    if not cohorts:
        print("\n  No cohort data available.")
        print("─" * 75)
        return

    header = f"  {'Cohort':<10} {'Size':>5}"
    for m in range(7):
        header += f" {'M' + str(m):>6}"
    print(f"\n{header}")
    print(f"  {'─' * 63}")

    sorted_cohorts = sorted(cohorts.items())
    for key, members in sorted_cohorts:
        size = len(members)
        row = f"  {key:<10} {size:>5}"

        for month_offset in range(7):
            # For each month, count members whose signup is at least that many months ago
            # and who are still active (or were active at that month)
            cohort_start = datetime.strptime(key + "-01", "%Y-%m-%d")
            month_end = cohort_start.replace(day=1) + timedelta(days=32 * (month_offset + 1))
            month_end = month_end.replace(day=1)

            if month_end > now:
                row += f" {'  —':>6}"
                continue

            # Simple retention model: active proportion decays
            # For real data, check last_seen against the month boundary
            active_at_month = 0
            eligible = 0
            for m in members:
                months_since_signup = _months_between(m["signup"], now)
                if months_since_signup >= month_offset:
                    eligible += 1
                    if m["active"] or (m["last_seen"] and _months_between(m["signup"], m["last_seen"]) >= month_offset):
                        active_at_month += 1

            if eligible > 0:
                pct = active_at_month / eligible * 100
                row += f" {pct:>5.0f}%"
            else:
                row += f" {'  —':>6}"

        print(row)

    print(f"\n{'─' * 75}")
    print(f"  {len(sorted_cohorts)} cohorts analyzed")
    print(f"  Retention = % of cohort still active at month N")
    print("─" * 75)

    log_task(AGENT, "Generated retention matrix", "Complete", "P1",
             f"{len(sorted_cohorts)} cohorts, Month 0-6")


def ltv_estimate(args):
    """Estimate Customer Lifetime Value per cohort."""
    leads = query_db("leads_crm")

    cohorts = defaultdict(list)
    for lead in leads:
        signup_date = _parse_date(lead.get("Date") or lead.get("Created") or "")
        if signup_date:
            cohorts[_cohort_key(signup_date)].append(lead)

    print("=" * 70)
    print("  💎 CUSTOMER LIFETIME VALUE BY COHORT")
    print("=" * 70)

    if not cohorts:
        print("\n  No cohort data available.")
        print("─" * 70)
        return

    print(f"\n  Pricing: Challenge Shield $29 | Multi-Challenge $59 | Unlimited $99")
    print(f"\n  {'Cohort':<10} {'Size':>5} {'ARPU':>7} {'Ret%':>6} {'Avg Life':>9} {'LTV':>9} {'Total LTV':>11}")
    print(f"  {'─' * 62}")

    grand_total_ltv = 0
    for key in sorted(cohorts.keys()):
        members = cohorts[key]
        size = len(members)
        active = sum(1 for m in members if _is_active(m))
        retention_rate = active / size if size > 0 else 0

        # Calculate ARPU from plan mix
        total_mrr = 0
        paying = 0
        for m in members:
            plan = m.get("Plan Interest") or "Free"
            mrr = PLAN_MRR.get(plan, DEFAULT_ARPU)
            total_mrr += mrr
            if mrr > 0:
                paying += 1

        arpu = total_mrr / paying if paying > 0 else DEFAULT_ARPU

        # Average lifetime in months: 1 / (1 - retention_rate), capped at 36
        churn_rate = 1 - retention_rate
        avg_lifetime = min(1 / churn_rate, 36) if churn_rate > 0 else 36

        # LTV = ARPU × Average Lifetime
        ltv = arpu * avg_lifetime
        cohort_total_ltv = ltv * size
        grand_total_ltv += cohort_total_ltv

        print(f"  {key:<10} {size:>5} ${arpu:>5.0f} {retention_rate:>5.0%} "
              f"{avg_lifetime:>7.1f}mo ${ltv:>7,.0f} ${cohort_total_ltv:>9,.0f}")

    total_users = sum(len(m) for m in cohorts.values())
    avg_ltv = grand_total_ltv / total_users if total_users > 0 else 0

    print(f"\n{'─' * 70}")
    print(f"  Total Users: {total_users:,} | Avg LTV: ${avg_ltv:,.0f} | "
          f"Total LTV: ${grand_total_ltv:,.0f}")
    print(f"  ℹ️  LTV = ARPU × (1 / Churn Rate), capped at 36 months")
    print("─" * 70)

    log_task(AGENT, "LTV estimation by cohort", "Complete", "P1",
             f"Avg LTV=${avg_ltv:,.0f}, Total=${grand_total_ltv:,.0f}")


def churn_analysis(args):
    """Analyze churn patterns: when, why, and trend."""
    leads = query_db("leads_crm")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    churned = []
    active_count = 0
    for lead in leads:
        if not _is_active(lead):
            signup = _parse_date(lead.get("Date") or lead.get("Created") or "")
            last_seen = _parse_date(lead.get("Last Activity") or lead.get("Updated") or "")
            churned.append({
                "name": lead.get("Name", "?"),
                "signup": signup,
                "last_seen": last_seen,
                "plan": lead.get("Plan Interest") or "Free",
                "stage": lead.get("Stage") or lead.get("Status") or "?",
                "months_active": _months_between(signup, last_seen) if signup and last_seen else 0,
            })
        else:
            active_count += 1

    total = len(churned) + active_count
    churn_rate = len(churned) / total * 100 if total > 0 else 0

    print("=" * 65)
    print("  📉 CHURN ANALYSIS")
    print("=" * 65)
    print(f"\n  Total Users: {total} | Active: {active_count} | "
          f"Churned: {len(churned)} | Churn Rate: {churn_rate:.1f}%")

    if not churned:
        print("\n  ✅ No churned users found!")
        print("─" * 65)
        log_task(AGENT, "Churn analysis", "Complete", "P2", "0 churned")
        return

    # When do users churn? (month distribution)
    month_dist = defaultdict(int)
    for c in churned:
        bucket = min(c["months_active"], 6)
        month_dist[bucket] += 1

    print(f"\n  📅 WHEN — Churn by Active Month:")
    for m in range(7):
        count = month_dist.get(m, 0)
        pct = count / len(churned) * 100 if churned else 0
        bar = "█" * int(pct / 2)
        print(f"    Month {m}: {count:>3} ({pct:>5.1f}%) {bar}")

    # Why — last stage before churn
    stage_dist = defaultdict(int)
    for c in churned:
        stage_dist[c["stage"]] += 1

    print(f"\n  ❓ WHY — Last Stage Before Churn:")
    for stage, count in sorted(stage_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
        pct = count / len(churned) * 100
        print(f"    {stage:<25} {count:>3} ({pct:.1f}%)")

    # Plan distribution of churned users
    plan_dist = defaultdict(int)
    for c in churned:
        plan_dist[c["plan"]] += 1

    print(f"\n  💳 PLAN — Churned User Plan Distribution:")
    for plan, count in sorted(plan_dist.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(churned) * 100
        print(f"    {plan:<25} {count:>3} ({pct:.1f}%)")

    # Monthly churn trend
    monthly_churn = defaultdict(int)
    for c in churned:
        if c["last_seen"]:
            monthly_churn[_cohort_key(c["last_seen"])] += 1

    if monthly_churn:
        print(f"\n  📈 TREND — Monthly Churn Count:")
        for month in sorted(monthly_churn.keys())[-6:]:
            count = monthly_churn[month]
            bar = "█" * count
            print(f"    {month}: {count:>3} {bar}")

    print(f"\n{'─' * 65}")
    peak_month = max(month_dist.items(), key=lambda x: x[1])[0] if month_dist else "?"
    print(f"  ⚠️  Peak churn at Month {peak_month}")
    print(f"  Recommendation: Strengthen onboarding and Month-{peak_month} engagement")
    print("─" * 65)

    log_task(AGENT, "Churn analysis", "Complete", "P1",
             f"{len(churned)} churned ({churn_rate:.1f}%), peak at M{peak_month}")


def cohort_comparison(args):
    """Compare two cohorts side by side."""
    leads = query_db("leads_crm")

    cohorts = defaultdict(list)
    for lead in leads:
        signup_date = _parse_date(lead.get("Date") or lead.get("Created") or "")
        if signup_date:
            cohorts[_cohort_key(signup_date)].append(lead)

    a_key = args.cohort_a
    b_key = args.cohort_b

    print("=" * 70)
    print(f"  🔍 COHORT COMPARISON: {a_key} vs {b_key}")
    print("=" * 70)

    if a_key not in cohorts and b_key not in cohorts:
        print(f"\n  ❌ Neither cohort found. Available: {', '.join(sorted(cohorts.keys()))}")
        print("─" * 70)
        return

    def _cohort_stats(members):
        size = len(members)
        active = sum(1 for m in members if _is_active(m))
        retention = active / size * 100 if size > 0 else 0
        paying = 0
        total_mrr = 0
        for m in members:
            mrr = PLAN_MRR.get(m.get("Plan Interest") or "Free", 0)
            total_mrr += mrr
            if mrr > 0:
                paying += 1
        arpu = total_mrr / paying if paying > 0 else 0
        churn = 1 - (active / size) if size > 0 else 0
        avg_life = min(1 / churn, 36) if churn > 0 else 36
        ltv = arpu * avg_life
        return {
            "size": size, "active": active, "retention": retention,
            "paying": paying, "arpu": arpu, "ltv": ltv,
            "mrr": total_mrr, "churn": churn * 100,
        }

    members_a = cohorts.get(a_key, [])
    members_b = cohorts.get(b_key, [])
    sa = _cohort_stats(members_a)
    sb = _cohort_stats(members_b)

    def _delta(va, vb, fmt=".0f", pct=False):
        diff = vb - va
        sign = "+" if diff > 0 else ""
        suffix = "pp" if pct else ""
        return f"{sign}{diff:{fmt}}{suffix}"

    print(f"\n  {'Metric':<22} {a_key:>12} {b_key:>12} {'Delta':>10}")
    print(f"  {'─' * 58}")
    print(f"  {'Cohort Size':<22} {sa['size']:>12,} {sb['size']:>12,} {_delta(sa['size'], sb['size']):>10}")
    print(f"  {'Active Users':<22} {sa['active']:>12,} {sb['active']:>12,} {_delta(sa['active'], sb['active']):>10}")
    print(f"  {'Retention %':<22} {sa['retention']:>11.1f}% {sb['retention']:>11.1f}% {_delta(sa['retention'], sb['retention'], '.1f', True):>10}")
    print(f"  {'Paying Users':<22} {sa['paying']:>12,} {sb['paying']:>12,} {_delta(sa['paying'], sb['paying']):>10}")
    print(f"  {'ARPU':<22} ${sa['arpu']:>10,.0f} ${sb['arpu']:>10,.0f} {_delta(sa['arpu'], sb['arpu']):>10}")
    print(f"  {'Churn %':<22} {sa['churn']:>11.1f}% {sb['churn']:>11.1f}% {_delta(sa['churn'], sb['churn'], '.1f', True):>10}")
    print(f"  {'Est. LTV':<22} ${sa['ltv']:>10,.0f} ${sb['ltv']:>10,.0f} {_delta(sa['ltv'], sb['ltv']):>10}")
    print(f"  {'Total MRR':<22} ${sa['mrr']:>10,.0f} ${sb['mrr']:>10,.0f} {_delta(sa['mrr'], sb['mrr']):>10}")

    # Verdict
    better = a_key if sa["ltv"] > sb["ltv"] else b_key
    print(f"\n{'─' * 70}")
    print(f"  🏆 {better} has higher estimated LTV")
    if sa["retention"] != sb["retention"]:
        better_ret = a_key if sa["retention"] > sb["retention"] else b_key
        print(f"  📊 {better_ret} has better retention ({max(sa['retention'], sb['retention']):.1f}%)")
    print("─" * 70)

    log_task(AGENT, f"Cohort comparison: {a_key} vs {b_key}",
             "Complete", "P2",
             f"{a_key}: LTV=${sa['ltv']:,.0f} | {b_key}: LTV=${sb['ltv']:,.0f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Cohort Analyzer — Analytics Agent")
    p.add_argument("--action", required=True,
                   choices=["build-cohorts", "retention-matrix", "ltv-estimate",
                            "churn-analysis", "cohort-comparison"])
    p.add_argument("--cohort-a", help="First cohort key (YYYY-MM)")
    p.add_argument("--cohort-b", help="Second cohort key (YYYY-MM)")

    args = p.parse_args()
    actions = {
        "build-cohorts": build_cohorts,
        "retention-matrix": retention_matrix,
        "ltv-estimate": ltv_estimate,
        "churn-analysis": churn_analysis,
        "cohort-comparison": cohort_comparison,
    }
    actions[args.action](args)
