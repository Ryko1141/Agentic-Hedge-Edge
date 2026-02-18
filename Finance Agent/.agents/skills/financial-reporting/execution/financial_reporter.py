#!/usr/bin/env python3
"""
financial_reporter.py — Finance Agent Financial Reporting

Generate P&L statements, cash flow analysis, runway calculations,
and board-level financial reports for Hedge Edge Ltd.

Usage:
    python financial_reporter.py --action pnl --period monthly
    python financial_reporter.py --action pnl --period quarterly
    python financial_reporter.py --action cash-flow
    python financial_reporter.py --action runway --cash-balance 25000
    python financial_reporter.py --action snapshot
    python financial_reporter.py --action board-report --cash-balance 25000
"""

import sys, os, argparse, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Finance"

# Pricing
STARTER_PRICE = 29.0
PRO_PRICE = 59.0
ENTERPRISE_PRICE = 99.0


def _parse_amount(row):
    val = row.get("Amount") or row.get("Value") or row.get("Commission") or 0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _get_period_range(period):
    """Return (start_date_str, end_date_str, label) for the given period."""
    now = datetime.now(timezone.utc)
    if period == "monthly":
        start = now.replace(day=1)
        label = now.strftime("%B %Y")
    elif period == "quarterly":
        q_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=q_month, day=1)
        label = f"Q{(now.month - 1) // 3 + 1} {now.year}"
    else:  # ytd
        start = now.replace(month=1, day=1)
        label = f"YTD {now.year}"
    return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"), label


def _sum_revenue(start, end):
    """Sum revenue from mrr_tracker and ib_commissions in date range."""
    mrr_rows = query_db("mrr_tracker")
    ib_rows = query_db("ib_commissions")

    saas_rev = 0.0
    for r in mrr_rows:
        d = (r.get("Date") or "")[:10]
        if start <= d <= end:
            starter = int(r.get("Starter_Count") or r.get("Starter") or 0)
            pro = int(r.get("Pro_Count") or r.get("Pro") or 0)
            ent = int(r.get("Enterprise_Count") or r.get("Enterprise") or 0)
            mrr_val = _parse_amount(r)
            if mrr_val > 0:
                saas_rev += mrr_val
            else:
                saas_rev += starter * STARTER_PRICE + pro * PRO_PRICE + ent * ENTERPRISE_PRICE

    ib_rev = 0.0
    for r in ib_rows:
        d = (r.get("Date") or "")[:10]
        if start <= d <= end:
            ib_rev += _parse_amount(r)

    return saas_rev, ib_rev


def _sum_expenses(start, end):
    """Sum expenses from expense_log in date range, grouped by category."""
    rows = query_db("expense_log")
    by_cat = defaultdict(float)
    total = 0.0
    for r in rows:
        d = (r.get("Date") or "")[:10]
        if start <= d <= end:
            amt = _parse_amount(r)
            if amt > 0:  # positive = expense, negative = receivable
                cat = (r.get("Category") or "Other").capitalize()
                by_cat[cat] += amt
                total += amt
    return by_cat, total


def pnl(args):
    """Generate Profit & Loss statement for the specified period."""
    start, end, label = _get_period_range(args.period)
    saas_rev, ib_rev = _sum_revenue(start, end)
    expense_cats, total_expenses = _sum_expenses(start, end)

    total_revenue = saas_rev + ib_rev
    gross_profit = total_revenue - total_expenses
    gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    ebitda = gross_profit  # No D&A for a pre-launch SaaS

    print("=" * 60)
    print(f"  📊 PROFIT & LOSS — {label}")
    print(f"  Period: {start} to {end}")
    print("=" * 60)

    print(f"\n  REVENUE")
    print(f"  {'─' * 45}")
    print(f"    SaaS Subscriptions        £{saas_rev:>12,.2f}")
    print(f"    IB Commissions            £{ib_rev:>12,.2f}")
    print(f"  {'─' * 45}")
    print(f"    Total Revenue             £{total_revenue:>12,.2f}")

    print(f"\n  EXPENSES")
    print(f"  {'─' * 45}")
    for cat, amt in sorted(expense_cats.items(), key=lambda x: -x[1]):
        print(f"    {cat:<26} £{amt:>12,.2f}")
    print(f"  {'─' * 45}")
    print(f"    Total Expenses            £{total_expenses:>12,.2f}")

    print(f"\n  PROFITABILITY")
    print(f"  {'─' * 45}")
    print(f"    Gross Profit              £{gross_profit:>12,.2f}")
    print(f"    Gross Margin              {gross_margin:>12.1f}%")
    print(f"    EBITDA                    £{ebitda:>12,.2f}")

    if gross_profit < 0:
        print(f"\n  🔴 Net Loss: £{abs(gross_profit):,.2f}")
    else:
        print(f"\n  🟢 Net Profit: £{gross_profit:,.2f}")
    print("─" * 60)

    log_task(AGENT, f"Generated P&L for {label}",
             "Complete", "P1",
             f"revenue=£{total_revenue:,.2f}, expenses=£{total_expenses:,.2f}, "
             f"margin={gross_margin:.1f}%")


def cash_flow(args):
    """Generate cash flow statement: operating, investing, financing."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    label = now.strftime("%B %Y")

    saas_rev, ib_rev = _sum_revenue(start, end)
    _, total_expenses = _sum_expenses(start, end)

    operating_cf = (saas_rev + ib_rev) - total_expenses
    investing_cf = 0.0  # No capex currently
    financing_cf = 0.0  # No external funding currently
    net_cf = operating_cf + investing_cf + financing_cf
    burn_rate = total_expenses - (saas_rev + ib_rev) if operating_cf < 0 else 0

    print("=" * 60)
    print(f"  💸 CASH FLOW STATEMENT — {label}")
    print("=" * 60)

    print(f"\n  OPERATING ACTIVITIES")
    print(f"  {'─' * 45}")
    print(f"    Cash from Revenue         £{saas_rev + ib_rev:>12,.2f}")
    print(f"    Cash Paid (Expenses)     (£{total_expenses:>11,.2f})")
    print(f"    Net Operating CF          £{operating_cf:>12,.2f}")

    print(f"\n  INVESTING ACTIVITIES")
    print(f"  {'─' * 45}")
    print(f"    Capital Expenditure       £{investing_cf:>12,.2f}")

    print(f"\n  FINANCING ACTIVITIES")
    print(f"  {'─' * 45}")
    print(f"    External Funding          £{financing_cf:>12,.2f}")

    print(f"\n  {'═' * 45}")
    print(f"    NET CASH FLOW             £{net_cf:>12,.2f}")
    if burn_rate > 0:
        print(f"\n  🔥 Monthly Burn Rate: £{burn_rate:,.2f}")
    else:
        print(f"\n  ✅ Cash Flow Positive")
    print("─" * 60)

    log_task(AGENT, f"Cash flow statement for {label}",
             "Complete", "P2",
             f"operating=£{operating_cf:,.2f}, net=£{net_cf:,.2f}, burn=£{burn_rate:,.2f}")


def runway(args):
    """Calculate runway in months based on cash balance and burn rate."""
    now = datetime.now(timezone.utc)
    cash = args.cash_balance or 0.0

    # Calculate average monthly burn from last 3 months
    monthly_burns = []
    for i in range(1, 4):
        d = now - timedelta(days=30 * i)
        m_start = d.replace(day=1).strftime("%Y-%m-%d")
        m_end = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        m_end = m_end.strftime("%Y-%m-%d")
        saas, ib = _sum_revenue(m_start, m_end)
        _, expenses = _sum_expenses(m_start, m_end)
        net = expenses - (saas + ib)
        if net > 0:
            monthly_burns.append(net)

    avg_burn = sum(monthly_burns) / len(monthly_burns) if monthly_burns else 0
    runway_months = (cash / avg_burn) if avg_burn > 0 else float('inf')

    print("=" * 60)
    print("  ⏳ RUNWAY ANALYSIS")
    print("=" * 60)
    print(f"\n  Cash Balance:         £{cash:>12,.2f}")
    print(f"  Avg Monthly Burn:     £{avg_burn:>12,.2f}")

    if avg_burn > 0:
        print(f"  Runway:               {runway_months:>12.1f} months")
        depletion = now + timedelta(days=runway_months * 30)
        print(f"  Cash Zero Date:       {depletion.strftime('%Y-%m-%d'):>12}")
    else:
        print(f"  Runway:               {'∞ (no burn)':>12}")

    print(f"\n  {'─' * 45}")
    if runway_months < 3:
        print("  🚨 CRITICAL: <3 months runway — immediate action needed")
        print("     Consider: cut costs, raise emergency funding, or accelerate revenue")
    elif runway_months < 6:
        print("  ⚠️  WARNING: <6 months runway — begin fundraising conversations")
        print("     Target: extend to 12+ months through revenue growth or funding")
    elif runway_months < 12:
        print("  🟡 MODERATE: 6-12 months — monitor monthly, plan next funding round")
    else:
        print("  🟢 HEALTHY: 12+ months runway")

    # Scenario analysis
    print(f"\n  Scenario Analysis:")
    for label_sc, multiplier in [("Cut costs 20%", 0.8), ("No change", 1.0), ("Costs +20%", 1.2)]:
        adj_burn = avg_burn * multiplier
        r = (cash / adj_burn) if adj_burn > 0 else float('inf')
        marker = " ◀ current" if multiplier == 1.0 else ""
        print(f"    {label_sc:<18} → {r:.1f} months{marker}")
    print("─" * 60)

    log_task(AGENT, f"Runway analysis: {runway_months:.1f} months",
             "Complete", "P1",
             f"cash=£{cash:,.2f}, burn=£{avg_burn:,.2f}/mo")


def snapshot(args):
    """Take a P&L snapshot and save to pnl_snapshots Notion DB."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    label = now.strftime("%B %Y")

    saas_rev, ib_rev = _sum_revenue(start, end)
    expense_cats, total_expenses = _sum_expenses(start, end)
    total_revenue = saas_rev + ib_rev
    gross_profit = total_revenue - total_expenses
    gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

    row = {
        "Name": f"P&L Snapshot — {label}",
        "Date": now.strftime("%Y-%m-%d"),
        "Revenue": total_revenue,
        "SaaS_Revenue": saas_rev,
        "IB_Revenue": ib_rev,
        "Expenses": total_expenses,
        "Gross_Profit": gross_profit,
        "Gross_Margin": round(gross_margin, 1),
        "Notes": json.dumps({
            "expense_breakdown": {k: round(v, 2) for k, v in expense_cats.items()},
            "generated_at": now.isoformat(),
        }),
    }
    add_row("pnl_snapshots", row)

    print("=" * 60)
    print(f"  📸 P&L SNAPSHOT SAVED — {label}")
    print("=" * 60)
    print(f"\n  Revenue:      £{total_revenue:>10,.2f}")
    print(f"  Expenses:     £{total_expenses:>10,.2f}")
    print(f"  Gross Profit: £{gross_profit:>10,.2f}")
    print(f"  Margin:       {gross_margin:>10.1f}%")
    print(f"\n  ✅ Saved to pnl_snapshots Notion DB")
    print("─" * 60)

    log_task(AGENT, f"P&L snapshot saved for {label}",
             "Complete", "P1",
             f"revenue=£{total_revenue:,.2f}, profit=£{gross_profit:,.2f}")


def board_report(args):
    """Generate board-level financial summary."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    label = now.strftime("%B %Y")
    cash = args.cash_balance or 0.0

    saas_rev, ib_rev = _sum_revenue(start, end)
    _, total_expenses = _sum_expenses(start, end)
    total_revenue = saas_rev + ib_rev
    burn = max(0, total_expenses - total_revenue)
    runway_m = (cash / burn) if burn > 0 else float('inf')

    # Previous month for growth calc
    prev_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    prev_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_saas, prev_ib = _sum_revenue(prev_start, prev_end)
    prev_total = prev_saas + prev_ib
    growth = ((total_revenue - prev_total) / prev_total * 100) if prev_total > 0 else 0

    # Read leads for CAC
    leads = query_db("leads_crm")
    new_customers_month = len([l for l in leads
                               if (l.get("Date") or "")[:7] == now.strftime("%Y-%m")])
    marketing_spend = 0.0
    expenses_rows = query_db("expense_log")
    for r in expenses_rows:
        d = (r.get("Date") or "")[:10]
        if start <= d <= end and (r.get("Category") or "").lower() == "marketing":
            marketing_spend += _parse_amount(r)
    cac = (marketing_spend / new_customers_month) if new_customers_month > 0 else 0
    arpu = (total_revenue / new_customers_month) if new_customers_month > 0 else 0
    ltv = arpu * 12 * 0.85  # assume 85% annual retention

    print("=" * 60)
    print(f"  🏛️  BOARD FINANCIAL REPORT — {label}")
    print("=" * 60)

    print(f"\n  KEY METRICS")
    print(f"  {'─' * 45}")
    print(f"    MRR                       £{saas_rev:>12,.2f}")
    print(f"    IB Revenue                £{ib_rev:>12,.2f}")
    print(f"    Total Monthly Revenue     £{total_revenue:>12,.2f}")
    print(f"    MoM Growth                {growth:>12.1f}%")
    print(f"    ARR (projected)           £{total_revenue * 12:>12,.2f}")

    print(f"\n  BURN & RUNWAY")
    print(f"  {'─' * 45}")
    print(f"    Monthly Expenses          £{total_expenses:>12,.2f}")
    print(f"    Net Burn Rate             £{burn:>12,.2f}")
    print(f"    Cash on Hand              £{cash:>12,.2f}")
    runway_str = f"{runway_m:.1f} months" if runway_m < 999 else "∞"
    print(f"    Runway                    {runway_str:>12}")

    print(f"\n  UNIT ECONOMICS")
    print(f"  {'─' * 45}")
    print(f"    New Customers (month)     {new_customers_month:>12}")
    print(f"    CAC                       £{cac:>12,.2f}")
    print(f"    ARPU                      £{arpu:>12,.2f}")
    print(f"    Est. LTV                  £{ltv:>12,.2f}")
    ratio = (ltv / cac) if cac > 0 else 0
    print(f"    LTV:CAC Ratio             {ratio:>12.1f}x")
    if ratio >= 3:
        print(f"    ✅ Healthy (target >3x)")
    elif ratio >= 1:
        print(f"    ⚠️  Below target (aim for >3x)")
    else:
        print(f"    🔴 Unsustainable — CAC exceeds LTV")
    print("─" * 60)

    log_task(AGENT, f"Board report generated for {label}",
             "Complete", "P1",
             f"MRR=£{saas_rev:,.2f}, growth={growth:.1f}%, "
             f"burn=£{burn:,.2f}, runway={runway_str}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Financial Reporter — Finance Agent")
    p.add_argument("--action", required=True,
                   choices=["pnl", "cash-flow", "runway", "snapshot", "board-report"])
    p.add_argument("--period", choices=["monthly", "quarterly", "ytd"],
                   default="monthly", help="Reporting period")
    p.add_argument("--cash-balance", type=float, default=0.0,
                   help="Current cash balance for runway / board report")

    args = p.parse_args()
    actions = {
        "pnl": pnl,
        "cash-flow": cash_flow,
        "runway": runway,
        "snapshot": snapshot,
        "board-report": board_report,
    }
    actions[args.action](args)
