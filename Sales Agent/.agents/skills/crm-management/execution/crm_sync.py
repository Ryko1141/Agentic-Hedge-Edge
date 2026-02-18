#!/usr/bin/env python3
"""
crm_sync.py — Sales Agent CRM Management

Manages the Leads CRM database in Notion. Add leads, update stages,
generate pipeline reports, and track follow-ups.

Usage:
    python crm_sync.py --action add-lead --name "John Doe" --email "john@email.com" --source Discord --plan Starter
    python crm_sync.py --action update-stage --name "John Doe" --stage Demo
    python crm_sync.py --action pipeline-report
    python crm_sync.py --action follow-up-list
"""

import sys, os, argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task


def add_lead(args):
    """Add a new lead to the CRM."""
    row = {
        "Name":          args.name,
        "Email":         args.email or "",
        "Source":        args.source or "Website",
        "Stage":         "New Lead",
        "Deal Value":    args.deal_value or 0,
        "Plan Interest": args.plan or "Starter",
        "Contact Date":  datetime.now().strftime("%Y-%m-%d"),
        "Follow Up":     (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
        "Notes":         args.notes or "",
        "Score":         args.score or 50,
    }
    add_row("leads_crm", row)
    print(f"✅ Lead added: {args.name}")
    print(f"   Source: {row['Source']} | Plan: {row['Plan Interest']} | Value: ${row['Deal Value']}")
    print(f"   Follow-up: {row['Follow Up']}")
    log_task("Sales", f"Added lead: {args.name}", "Complete", "P2",
             f"New lead from {row['Source']}, interested in {row['Plan Interest']}")


def update_stage(args):
    """Update a lead's pipeline stage."""
    leads = query_db("leads_crm", filter={
        "property": "Name", "title": {"equals": args.name}
    })
    if not leads:
        print(f"❌ Lead not found: {args.name}")
        return
    lead = leads[0]
    old_stage = lead.get("Stage", "Unknown")
    update_row(lead["_id"], "leads_crm", {"Stage": args.stage})
    print(f"✅ {args.name}: {old_stage} → {args.stage}")
    log_task("Sales", f"Stage update: {args.name}", "Complete", "P2",
             f"{old_stage} → {args.stage}")


def pipeline_report(args):
    """Generate a pipeline report grouped by stage."""
    leads = query_db("leads_crm")
    stages = {}
    for lead in leads:
        stage = lead.get("Stage", "Unknown")
        if stage not in stages:
            stages[stage] = {"count": 0, "value": 0, "leads": []}
        stages[stage]["count"] += 1
        stages[stage]["value"] += lead.get("Deal Value") or 0
        stages[stage]["leads"].append(lead.get("Name", "?"))

    stage_order = ["New Lead", "Contacted", "Discovery", "Demo", "Proposal", "Negotiation", "Won", "Lost"]
    print("=" * 60)
    print("  📈 SALES PIPELINE REPORT")
    print("=" * 60)
    total_value, total_leads = 0, 0
    for stage in stage_order:
        if stage in stages:
            s = stages[stage]
            print(f"\n  {stage} ({s['count']} leads | ${s['value']:,.0f})")
            for name in s["leads"][:5]:
                print(f"    • {name}")
            total_value += s["value"]
            total_leads += s["count"]
    print(f"\n{'─' * 60}")
    print(f"  Total: {total_leads} leads | ${total_value:,.0f} pipeline value")
    log_task("Sales", "Pipeline report", "Complete", "P3",
             f"{total_leads} leads, ${total_value:,.0f} value")


def follow_up_list(args):
    """List leads needing follow-up today or overdue."""
    today = datetime.now().strftime("%Y-%m-%d")
    leads = query_db("leads_crm", filter={
        "property": "Follow Up", "date": {"on_or_before": today}
    })
    actionable = [l for l in leads if l.get("Stage") not in ("Won", "Lost")]
    print("=" * 60)
    print("  📞 FOLLOW-UP LIST")
    print("=" * 60)
    if not actionable:
        print("\n  ✅ No follow-ups due!")
    for lead in actionable:
        fu = lead.get("Follow Up", "?")
        flag = " ⚠️ OVERDUE" if fu and fu < today else ""
        print(f"\n  {lead.get('Name', '?')}{flag}")
        print(f"    Stage: {lead.get('Stage')} | Email: {lead.get('Email', '?')}")
    print(f"\n  Total: {len(actionable)} action items")
    log_task("Sales", "Follow-up list", "Complete", "P3", f"{len(actionable)} follow-ups due")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sales CRM Management")
    parser.add_argument("--action", required=True,
                        choices=["add-lead", "update-stage", "pipeline-report", "follow-up-list"])
    parser.add_argument("--name", help="Lead name")
    parser.add_argument("--email", help="Lead email")
    parser.add_argument("--source", default="Website")
    parser.add_argument("--stage", help="Pipeline stage")
    parser.add_argument("--plan", default="Starter")
    parser.add_argument("--deal-value", type=float, default=0, dest="deal_value")
    parser.add_argument("--score", type=int, default=50)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    {"add-lead": add_lead, "update-stage": update_stage,
     "pipeline-report": pipeline_report, "follow-up-list": follow_up_list}[args.action](args)
