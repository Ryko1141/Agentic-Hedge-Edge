#!/usr/bin/env python3
"""
cross_agent_coordinator.py — Orchestrator Cross-Agent Workflow Coordination

Manages multi-agent workflow execution: dispatches sub-tasks across specialist
agents, tracks dependencies, aggregates results, and detects conflicting
recommendations between agents.

Usage:
    python cross_agent_coordinator.py --action run-workflow --workflow launch-campaign
    python cross_agent_coordinator.py --action workflow-status --workflow-id WF-20260218-001
    python cross_agent_coordinator.py --action list-workflows
    python cross_agent_coordinator.py --action conflict-check
"""

import sys, os, argparse, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, update_row, log_task

# ── Pre-Defined Cross-Agent Workflows ────────────────────────────────

WORKFLOWS = {
    "launch-campaign": {
        "name": "Launch Campaign",
        "description": "End-to-end campaign launch across marketing, content, sales, and analytics.",
        "agents": ["Marketing", "Content Engine", "Sales", "Analytics"],
        "tasks": [
            {"step": 1, "agent": "Marketing",      "task": "Define campaign brief, audience segment, and KPIs",         "depends_on": []},
            {"step": 2, "agent": "Content Engine",  "task": "Produce campaign assets (video, copy, creatives)",          "depends_on": [1]},
            {"step": 3, "agent": "Marketing",       "task": "Set up email sequences and landing page",                  "depends_on": [1]},
            {"step": 4, "agent": "Sales",           "task": "Prepare lead capture pipeline and follow-up scripts",      "depends_on": [1]},
            {"step": 5, "agent": "Marketing",       "task": "Launch ads and distribute content",                        "depends_on": [2, 3]},
            {"step": 6, "agent": "Analytics",        "task": "Set up campaign tracking dashboard and attribution",       "depends_on": [5]},
            {"step": 7, "agent": "Sales",           "task": "Begin outbound follow-up on inbound leads",               "depends_on": [5, 4]},
        ],
    },
    "monthly-review": {
        "name": "Monthly Business Review",
        "description": "Cross-functional monthly review pulling data from all agents.",
        "agents": ["Finance", "Analytics", "Sales", "Marketing", "Product", "Community"],
        "tasks": [
            {"step": 1, "agent": "Finance",         "task": "Generate P&L snapshot and MRR report",                    "depends_on": []},
            {"step": 2, "agent": "Analytics",        "task": "Compile KPI dashboard and funnel metrics",                "depends_on": []},
            {"step": 3, "agent": "Sales",           "task": "Pipeline report and conversion analysis",                 "depends_on": []},
            {"step": 4, "agent": "Marketing",       "task": "Campaign performance and SEO ranking report",             "depends_on": []},
            {"step": 5, "agent": "Product",         "task": "Release log summary and roadmap status",                  "depends_on": []},
            {"step": 6, "agent": "Community",       "task": "Sentiment report and support ticket summary",             "depends_on": []},
            {"step": 7, "agent": "Business Strategist", "task": "Synthesize cross-agent data into strategic brief",    "depends_on": [1, 2, 3, 4, 5, 6]},
        ],
    },
    "feature-release": {
        "name": "Feature Release",
        "description": "Coordinate a new feature release across product, marketing, and community.",
        "agents": ["Product", "Marketing", "Content Engine", "Community", "Sales"],
        "tasks": [
            {"step": 1, "agent": "Product",         "task": "Finalize feature spec and QA sign-off",                   "depends_on": []},
            {"step": 2, "agent": "Product",         "task": "Deploy to production and update release log",             "depends_on": [1]},
            {"step": 3, "agent": "Marketing",       "task": "Draft announcement email and landing page update",        "depends_on": [2]},
            {"step": 4, "agent": "Content Engine",  "task": "Create demo video, social posts, changelog",              "depends_on": [2]},
            {"step": 5, "agent": "Community",       "task": "Post Discord announcement and update onboarding docs",    "depends_on": [2]},
            {"step": 6, "agent": "Sales",           "task": "Update pitch deck and notify pipeline leads",             "depends_on": [3, 4]},
        ],
    },
    "weekly-sprint": {
        "name": "Weekly Sprint Coordination",
        "description": "Weekly planning cycle across all active agents.",
        "agents": ["Business Strategist", "Product", "Marketing", "Sales", "Content Engine"],
        "tasks": [
            {"step": 1, "agent": "Business Strategist", "task": "Review OKR progress and set weekly priorities",       "depends_on": []},
            {"step": 2, "agent": "Product",         "task": "Groom backlog and assign sprint tasks",                   "depends_on": [1]},
            {"step": 3, "agent": "Marketing",       "task": "Plan weekly campaigns and content pushes",                "depends_on": [1]},
            {"step": 4, "agent": "Sales",           "task": "Set weekly outreach targets and demo slots",              "depends_on": [1]},
            {"step": 5, "agent": "Content Engine",  "task": "Schedule content calendar for the week",                  "depends_on": [3]},
        ],
    },
    "onboard-partner": {
        "name": "Partner Onboarding",
        "description": "Multi-step IB partner onboarding workflow.",
        "agents": ["Business Strategist", "Sales", "Finance", "Marketing", "Community"],
        "tasks": [
            {"step": 1, "agent": "Business Strategist", "task": "Validate partner fit and agreement terms",            "depends_on": []},
            {"step": 2, "agent": "Sales",           "task": "Create CRM entry and schedule kickoff call",              "depends_on": [1]},
            {"step": 3, "agent": "Finance",         "task": "Set up IB commission tracking and payout terms",          "depends_on": [1]},
            {"step": 4, "agent": "Marketing",       "task": "Create co-branded landing page and referral links",       "depends_on": [2]},
            {"step": 5, "agent": "Community",       "task": "Set up partner Discord channel and welcome sequence",     "depends_on": [2]},
        ],
    },
    "handle-complaint": {
        "name": "Complaint Resolution",
        "description": "Escalation workflow for customer complaints requiring multi-agent response.",
        "agents": ["Community", "Product", "Sales", "Business Strategist"],
        "tasks": [
            {"step": 1, "agent": "Community",       "task": "Log complaint, assess severity, send acknowledgment",     "depends_on": []},
            {"step": 2, "agent": "Product",         "task": "Investigate if complaint is a bug or missing feature",    "depends_on": [1]},
            {"step": 3, "agent": "Sales",           "task": "Check customer value and retention risk",                 "depends_on": [1]},
            {"step": 4, "agent": "Community",       "task": "Deliver resolution and follow-up message",                "depends_on": [2, 3]},
            {"step": 5, "agent": "Business Strategist", "task": "Log learnings and update process if systemic",        "depends_on": [4]},
        ],
    },
}


def _generate_workflow_id():
    """Generate a unique workflow ID."""
    return f"WF-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"


# ── Actions ───────────────────────────────────────────────────────────

def run_workflow(args):
    """Create and dispatch a multi-agent workflow."""
    wf_key = args.workflow
    if wf_key not in WORKFLOWS:
        print(f"❌ Unknown workflow: {wf_key}")
        print(f"   Available: {', '.join(WORKFLOWS.keys())}")
        return

    wf = WORKFLOWS[wf_key]
    wf_id = _generate_workflow_id()

    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  ▶️  DISPATCHING WORKFLOW: {wf['name']:<37}║")
    print(f"║  ID: {wf_id:<59}║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  {wf['description']:<64}║")
    print(f"║  Agents: {', '.join(wf['agents']):<55}║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    for step in wf["tasks"]:
        deps_str = f" (after step {step['depends_on']})" if step["depends_on"] else " (ready)"
        status = "Pending" if step["depends_on"] else "Dispatched"
        icon = "🔵" if status == "Dispatched" else "⬜"

        # Log each sub-task to Notion task_log
        add_row("task_log", {
            "Name":           f"[{wf_id}] Step {step['step']}: {step['task'][:50]}",
            "Agent":          step["agent"],
            "Status":         status,
            "Priority":       "P2",
            "Timestamp":      datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "Output Summary": json.dumps({"workflow_id": wf_id, "step": step["step"],
                                          "depends_on": step["depends_on"]}),
        })

        print(f"║  {icon} Step {step['step']}: [{step['agent']:<18}] {step['task'][:35]:<35}║")
        if step["depends_on"]:
            print(f"║     └─ depends on: step(s) {step['depends_on']!s:<36}║")

    dispatched = sum(1 for s in wf["tasks"] if not s["depends_on"])
    pending = len(wf["tasks"]) - dispatched

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  📨 Dispatched: {dispatched}  |  ⏳ Pending: {pending}  |  Total: {len(wf['tasks']):<13}║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    log_task("Orchestrator", f"Workflow dispatched: {wf['name']}", "In Progress", "P1",
             f"{wf_id}: {len(wf['tasks'])} tasks across {len(wf['agents'])} agents")
    return wf_id


def workflow_status(args):
    """Show status of all sub-tasks in a workflow."""
    wf_id = args.workflow_id
    if not wf_id:
        print("❌ --workflow-id is required"); return

    items = query_db("task_log")
    wf_tasks = [t for t in items if wf_id in (t.get("Name", "") or "")]
    wf_tasks.sort(key=lambda x: x.get("Name", ""))

    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  📋  WORKFLOW STATUS: {wf_id:<42}║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    if not wf_tasks:
        print(f"║  ⚠️  No tasks found for workflow {wf_id:<30}║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        return

    completed, in_progress, pending = 0, 0, 0
    for t in wf_tasks:
        status = t.get("Status", "Pending")
        agent = t.get("Agent", "?")
        name = (t.get("Name", "") or "").replace(f"[{wf_id}] ", "")
        if status == "Complete":
            icon = "✅"; completed += 1
        elif status == "In Progress" or status == "Dispatched":
            icon = "🔵"; in_progress += 1
        else:
            icon = "⬜"; pending += 1
        print(f"║  {icon} [{agent:<18}] {name[:40]:<40}║")

    total = len(wf_tasks)
    pct = (completed / total * 100) if total else 0
    bar_filled = int(pct / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Progress: {bar} {pct:>5.1f}%                      ║")
    print(f"║  ✅ {completed} complete  |  🔵 {in_progress} active  |  ⬜ {pending} pending            ║")
    print("╚══════════════════════════════════════════════════════════════════╝")


def list_workflows(args):
    """List all pre-defined workflows with their participants."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              📚  AVAILABLE CROSS-AGENT WORKFLOWS               ║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    for key, wf in WORKFLOWS.items():
        agent_str = ", ".join(wf["agents"][:4])
        extra = f" +{len(wf['agents']) - 4}" if len(wf["agents"]) > 4 else ""
        print(f"║                                                                  ║")
        print(f"║  📌 {wf['name']:<59}║")
        print(f"║     Key: --workflow {key:<43}║")
        print(f"║     {wf['description'][:60]:<60}    ║")
        print(f"║     Agents: {agent_str}{extra:<52}║")
        print(f"║     Steps: {len(wf['tasks']):<53}║")
        print(f"║{'─' * 66}║")

    print(f"║  Total workflows: {len(WORKFLOWS):<45}║")
    print("╚══════════════════════════════════════════════════════════════════╝")


def conflict_check(args):
    """Scan recent task_log for conflicting agent recommendations."""
    items = query_db("task_log")
    items.sort(key=lambda x: x.get("Timestamp", ""), reverse=True)
    recent = items[:100]  # Check last 100 tasks

    # Conflict detection heuristics
    CONFLICT_PATTERNS = [
        {"agents": ("Marketing", "Finance"),
         "signals": ("increase spend", "cut costs", "reduce budget", "scale ads", "cut expenses"),
         "desc": "Marketing wants to spend more while Finance wants to cut costs"},
        {"agents": ("Sales", "Product"),
         "signals": ("promise feature", "not on roadmap", "custom request", "roadmap"),
         "desc": "Sales promising features not on Product roadmap"},
        {"agents": ("Marketing", "Content Engine"),
         "signals": ("urgent campaign", "content backlog", "capacity", "deadline"),
         "desc": "Marketing campaign timelines conflicting with Content capacity"},
        {"agents": ("Business Strategist", "Sales"),
         "signals": ("enterprise pivot", "smb focus", "upmarket", "downmarket"),
         "desc": "Strategy and Sales misaligned on target segment"},
    ]

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║              ⚡  CROSS-AGENT CONFLICT CHECK                    ║")
    print("╠══════════════════════════════════════════════════════════════════╣")

    conflicts_found = 0
    task_texts = {t.get("Agent", ""): [] for t in recent}
    for t in recent:
        agent = t.get("Agent", "")
        text = ((t.get("Task", "") or "") + " " + (t.get("Output Summary", "") or "")).lower()
        task_texts.setdefault(agent, []).append(text)

    for pattern in CONFLICT_PATTERNS:
        a1, a2 = pattern["agents"]
        a1_texts = " ".join(task_texts.get(a1, []))
        a2_texts = " ".join(task_texts.get(a2, []))
        combined = a1_texts + " " + a2_texts

        signal_matches = [s for s in pattern["signals"] if s in combined]
        if len(signal_matches) >= 2:
            conflicts_found += 1
            print(f"║  ⚠️  POTENTIAL CONFLICT #{conflicts_found:<46}║")
            print(f"║     {a1} ↔ {a2:<53}║")
            print(f"║     {pattern['desc'][:60]:<60}    ║")
            print(f"║     Signals: {', '.join(signal_matches[:3]):<50}║")
            print(f"║{'─' * 66}║")

    if conflicts_found == 0:
        print("║  ✅ No cross-agent conflicts detected in recent activity.       ║")
    else:
        print(f"║  Total potential conflicts: {conflicts_found:<36}║")

    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Scanned: {len(recent)} recent tasks across {len(task_texts)} agents               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    log_task("Orchestrator", "Conflict check", "Complete", "P2",
             f"{conflicts_found} conflicts in {len(recent)} tasks")


# ── CLI ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrator Cross-Agent Workflow Coordinator")
    parser.add_argument("--action", required=True,
                        choices=["run-workflow", "workflow-status", "list-workflows", "conflict-check"])
    parser.add_argument("--workflow", help="Workflow key to run (e.g. launch-campaign, monthly-review)")
    parser.add_argument("--workflow-id", help="Workflow ID for status check (e.g. WF-20260218-001)")
    args = parser.parse_args()
    {"run-workflow": run_workflow, "workflow-status": workflow_status,
     "list-workflows": list_workflows, "conflict-check": conflict_check}[args.action](args)
