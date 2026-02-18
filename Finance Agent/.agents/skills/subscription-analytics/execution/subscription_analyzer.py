#!/usr/bin/env python3
"""
subscription_analyzer.py — Finance Agent Subscription Analytics

Analyze subscription metrics: churn, expansion, contraction, plan
distribution, and composite health scoring for Hedge Edge Ltd.

Usage:
    python subscription_analyzer.py --action plan-distribution
    python subscription_analyzer.py --action churn-rate --month 2026-02
    python subscription_analyzer.py --action expansion-revenue
    python subscription_analyzer.py --action downgrade-analysis
    python subscription_analyzer.py --action subscription-health
"""

import sys, os, argparse, json, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Finance"

PLAN_ORDER = ["Free Trial", "Starter", "Pro", "Enterprise"]
PLAN_PRICES = {"Free Trial": 0, "Starter": 29, "Pro": 59, "Enterprise": 99}
SMB_CHURN_BENCHMARK_LOW = 0.05   # 5%
SMB_CHURN_BENCHMARK_HIGH = 0.07  # 7%


def _parse_num(row, key, default=0):
    val = row.get(key, default)
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default


def _get_mrr_rows():
    return query_db("mrr_tracker")


def _get_month_data(rows, month):
    """Get all mrr_tracker rows matching a YYYY-MM month."""
    return [r for r in rows if (r.get("Date") or "")[:7] == month]


def _extract_counts(row):
    """Extract subscriber counts per plan from a row."""
    s = int(_parse_num(row, "Starter_Count") or _parse_num(row, "Starter"))
    p = int(_parse_num(row, "Pro_Count") or _parse_num(row, "Pro"))
    e = int(_parse_num(row, "Enterprise_Count") or _parse_num(row, "Enterprise"))
    f = int(_parse_num(row, "Free_Trial") or _parse_num(row, "Trial"))
    return {"Free Trial": f, "Starter": s, "Pro": p, "Enterprise": e}


def plan_distribution(args):
    """Show distribution of subscribers by plan with ASCII bar chart."""
    rows = _get_mrr_rows()
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    current = _get_month_data(rows, month)

    # Aggregate counts
    totals = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
    for r in current:
        counts = _extract_counts(r)
        for plan in PLAN_ORDER:
            totals[plan] += counts[plan]

    grand = sum(totals.values()) or 1
    total_mrr = sum(totals[p] * PLAN_PRICES[p] for p in PLAN_ORDER)

    print("=" * 60)
    print(f"  📊 PLAN DISTRIBUTION — {month}")
    print("=" * 60)
    print(f"\n  {'Plan':<14} {'Subs':>6} {'Share':>7} {'MRR':>10} {'Bar'}")
    print(f"  {'─' * 55}")

    for plan in PLAN_ORDER:
        c = totals[plan]
        pct = c / grand * 100
        mrr = c * PLAN_PRICES[plan]
        bar_len = int(pct / 2) or (1 if c > 0 else 0)
        bar = "█" * bar_len
        print(f"  {plan:<14} {c:>6} {pct:>6.1f}% £{mrr:>8,.2f}  {bar}")

    print(f"  {'─' * 55}")
    print(f"  {'TOTAL':<14} {grand:>6} {'100%':>7} £{total_mrr:>8,.2f}")

    # ASCII pie chart (simplified ring)
    print(f"\n  Distribution Ring:")
    ring = ""
    for plan in PLAN_ORDER:
        pct = totals[plan] / grand * 100
        chars = max(1, round(pct / 5)) if totals[plan] > 0 else 0
        symbol = {"Free Trial": "○", "Starter": "●", "Pro": "◆", "Enterprise": "★"}[plan]
        ring += symbol * chars
    print(f"  [{ring}]")
    for plan in PLAN_ORDER:
        symbol = {"Free Trial": "○", "Starter": "●", "Pro": "◆", "Enterprise": "★"}[plan]
        print(f"    {symbol} = {plan}")

    # Revenue concentration
    if grand > 0 and totals["Enterprise"] > 0:
        ent_rev_pct = (totals["Enterprise"] * PLAN_PRICES["Enterprise"]) / total_mrr * 100 if total_mrr > 0 else 0
        print(f"\n  Enterprise revenue share: {ent_rev_pct:.0f}% of MRR from "
              f"{totals['Enterprise'] / grand * 100:.0f}% of subscribers")
    print("─" * 60)

    log_task(AGENT, f"Plan distribution for {month}",
             "Complete", "P2",
             f"total={grand}, mrr=£{total_mrr:,.2f}")


def churn_rate(args):
    """Calculate monthly churn rate and compare to SaaS benchmarks."""
    rows = _get_mrr_rows()
    month = args.month or datetime.now(timezone.utc).strftime("%Y-%m")

    # Parse target month and previous month
    target_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    prev_date = (target_date - timedelta(days=1)).replace(day=1)
    prev_month = prev_date.strftime("%Y-%m")

    current_rows = _get_month_data(rows, month)
    prev_rows = _get_month_data(rows, prev_month)

    # Aggregate
    curr_counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
    prev_counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}

    for r in current_rows:
        c = _extract_counts(r)
        for p in PLAN_ORDER:
            curr_counts[p] += c[p]
    for r in prev_rows:
        c = _extract_counts(r)
        for p in PLAN_ORDER:
            prev_counts[p] += c[p]

    prev_total = sum(prev_counts.values())
    curr_total = sum(curr_counts.values())
    prev_mrr = sum(prev_counts[p] * PLAN_PRICES[p] for p in PLAN_ORDER)
    curr_mrr = sum(curr_counts[p] * PLAN_PRICES[p] for p in PLAN_ORDER)

    # Customer churn
    lost_customers = max(0, prev_total - curr_total)
    cust_churn = lost_customers / prev_total if prev_total > 0 else 0

    # Revenue (MRR) churn
    lost_mrr = max(0, prev_mrr - curr_mrr)
    mrr_churn = lost_mrr / prev_mrr if prev_mrr > 0 else 0

    print("=" * 60)
    print(f"  📉 CHURN ANALYSIS — {month}")
    print("=" * 60)

    print(f"\n  {'Metric':<28} {'Previous':>10} {'Current':>10} {'Change':>10}")
    print(f"  {'─' * 62}")
    print(f"  {'Total Subscribers':<28} {prev_total:>10} {curr_total:>10} {curr_total - prev_total:>+10}")
    print(f"  {'MRR':<28} £{prev_mrr:>8,.2f} £{curr_mrr:>8,.2f} £{curr_mrr - prev_mrr:>+8,.2f}")

    print(f"\n  CHURN RATES")
    print(f"  {'─' * 45}")
    print(f"    Customer Churn:    {cust_churn:>8.1%}  ({lost_customers} lost)")
    print(f"    Revenue Churn:     {mrr_churn:>8.1%}  (£{lost_mrr:,.2f} lost)")

    # Per-plan churn
    print(f"\n  Per-Plan Churn:")
    for plan in PLAN_ORDER[1:]:  # Skip free trial
        prev_p = prev_counts[plan]
        curr_p = curr_counts[plan]
        lost = max(0, prev_p - curr_p)
        rate = lost / prev_p if prev_p > 0 else 0
        icon = "🟢" if rate <= SMB_CHURN_BENCHMARK_LOW else ("🟡" if rate <= SMB_CHURN_BENCHMARK_HIGH else "🔴")
        print(f"    {icon} {plan:<14} {rate:.1%} ({lost} lost of {prev_p})")

    print(f"\n  SaaS SMB Benchmark: {SMB_CHURN_BENCHMARK_LOW:.0%}-{SMB_CHURN_BENCHMARK_HIGH:.0%} monthly")
    if cust_churn <= SMB_CHURN_BENCHMARK_LOW:
        print(f"  ✅ Below benchmark — excellent retention")
    elif cust_churn <= SMB_CHURN_BENCHMARK_HIGH:
        print(f"  🟡 Within benchmark range — room for improvement")
    else:
        print(f"  🔴 Above benchmark — investigate churn drivers urgently")
    print("─" * 60)

    log_task(AGENT, f"Churn analysis for {month}",
             "Complete", "P1",
             f"customer_churn={cust_churn:.1%}, mrr_churn={mrr_churn:.1%}")


def expansion_revenue(args):
    """Track upgrade/expansion revenue and net revenue retention."""
    rows = _get_mrr_rows()
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    prev_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    prev_month = prev_date.strftime("%Y-%m")

    current_rows = _get_month_data(rows, month)
    prev_rows = _get_month_data(rows, prev_month)

    curr_counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
    prev_counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
    for r in current_rows:
        c = _extract_counts(r)
        for p in PLAN_ORDER:
            curr_counts[p] += c[p]
    for r in prev_rows:
        c = _extract_counts(r)
        for p in PLAN_ORDER:
            prev_counts[p] += c[p]

    prev_mrr = sum(prev_counts[p] * PLAN_PRICES[p] for p in PLAN_ORDER)
    curr_mrr = sum(curr_counts[p] * PLAN_PRICES[p] for p in PLAN_ORDER)

    # Estimate upgrades: growth in higher tiers that can't be explained by new subs
    upgrade_paths = [
        ("Starter → Pro", "Starter", "Pro"),
        ("Pro → Enterprise", "Pro", "Enterprise"),
        ("Free → Starter", "Free Trial", "Starter"),
    ]

    expansion_mrr = 0.0
    print("=" * 60)
    print(f"  ⬆️  EXPANSION REVENUE — {month}")
    print("=" * 60)
    print(f"\n  {'Upgrade Path':<22} {'Est. Upgrades':>14} {'MRR Impact':>12}")
    print(f"  {'─' * 52}")

    for label, from_plan, to_plan in upgrade_paths:
        # Estimate: decrease in lower plan subs that appear as increase in higher
        from_lost = max(0, prev_counts[from_plan] - curr_counts[from_plan])
        to_gained = max(0, curr_counts[to_plan] - prev_counts[to_plan])
        est_upgrades = min(from_lost, to_gained)
        mrr_diff = est_upgrades * (PLAN_PRICES[to_plan] - PLAN_PRICES[from_plan])
        expansion_mrr += mrr_diff
        print(f"  {label:<22} {est_upgrades:>14} £{mrr_diff:>10,.2f}")

    print(f"  {'─' * 52}")
    print(f"  {'Total Expansion MRR':<22} {'':<14} £{expansion_mrr:>10,.2f}")

    # Net Revenue Retention (NRR)
    contraction_mrr = max(0, prev_mrr - curr_mrr + expansion_mrr)
    nrr = ((curr_mrr) / prev_mrr * 100) if prev_mrr > 0 else 100

    print(f"\n  NET REVENUE RETENTION")
    print(f"  {'─' * 40}")
    print(f"    Starting MRR ({prev_month}):  £{prev_mrr:>10,.2f}")
    print(f"    Expansion MRR:           £{expansion_mrr:>10,.2f}")
    print(f"    Contraction MRR:        -£{contraction_mrr:>10,.2f}")
    print(f"    Ending MRR ({month}):    £{curr_mrr:>10,.2f}")
    print(f"\n    NRR: {nrr:.1f}%")

    if nrr >= 120:
        print(f"    🟢 Excellent — best-in-class SaaS (>120%)")
    elif nrr >= 100:
        print(f"    ✅ Healthy — net positive expansion (>100%)")
    elif nrr >= 90:
        print(f"    🟡 Moderate — aim to get above 100%")
    else:
        print(f"    🔴 Net negative — losing more than expanding")
    print("─" * 60)

    log_task(AGENT, f"Expansion revenue analysis for {month}",
             "Complete", "P2",
             f"expansion=£{expansion_mrr:,.2f}, nrr={nrr:.1f}%")


def downgrade_analysis(args):
    """Analyze downgrades and cancellations: patterns and timing."""
    rows = _get_mrr_rows()
    now = datetime.now(timezone.utc)

    # Analyze last 6 months of data
    months = []
    for i in range(5, -1, -1):
        d = now - timedelta(days=30 * i)
        months.append(d.strftime("%Y-%m"))

    print("=" * 60)
    print("  ⬇️  DOWNGRADE & CANCELLATION ANALYSIS")
    print("=" * 60)

    # Track MoM changes per plan
    monthly_counts = {}
    for m in months:
        month_rows = _get_month_data(rows, m)
        counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
        for r in month_rows:
            c = _extract_counts(r)
            for p in PLAN_ORDER:
                counts[p] += c[p]
        monthly_counts[m] = counts

    # Identify downgrades month over month
    print(f"\n  {'Month':<10}", end="")
    for plan in PLAN_ORDER[1:]:
        print(f" {plan:>11}", end="")
    print(f" {'Net Chg':>8}")
    print(f"  {'─' * 52}")

    total_downgrades = 0
    for i in range(1, len(months)):
        m = months[i]
        prev = monthly_counts[months[i - 1]]
        curr = monthly_counts[m]
        print(f"  {m:<10}", end="")
        net_change = 0
        for plan in PLAN_ORDER[1:]:
            diff = curr[plan] - prev[plan]
            net_change += diff
            icon = "▼" if diff < 0 else ("▲" if diff > 0 else " ")
            print(f" {icon}{diff:>+10}", end="")
            if diff < 0:
                total_downgrades += abs(diff)
        print(f" {net_change:>+8}")

    # Plan-specific loss analysis
    print(f"\n  PLAN VULNERABILITY")
    print(f"  {'─' * 45}")
    if len(months) >= 2:
        first_m = months[0]
        last_m = months[-1]
        for plan in PLAN_ORDER[1:]:
            initial = monthly_counts[first_m][plan]
            final = monthly_counts[last_m][plan]
            retention = (final / initial * 100) if initial > 0 else 100
            icon = "🟢" if retention >= 90 else ("🟡" if retention >= 75 else "🔴")
            print(f"    {icon} {plan:<14} {initial} → {final} ({retention:.0f}% retained over 6mo)")

    # Timing patterns
    print(f"\n  COMMON CHURN TIMING PATTERNS (SaaS industry):")
    print(f"    • Month 1-2: Trial friction → improve onboarding")
    print(f"    • Month 3-4: Value realisation gap → ensure aha moment")
    print(f"    • Month 7+:  Budget review cycles → demonstrate ROI")
    print(f"\n  Total estimated downgrades/cancellations (6mo): {total_downgrades}")

    # Recommendations
    print(f"\n  RECOMMENDED ACTIONS:")
    if total_downgrades > 10:
        print(f"    🔴 High churn detected — implement exit surveys")
        print(f"    🔴 Consider: win-back campaigns with 30% discount")
    elif total_downgrades > 5:
        print(f"    🟡 Moderate churn — review onboarding completion rates")
        print(f"    🟡 Consider: quarterly business reviews for Pro/Enterprise")
    else:
        print(f"    🟢 Low churn — maintain current retention strategy")
    print("─" * 60)

    log_task(AGENT, "Downgrade analysis completed",
             "Complete", "P2",
             f"period={months[0]}..{months[-1]}, downgrades={total_downgrades}")


def subscription_health(args):
    """Composite subscription health score logged to kpi_snapshots."""
    rows = _get_mrr_rows()
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    prev_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    prev_month = prev_date.strftime("%Y-%m")

    current_rows = _get_month_data(rows, month)
    prev_rows = _get_month_data(rows, prev_month)

    # Aggregate counts
    curr_counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
    prev_counts = {"Free Trial": 0, "Starter": 0, "Pro": 0, "Enterprise": 0}
    for r in current_rows:
        c = _extract_counts(r)
        for p in PLAN_ORDER:
            curr_counts[p] += c[p]
    for r in prev_rows:
        c = _extract_counts(r)
        for p in PLAN_ORDER:
            prev_counts[p] += c[p]

    prev_total = sum(prev_counts.values())
    curr_total = sum(curr_counts.values())
    prev_mrr = sum(prev_counts[p] * PLAN_PRICES[p] for p in PLAN_ORDER)
    curr_mrr = sum(curr_counts[p] * PLAN_PRICES[p] for p in PLAN_ORDER)

    # Metrics
    churn_rate_val = max(0, prev_total - curr_total) / prev_total if prev_total > 0 else 0
    nrr = (curr_mrr / prev_mrr * 100) if prev_mrr > 0 else 100
    trial_conversion = (curr_counts["Starter"] + curr_counts["Pro"] + curr_counts["Enterprise"]) / (
        curr_counts["Free Trial"] + curr_counts["Starter"] + curr_counts["Pro"] + curr_counts["Enterprise"]
    ) * 100 if curr_total > 0 else 0
    upgrade_ratio = (curr_counts["Pro"] + curr_counts["Enterprise"]) / curr_total * 100 if curr_total > 0 else 0

    # Score components (0-100 each)
    churn_score = max(0, min(100, (1 - churn_rate_val / 0.10) * 100))  # 0% = 100, 10% = 0
    nrr_score = max(0, min(100, (nrr - 80) / 0.4))                    # 80% = 0, 120% = 100
    trial_score = max(0, min(100, trial_conversion / 0.8))              # 80% conversion = 100
    upgrade_score = max(0, min(100, upgrade_ratio / 0.5))               # 50% on paid = 100

    weights = {"churn": 0.35, "nrr": 0.30, "trial": 0.20, "upgrade": 0.15}
    composite = (churn_score * weights["churn"] +
                 nrr_score * weights["nrr"] +
                 trial_score * weights["trial"] +
                 upgrade_score * weights["upgrade"])

    print("=" * 60)
    print(f"  🏥 SUBSCRIPTION HEALTH SCORE — {month}")
    print("=" * 60)

    def score_bar(score):
        filled = int(score / 5)
        return "█" * filled + "░" * (20 - filled)

    print(f"\n  {'Component':<22} {'Score':>6} {'Weight':>7}  Bar")
    print(f"  {'─' * 58}")
    print(f"  {'Churn Rate':<22} {churn_score:>5.0f}  {weights['churn']:>6.0%}  {score_bar(churn_score)}")
    print(f"    (Churn: {churn_rate_val:.1%})")
    print(f"  {'Net Revenue Retention':<22} {nrr_score:>5.0f}  {weights['nrr']:>6.0%}  {score_bar(nrr_score)}")
    print(f"    (NRR: {nrr:.1f}%)")
    print(f"  {'Trial Conversion':<22} {trial_score:>5.0f}  {weights['trial']:>6.0%}  {score_bar(trial_score)}")
    print(f"    (Conversion: {trial_conversion:.1f}%)")
    print(f"  {'Upgrade Ratio':<22} {upgrade_score:>5.0f}  {weights['upgrade']:>6.0%}  {score_bar(upgrade_score)}")
    print(f"    (Paid plan ratio: {upgrade_ratio:.1f}%)")

    print(f"\n  {'─' * 58}")
    print(f"  COMPOSITE SCORE: {composite:.0f}/100  {score_bar(composite)}")

    if composite >= 80:
        grade = "A — Excellent"
        icon = "🟢"
    elif composite >= 60:
        grade = "B — Good"
        icon = "🟢"
    elif composite >= 40:
        grade = "C — Needs Improvement"
        icon = "🟡"
    elif composite >= 20:
        grade = "D — At Risk"
        icon = "🟠"
    else:
        grade = "F — Critical"
        icon = "🔴"
    print(f"  Grade: {icon} {grade}")

    # Save to kpi_snapshots
    add_row("kpi_snapshots", {
        "Name": f"Subscription Health — {month}",
        "Metric": "subscription_health_score",
        "Value": round(composite, 1),
        "Date": now.strftime("%Y-%m-%d"),
        "Notes": json.dumps({
            "churn_rate": round(churn_rate_val, 4),
            "nrr": round(nrr, 1),
            "trial_conversion": round(trial_conversion, 1),
            "upgrade_ratio": round(upgrade_ratio, 1),
            "component_scores": {
                "churn": round(churn_score, 1),
                "nrr": round(nrr_score, 1),
                "trial": round(trial_score, 1),
                "upgrade": round(upgrade_score, 1),
            },
            "grade": grade,
        }),
    })
    print(f"\n  ✅ Saved to kpi_snapshots Notion DB")
    print("─" * 60)

    log_task(AGENT, f"Subscription health score: {composite:.0f}/100 ({grade})",
             "Complete", "P1",
             f"churn={churn_rate_val:.1%}, nrr={nrr:.1f}%, score={composite:.0f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Subscription Analyzer — Finance Agent")
    p.add_argument("--action", required=True,
                   choices=["plan-distribution", "churn-rate", "expansion-revenue",
                            "downgrade-analysis", "subscription-health"])
    p.add_argument("--month", help="Target month in YYYY-MM format")

    args = p.parse_args()
    actions = {
        "plan-distribution": plan_distribution,
        "churn-rate": churn_rate,
        "expansion-revenue": expansion_revenue,
        "downgrade-analysis": downgrade_analysis,
        "subscription-health": subscription_health,
    }
    actions[args.action](args)
