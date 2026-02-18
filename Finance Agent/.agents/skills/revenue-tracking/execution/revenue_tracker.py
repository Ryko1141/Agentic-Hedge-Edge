#!/usr/bin/env python3
"""
revenue_tracker.py — Finance Agent Revenue Tracking

Track all revenue streams: SaaS MRR, IB commissions, enterprise deals
for Hedge Edge Ltd.

Usage:
    python revenue_tracker.py --action record-mrr --month 2026-02 --starter-count 45 --pro-count 12 --enterprise-count 3
    python revenue_tracker.py --action mrr-trend
    python revenue_tracker.py --action revenue-breakdown
    python revenue_tracker.py --action arr-projection
    python revenue_tracker.py --action unit-economics
"""

import sys, os, argparse, json, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Finance"

# Pricing tiers (monthly)
STARTER_PRICE = 29.0
PRO_PRICE = 59.0
ENTERPRISE_PRICE = 99.0

PLAN_PRICES = {
    "Starter": STARTER_PRICE,
    "Pro": PRO_PRICE,
    "Enterprise": ENTERPRISE_PRICE,
}


def _parse_num(row, key, default=0):
    val = row.get(key, default)
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default


def _get_mrr_rows():
    return query_db("mrr_tracker")


def _calc_mrr(row):
    """Calculate MRR from a row's subscriber counts or direct Amount."""
    amount = _parse_num(row, "Amount")
    if amount > 0:
        return amount
    starter = int(_parse_num(row, "Starter_Count") or _parse_num(row, "Starter"))
    pro = int(_parse_num(row, "Pro_Count") or _parse_num(row, "Pro"))
    ent = int(_parse_num(row, "Enterprise_Count") or _parse_num(row, "Enterprise"))
    return starter * STARTER_PRICE + pro * PRO_PRICE + ent * ENTERPRISE_PRICE


def record_mrr(args):
    """Record monthly MRR with subscriber counts per plan."""
    starter_mrr = args.starter_count * STARTER_PRICE
    pro_mrr = args.pro_count * PRO_PRICE
    ent_mrr = args.enterprise_count * ENTERPRISE_PRICE
    total_mrr = starter_mrr + pro_mrr + ent_mrr
    total_subs = args.starter_count + args.pro_count + args.enterprise_count
    arpu = total_mrr / total_subs if total_subs > 0 else 0

    row = {
        "Name": f"MRR — {args.month}",
        "Date": f"{args.month}-01",
        "Starter_Count": args.starter_count,
        "Pro_Count": args.pro_count,
        "Enterprise_Count": args.enterprise_count,
        "Amount": total_mrr,
        "Total_Subscribers": total_subs,
        "ARPU": round(arpu, 2),
        "Notes": json.dumps({
            "starter_mrr": starter_mrr,
            "pro_mrr": pro_mrr,
            "enterprise_mrr": ent_mrr,
        }),
    }
    add_row("mrr_tracker", row)

    print("=" * 60)
    print(f"  💰 MRR RECORDED — {args.month}")
    print("=" * 60)

    print(f"\n  {'Plan':<14} {'Subs':>6} {'Price':>8} {'MRR':>12}")
    print(f"  {'─' * 44}")
    print(f"  {'Starter':<14} {args.starter_count:>6} £{STARTER_PRICE:>6,.0f} £{starter_mrr:>10,.2f}")
    print(f"  {'Pro':<14} {args.pro_count:>6} £{PRO_PRICE:>6,.0f} £{pro_mrr:>10,.2f}")
    print(f"  {'Enterprise':<14} {args.enterprise_count:>6} £{ENTERPRISE_PRICE:>6,.0f} £{ent_mrr:>10,.2f}")
    print(f"  {'─' * 44}")
    print(f"  {'TOTAL':<14} {total_subs:>6} {'':>8} £{total_mrr:>10,.2f}")
    print(f"\n  ARPU: £{arpu:,.2f}")
    print(f"  ARR (annualised): £{total_mrr * 12:,.2f}")
    print("─" * 60)

    log_task(AGENT, f"Recorded MRR for {args.month}: £{total_mrr:,.2f}",
             "Complete", "P1",
             f"subs={total_subs}, arpu=£{arpu:.2f}")


def mrr_trend(args):
    """Show MRR trend over last 12 months with MoM growth rate."""
    rows = _get_mrr_rows()

    # Group by month
    by_month = {}
    for r in rows:
        m = (r.get("Date") or "")[:7]
        if m:
            mrr = _calc_mrr(r)
            by_month[m] = max(by_month.get(m, 0), mrr)  # latest/highest for month

    months_sorted = sorted(by_month.keys())[-12:]

    print("=" * 60)
    print("  📈 MRR TREND — LAST 12 MONTHS")
    print("=" * 60)
    print(f"\n  {'Month':<10} {'MRR':>12} {'MoM':>8} {'Bar'}")
    print(f"  {'─' * 55}")

    prev_mrr = None
    max_mrr = max(by_month.values()) if by_month else 1
    for m in months_sorted:
        mrr = by_month[m]
        if prev_mrr and prev_mrr > 0:
            growth = ((mrr - prev_mrr) / prev_mrr) * 100
            growth_str = f"{growth:+.1f}%"
        else:
            growth_str = "  —"

        bar_len = int((mrr / max_mrr) * 25) if max_mrr > 0 else 0
        bar = "█" * bar_len
        print(f"  {m:<10} £{mrr:>10,.2f} {growth_str:>8}  {bar}")
        prev_mrr = mrr

    if len(months_sorted) >= 2:
        first = by_month[months_sorted[0]]
        last = by_month[months_sorted[-1]]
        total_growth = ((last - first) / first * 100) if first > 0 else 0
        cagr_months = len(months_sorted) - 1
        if first > 0 and last > 0 and cagr_months > 0:
            cmgr = (math.pow(last / first, 1 / cagr_months) - 1) * 100
        else:
            cmgr = 0
        print(f"\n  Period Growth: {total_growth:+.1f}%")
        print(f"  CMGR (compound monthly): {cmgr:.1f}%")
    print("─" * 60)

    log_task(AGENT, "MRR trend analysis",
             "Complete", "P2",
             f"{len(months_sorted)} months tracked, latest MRR=£{by_month.get(months_sorted[-1], 0):,.2f}" if months_sorted else "No data")


def revenue_breakdown(args):
    """Break down revenue: SaaS vs IB commissions vs enterprise."""
    mrr_rows = _get_mrr_rows()
    ib_rows = query_db("ib_commissions")

    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")

    # Current month SaaS
    saas_total = 0
    for r in mrr_rows:
        if (r.get("Date") or "")[:7] == month:
            saas_total += _calc_mrr(r)

    # Current month IB
    ib_total = 0
    ib_by_broker = defaultdict(float)
    for r in ib_rows:
        if (r.get("Date") or "")[:7] == month:
            amt = _parse_num(r, "Amount") or _parse_num(r, "Commission")
            ib_total += amt
            broker = r.get("Broker") or r.get("Name") or "Unknown"
            ib_by_broker[broker] += amt

    grand_total = saas_total + ib_total
    saas_pct = (saas_total / grand_total * 100) if grand_total > 0 else 0
    ib_pct = (ib_total / grand_total * 100) if grand_total > 0 else 0

    print("=" * 60)
    print(f"  💎 REVENUE BREAKDOWN — {month}")
    print("=" * 60)

    print(f"\n  {'Stream':<24} {'Amount':>12} {'Share':>8}")
    print(f"  {'─' * 48}")
    print(f"  {'SaaS Subscriptions':<24} £{saas_total:>10,.2f} {saas_pct:>7.1f}%")
    print(f"  {'IB Commissions':<24} £{ib_total:>10,.2f} {ib_pct:>7.1f}%")
    print(f"  {'─' * 48}")
    print(f"  {'TOTAL REVENUE':<24} £{grand_total:>10,.2f} {'100.0%':>8}")

    if ib_by_broker:
        print(f"\n  IB Commission by Broker:")
        for broker, amt in sorted(ib_by_broker.items(), key=lambda x: -x[1]):
            pct = amt / ib_total * 100 if ib_total > 0 else 0
            print(f"    {broker:<20} £{amt:>8,.2f} ({pct:.0f}%)")

    # Revenue concentration risk
    print(f"\n  Revenue Concentration:")
    if grand_total > 0:
        if max(saas_pct, ib_pct) > 80:
            print(f"  ⚠️  High concentration — {('SaaS' if saas_pct > ib_pct else 'IB')} "
                  f"= {max(saas_pct, ib_pct):.0f}% of revenue")
            print(f"      Diversify revenue streams to reduce risk")
        else:
            print(f"  ✅ Balanced revenue mix")
    else:
        print(f"  📭 No revenue recorded for {month}")
    print("─" * 60)

    log_task(AGENT, f"Revenue breakdown for {month}",
             "Complete", "P2",
             f"saas=£{saas_total:,.2f} ({saas_pct:.0f}%), ib=£{ib_total:,.2f} ({ib_pct:.0f}%)")


def arr_projection(args):
    """Project ARR from current MRR trajectory with linear and growth models."""
    rows = _get_mrr_rows()
    by_month = {}
    for r in rows:
        m = (r.get("Date") or "")[:7]
        if m:
            by_month[m] = max(by_month.get(m, 0), _calc_mrr(r))

    months_sorted = sorted(by_month.keys())

    current_mrr = by_month[months_sorted[-1]] if months_sorted else 0
    current_arr = current_mrr * 12

    # Calculate average MoM growth
    growth_rates = []
    for i in range(1, len(months_sorted)):
        prev = by_month[months_sorted[i - 1]]
        curr = by_month[months_sorted[i]]
        if prev > 0:
            growth_rates.append((curr - prev) / prev)

    avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0

    print("=" * 60)
    print("  🔮 ARR PROJECTION")
    print("=" * 60)
    print(f"\n  Current MRR: £{current_mrr:,.2f}")
    print(f"  Current ARR: £{current_arr:,.2f}")
    print(f"  Avg MoM Growth: {avg_growth * 100:.1f}%")

    # 12-month projections
    print(f"\n  {'Month':>8} {'Linear':>14} {'Growth Adj':>14} {'Aggressive':>14}")
    print(f"  {'─' * 56}")

    linear_mrr = current_mrr
    growth_mrr = current_mrr
    aggr_mrr = current_mrr
    monthly_add = by_month[months_sorted[-1]] - by_month[months_sorted[-2]] if len(months_sorted) >= 2 else 0

    now = datetime.now(timezone.utc)
    for i in range(1, 13):
        future = now + timedelta(days=30 * i)
        label = future.strftime("%Y-%m")

        linear_mrr += monthly_add
        growth_mrr *= (1 + avg_growth)
        aggr_mrr *= (1 + avg_growth * 1.5)  # 50% more aggressive growth

        print(f"  {label:>8} £{linear_mrr:>12,.2f} £{growth_mrr:>12,.2f} £{aggr_mrr:>12,.2f}")

    print(f"  {'─' * 56}")
    print(f"  12M ARR:")
    print(f"    Linear:     £{linear_mrr * 12:>12,.2f}")
    print(f"    Growth:     £{growth_mrr * 12:>12,.2f}")
    print(f"    Aggressive: £{aggr_mrr * 12:>12,.2f}")

    # Milestones
    milestones = [10000, 50000, 100000, 500000, 1000000]
    print(f"\n  ARR Milestones (growth-adjusted):")
    proj_mrr = current_mrr
    for i in range(1, 61):  # 5 years max
        proj_mrr *= (1 + avg_growth)
        proj_arr = proj_mrr * 12
        for ms in milestones[:]:
            if proj_arr >= ms:
                d = now + timedelta(days=30 * i)
                print(f"    £{ms:>10,} ARR → {d.strftime('%Y-%m')} (~{i} months)")
                milestones.remove(ms)
        if not milestones:
            break
    print("─" * 60)

    log_task(AGENT, "ARR projection generated",
             "Complete", "P2",
             f"current_arr=£{current_arr:,.2f}, avg_growth={avg_growth * 100:.1f}%/mo")


def unit_economics(args):
    """Calculate unit economics: ARPU, CAC, LTV, LTV:CAC ratio."""
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")

    # MRR and subscribers
    mrr_rows = _get_mrr_rows()
    current = [r for r in mrr_rows if (r.get("Date") or "")[:7] == month]
    total_mrr = sum(_calc_mrr(r) for r in current) if current else 0

    total_subs = 0
    for r in current:
        s = int(_parse_num(r, "Starter_Count") or _parse_num(r, "Starter"))
        p = int(_parse_num(r, "Pro_Count") or _parse_num(r, "Pro"))
        e = int(_parse_num(r, "Enterprise_Count") or _parse_num(r, "Enterprise"))
        total_subs += s + p + e

    arpu = total_mrr / total_subs if total_subs > 0 else 0

    # Marketing spend from expense_log
    expenses = query_db("expense_log")
    marketing_spend = sum(
        _parse_num(r, "Amount")
        for r in expenses
        if (r.get("Date") or "")[:7] == month
        and (r.get("Category") or "").lower() == "marketing"
    )

    # New customers from leads_crm
    leads = query_db("leads_crm")
    new_customers = len([
        l for l in leads
        if (l.get("Date") or "")[:7] == month
        and (l.get("Status") or "").lower() in ("converted", "customer", "active")
    ])

    cac = marketing_spend / new_customers if new_customers > 0 else 0

    # Churn and LTV
    avg_monthly_churn = 0.05  # 5% default assumption for SMB SaaS
    avg_lifetime_months = 1 / avg_monthly_churn if avg_monthly_churn > 0 else 24
    ltv = arpu * avg_lifetime_months
    ltv_cac = ltv / cac if cac > 0 else 0
    payback_months = cac / arpu if arpu > 0 else 0

    print("=" * 60)
    print(f"  🧮 UNIT ECONOMICS — {month}")
    print("=" * 60)

    print(f"\n  SUBSCRIBERS")
    print(f"  {'─' * 40}")
    print(f"    Total Subscribers:        {total_subs:>10}")
    print(f"    New This Month:           {new_customers:>10}")
    print(f"    MRR:                      £{total_mrr:>10,.2f}")

    print(f"\n  UNIT METRICS")
    print(f"  {'─' * 40}")
    print(f"    ARPU (monthly):           £{arpu:>10,.2f}")
    print(f"    Marketing Spend:          £{marketing_spend:>10,.2f}")
    print(f"    CAC:                      £{cac:>10,.2f}")
    print(f"    Est. Lifetime:            {avg_lifetime_months:>10.0f} months")
    print(f"    LTV:                      £{ltv:>10,.2f}")

    print(f"\n  EFFICIENCY")
    print(f"  {'─' * 40}")
    print(f"    LTV:CAC Ratio:            {ltv_cac:>10.1f}x")
    print(f"    CAC Payback:              {payback_months:>10.1f} months")

    # Benchmarks
    print(f"\n  SaaS Benchmarks:")
    benchmarks = [
        ("LTV:CAC", ltv_cac, 3.0, "x", "≥3x healthy"),
        ("CAC Payback", payback_months, 12.0, "mo", "≤12mo good"),
    ]
    for name, actual, target, unit, desc in benchmarks:
        if name == "LTV:CAC":
            ok = actual >= target
        else:
            ok = actual <= target and actual > 0
        icon = "✅" if ok else "⚠️"
        print(f"    {icon} {name}: {actual:.1f}{unit} (target: {desc})")

    # Revenue per marketing dollar
    rpm = total_mrr / marketing_spend if marketing_spend > 0 else 0
    print(f"\n    Revenue per £1 marketing: £{rpm:.2f}")
    print("─" * 60)

    log_task(AGENT, f"Unit economics for {month}",
             "Complete", "P2",
             f"arpu=£{arpu:.2f}, cac=£{cac:.2f}, ltv=£{ltv:.2f}, ratio={ltv_cac:.1f}x")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Revenue Tracker — Finance Agent")
    p.add_argument("--action", required=True,
                   choices=["record-mrr", "mrr-trend", "revenue-breakdown",
                            "arr-projection", "unit-economics"])
    p.add_argument("--month", help="Month in YYYY-MM format")
    p.add_argument("--starter-count", type=int, default=0, help="Number of Starter subscribers")
    p.add_argument("--pro-count", type=int, default=0, help="Number of Pro subscribers")
    p.add_argument("--enterprise-count", type=int, default=0, help="Number of Enterprise subscribers")

    args = p.parse_args()
    actions = {
        "record-mrr": record_mrr,
        "mrr-trend": mrr_trend,
        "revenue-breakdown": revenue_breakdown,
        "arr-projection": arr_projection,
        "unit-economics": unit_economics,
    }
    actions[args.action](args)
