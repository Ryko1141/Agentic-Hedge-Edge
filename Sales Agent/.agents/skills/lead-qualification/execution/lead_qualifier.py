#!/usr/bin/env python3
"""
lead_qualifier.py — Sales Agent Lead Qualification

Qualify leads using BANT framework (Budget, Authority, Need, Timeline)
with trading-specific scoring signals for prop-firm traders.

Usage:
    python lead_qualifier.py --action qualify --email john@trader.com
    python lead_qualifier.py --action bulk-qualify
    python lead_qualifier.py --action sql-list
    python lead_qualifier.py --action qualification-report
"""

import sys, os, argparse, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

AGENT = "Sales"

# ──────────────────────────────────────────────
# BANT + Trading-Specific Scoring Matrix
# ──────────────────────────────────────────────
# Each criterion maps to a property/keyword check and a point value.

def _score_lead(lead: dict) -> dict:
    """Apply BANT + trading scoring to a lead dict. Returns scoring breakdown."""
    score = 0
    breakdown = {"Budget": [], "Authority": [], "Need": [], "Timeline": []}
    notes = (lead.get("Notes") or "").lower()
    source = (lead.get("Source") or "").lower()
    name = lead.get("Name", "")
    deal_value = lead.get("Deal Value") or 0

    # ── BUDGET (max 45 pts) ──
    if any(kw in notes for kw in ["funded", "funded account", "live account"]):
        score += 10
        breakdown["Budget"].append("Funded accounts (+10)")
    if any(kw in notes for kw in ["multiple accounts", "multi-account", "several accounts"]):
        score += 15
        breakdown["Budget"].append("Multiple accounts (+15)")
    if deal_value >= 50000 or any(kw in notes for kw in [">50k", "50k+", "100k", "manages"]):
        score += 20
        breakdown["Budget"].append("Manages >$50k total (+20)")

    # ── AUTHORITY (max 25 pts) ──
    if any(kw in notes for kw in ["account holder", "my account", "personal"]):
        score += 10
        breakdown["Authority"].append("Account holder (+10)")
    if any(kw in notes for kw in ["team", "fund manager", "managing", "group", "decision"]):
        score += 15
        breakdown["Authority"].append("Decision maker for team (+15)")

    # ── NEED (max 45 pts) ──
    if any(kw in notes for kw in ["failed challenge", "blown", "bust", "failed"]):
        score += 20
        breakdown["Need"].append("Failed challenges before (+20)")
    if any(kw in notes for kw in ["manual", "spreadsheet", "manually", "drawdown"]):
        score += 15
        breakdown["Need"].append("Managing drawdown manually (+15)")
    if any(kw in notes for kw in ["competitor", "using", "switched from", "current tool"]):
        score += 10
        breakdown["Need"].append("Using competitor (+10)")

    # ── TIMELINE (max 20 pts) ──
    if any(kw in notes for kw in ["asap", "now", "today", "urgent", "immediately"]):
        score += 20
        breakdown["Timeline"].append("Actively looking now (+20)")
    elif any(kw in notes for kw in ["this month", "30 days", "soon", "next week"]):
        score += 15
        breakdown["Timeline"].append("Within 30 days (+15)")
    elif any(kw in notes for kw in ["exploring", "researching", "looking into", "considering"]):
        score += 5
        breakdown["Timeline"].append("Exploring (+5)")

    # ── Source bonus ──
    if source in ("referral", "ib", "partner"):
        score += 10
        breakdown["Budget"].append("Referral/IB source (+10)")
    elif source in ("demo request", "cal.com"):
        score += 5
        breakdown["Timeline"].append("Direct demo request (+5)")

    # Determine tier
    if score >= 80:
        tier = "Opportunity"
    elif score >= 60:
        tier = "SQL"
    elif score >= 30:
        tier = "MQL"
    else:
        tier = "Unqualified"

    return {
        "score": score,
        "tier": tier,
        "breakdown": breakdown,
        "max_possible": 135,
    }


def qualify(args):
    """Qualify a single lead by email."""
    leads = query_db("leads_crm", filter={
        "property": "Email", "email": {"equals": args.email}
    })
    if not leads:
        print(f"❌ Lead not found: {args.email}")
        print("   Check the email address or add the lead first via crm_sync.py")
        return

    lead = leads[0]
    result = _score_lead(lead)

    # Update lead in Notion
    update_row(lead["_id"], "leads_crm", {
        "Score": result["score"],
        "Stage": result["tier"] if lead.get("Stage") in ("New Lead", None, "") else lead.get("Stage"),
    })

    print("=" * 60)
    print("  🎯 LEAD QUALIFICATION")
    print("=" * 60)
    print(f"  Lead:    {lead.get('Name', '?')}")
    print(f"  Email:   {args.email}")
    print(f"  Score:   {result['score']}/{result['max_possible']}")
    print(f"  Tier:    {result['tier']}")
    print(f"\n  {'─' * 44}")
    print("  BANT Breakdown:")
    for category, items in result["breakdown"].items():
        if items:
            print(f"    {category}:")
            for item in items:
                print(f"      ✓ {item}")
        else:
            print(f"    {category}: (no signals detected)")
    print("─" * 60)

    if result["tier"] == "Unqualified":
        print("  💡 Tip: Add more context to the lead's Notes field (funded accounts,")
        print("     challenge history, timeline) to improve qualification accuracy.")

    log_task(AGENT, f"Qualified lead: {args.email}",
             "Complete", "P2", f"Score {result['score']}, Tier: {result['tier']}")


def bulk_qualify(args):
    """Run BANT qualification across all unqualified/unscored leads."""
    leads = query_db("leads_crm")
    unqualified = [l for l in leads if not l.get("Score") or l.get("Score") == 0]

    print("=" * 60)
    print("  🔄 BULK LEAD QUALIFICATION")
    print("=" * 60)

    if not unqualified:
        print(f"\n  ✅ All {len(leads)} leads already qualified!")
        print("─" * 60)
        log_task(AGENT, "Bulk qualify", "Complete", "P3", "No unqualified leads")
        return

    results = {"Opportunity": 0, "SQL": 0, "MQL": 0, "Unqualified": 0}
    for lead in unqualified:
        result = _score_lead(lead)
        update_row(lead["_id"], "leads_crm", {
            "Score": result["score"],
            "Stage": result["tier"] if lead.get("Stage") in ("New Lead", None, "") else lead.get("Stage"),
        })
        results[result["tier"]] += 1
        print(f"  {lead.get('Name', '?'):<30} Score: {result['score']:>3}  → {result['tier']}")

    print(f"\n{'─' * 60}")
    print(f"  Processed: {len(unqualified)} leads")
    for tier, count in results.items():
        if count:
            print(f"    {tier:<16} {count}")

    summary = f"Qualified {len(unqualified)} leads: {results}"
    log_task(AGENT, "Bulk qualify", "Complete", "P2", summary)


def sql_list(args):
    """List all Sales Qualified Leads (score >= 60)."""
    leads = query_db("leads_crm")
    sqls = [l for l in leads if (l.get("Score") or 0) >= 60]
    sqls.sort(key=lambda l: l.get("Score", 0), reverse=True)

    print("=" * 60)
    print("  🏆 SALES QUALIFIED LEADS")
    print("=" * 60)

    if not sqls:
        print("\n  No SQLs yet. Run --action bulk-qualify to score leads.")
        print("─" * 60)
        log_task(AGENT, "SQL list", "Complete", "P3", "0 SQLs")
        return

    for lead in sqls:
        score = lead.get("Score", 0)
        tier = "OPP" if score >= 80 else "SQL"
        stage = lead.get("Stage", "?")
        plan = lead.get("Plan Interest", "?")
        value = lead.get("Deal Value") or 0

        print(f"\n  [{tier}] {lead.get('Name', '?')} — Score: {score}")
        print(f"    Email: {lead.get('Email', '?')}")
        print(f"    Stage: {stage} | Plan: {plan} | Value: ${value:,.0f}")
        if lead.get("Notes"):
            print(f"    Notes: {lead['Notes'][:80]}")

    total_value = sum(l.get("Deal Value") or 0 for l in sqls)
    print(f"\n{'─' * 60}")
    print(f"  Total SQLs: {len(sqls)} | Pipeline Value: ${total_value:,.0f}")

    log_task(AGENT, "SQL list", "Complete", "P3",
             f"{len(sqls)} SQLs, ${total_value:,.0f} value")


def qualification_report(args):
    """Show full qualification funnel with conversion rates."""
    leads = query_db("leads_crm")
    total = len(leads)

    tiers = {"Unqualified": [], "MQL": [], "SQL": [], "Opportunity": []}
    unscored = 0
    for lead in leads:
        score = lead.get("Score") or 0
        if score == 0:
            unscored += 1
            tiers["Unqualified"].append(lead)
        elif score >= 80:
            tiers["Opportunity"].append(lead)
        elif score >= 60:
            tiers["SQL"].append(lead)
        elif score >= 30:
            tiers["MQL"].append(lead)
        else:
            tiers["Unqualified"].append(lead)

    print("=" * 60)
    print("  📊 LEAD QUALIFICATION FUNNEL")
    print("=" * 60)

    if total == 0:
        print("\n  No leads in CRM yet.")
        print("─" * 60)
        log_task(AGENT, "Qualification report", "Complete", "P3", "0 leads")
        return

    funnel_stages = [
        ("Total Leads", total, "━"),
        ("MQL (30+)", len(tiers["MQL"]), "▓"),
        ("SQL (60+)", len(tiers["SQL"]), "█"),
        ("Opportunity (80+)", len(tiers["Opportunity"]), "█"),
    ]

    max_bar = 40
    for label, count, char in funnel_stages:
        pct = count / total * 100 if total else 0
        bar_len = int(count / total * max_bar) if total else 0
        bar = char * max(bar_len, 1) if count > 0 else ""
        print(f"\n  {label:<22} {count:>4} ({pct:>5.1f}%)")
        if bar:
            print(f"    {bar}")

    # Conversion rates
    mql_plus = len(tiers["MQL"]) + len(tiers["SQL"]) + len(tiers["Opportunity"])
    sql_plus = len(tiers["SQL"]) + len(tiers["Opportunity"])
    opp = len(tiers["Opportunity"])

    print(f"\n  {'─' * 44}")
    print("  Conversion Rates:")
    print(f"    Lead → MQL:    {mql_plus / total * 100:.1f}%" if total else "    Lead → MQL:    N/A")
    print(f"    MQL → SQL:     {sql_plus / mql_plus * 100:.1f}%" if mql_plus else "    MQL → SQL:     N/A")
    print(f"    SQL → Opp:     {opp / sql_plus * 100:.1f}%" if sql_plus else "    SQL → Opp:     N/A")
    if unscored:
        print(f"\n  ⚠️  {unscored} leads unscored — run --action bulk-qualify")
    print("─" * 60)

    summary = (f"{total} leads: {len(tiers['MQL'])} MQL, "
               f"{len(tiers['SQL'])} SQL, {len(tiers['Opportunity'])} Opp")
    log_task(AGENT, "Qualification report", "Complete", "P3", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sales Lead Qualifier (BANT)")
    parser.add_argument("--action", required=True,
                        choices=["qualify", "bulk-qualify", "sql-list", "qualification-report"])
    parser.add_argument("--email", help="Lead email for single qualification")
    args = parser.parse_args()

    dispatch = {
        "qualify": qualify,
        "bulk-qualify": bulk_qualify,
        "sql-list": sql_list,
        "qualification-report": qualification_report,
    }
    dispatch[args.action](args)
