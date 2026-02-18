#!/usr/bin/env python3
"""
Hedge Edge — Orchestrator Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Master entry point. Routes tasks to the correct agent's run.py.

Usage:
    python "Orchestrator Agent/run.py" --agent sales --task crm-sync --action list
    python "Orchestrator Agent/run.py" --agent analytics --task kpi-snapshot --action latest
    python "Orchestrator Agent/run.py" --list-agents
    python "Orchestrator Agent/run.py" --list-tasks sales
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime

# ── Ensure workspace root is on sys.path ──────────────────────
_WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WORKSPACE)

from shared.notion_client import log_task
from shared.api_registry import get_agent_apis, can_access

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────
# Internal Task Registry (Orchestrator's own skills)
# ──────────────────────────────────────────────
INTERNAL_TASKS: dict[str, dict] = {
    "route": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "agent-routing",
                               "execution", "agent_router.py"),
        "description": "Classify intent and route requests to the correct agent",
    },
    "coordinate": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "cross-agent-coordination",
                               "execution", "cross_agent_coordinator.py"),
        "description": "Run multi-agent workflows and coordinate cross-agent tasks",
    },
    "decompose": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "task-decomposition",
                               "execution", "task_decomposer.py"),
        "description": "Break complex requests into atomic sub-tasks with dependency DAG",
    },
    "status": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "status-reporting",
                               "execution", "status_aggregator.py"),
        "description": "Aggregate status across all agents and Notion databases",
    },
}

# ──────────────────────────────────────────────
# Agent Registry
# ──────────────────────────────────────────────
AGENTS: dict[str, dict] = {
    "analytics": {
        "folder": "Analytics Agent",
        "key": "analytics",
        "description": "KPI dashboards, funnel analytics, and performance metrics",
    },
    "business-strategist": {
        "folder": "Business Strategist Agent",
        "key": "business_strategist",
        "description": "Competitive intelligence, growth strategy, partnerships, revenue",
    },
    "community-manager": {
        "folder": "Community Manager Agent",
        "key": "community_manager",
        "description": "Feedback collection, support triage, community events",
    },
    "content-engine": {
        "folder": "Content Engine Agent",
        "key": "content_engine",
        "description": "Content scheduling, video production pipeline",
    },
    "finance": {
        "folder": "Finance Agent",
        "key": "finance",
        "description": "IB commissions, MRR tracking, P&L, expenses",
    },
    "marketing": {
        "folder": "Marketing Agent",
        "key": "marketing",
        "description": "Ad campaigns, email marketing, SEO strategy",
    },
    "product": {
        "folder": "Product Agent",
        "key": "product",
        "description": "Bug triage, feature roadmap, release management",
    },
    "sales": {
        "folder": "Sales Agent",
        "key": "sales",
        "description": "CRM management, demo tracking, proposal generation",
    },
    "orchestrator": {
        "folder": "Orchestrator Agent",
        "key": "orchestrator",
        "description": "Master dispatcher and status reporting",
    },
}


def _agent_run_py(agent_slug: str) -> str:
    """Return the absolute path to an agent's run.py."""
    info = AGENTS[agent_slug]
    return os.path.join(_WORKSPACE, info["folder"], "run.py")


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_list_internal_tasks() -> None:
    """Print all Orchestrator internal tasks."""
    print("=" * 65)
    print("  🏢 ORCHESTRATOR — Internal Tasks")
    print("=" * 65)
    for name, info in sorted(INTERNAL_TASKS.items()):
        exists = "✅" if os.path.isfile(info["script"]) else "❌"
        print(f"\n  {exists} {name}")
        print(f"     {info['description']}")
    print(f"\n{'─' * 65}")
    print(f"  {len(INTERNAL_TASKS)} internal tasks registered")


def cmd_run_internal(task: str, action: str, extra: list[str]) -> None:
    """Run an Orchestrator internal task."""
    info = INTERNAL_TASKS.get(task)
    if not info:
        print(f"❌ Unknown internal task: {task}")
        print(f"   Available: {', '.join(sorted(INTERNAL_TASKS.keys()))}")
        sys.exit(1)
    script = info["script"]
    if not os.path.isfile(script):
        print(f"❌ Script not found: {script}")
        sys.exit(1)
    cmd = [sys.executable, script, "--action", action, *extra]
    result = subprocess.run(cmd, check=False)
    status = "Complete" if result.returncode == 0 else "Error"
    try:
        log_task("Orchestrator", f"internal:{task}/{action}", status, "P2",
                 f"Ran {task} --action {action}")
    except Exception:
        pass
    if result.returncode != 0:
        sys.exit(result.returncode)


def cmd_list_agents() -> None:
    """Print all registered agents and their API access."""
    print("=" * 65)
    print("  🏢 HEDGE EDGE — AGENT ROSTER")
    print("=" * 65)
    for slug, info in sorted(AGENTS.items()):
        apis = get_agent_apis(info["key"])
        api_list = ", ".join(sorted(apis.keys())) if apis else "(none)"
        print(f"\n  {slug}")
        print(f"    {info['description']}")
        print(f"    APIs: {api_list}")
    print(f"\n{'─' * 65}")
    print(f"  {len(AGENTS)} agents registered")


def cmd_list_tasks(agent_slug: str) -> None:
    """Delegate to the agent's run.py --list-tasks."""
    run_py = _agent_run_py(agent_slug)
    if not os.path.isfile(run_py):
        print(f"❌ No run.py found for agent '{agent_slug}' at {run_py}")
        sys.exit(1)
    subprocess.run([sys.executable, run_py, "--list-tasks"], check=False)


def cmd_dispatch(agent_slug: str, task: str, action: str, extra: list[str]) -> None:
    """Route a task to the target agent's run.py."""
    info = AGENTS.get(agent_slug)
    if not info:
        print(f"❌ Unknown agent: {agent_slug}")
        print(f"   Available: {', '.join(sorted(AGENTS.keys()))}")
        sys.exit(1)

    run_py = _agent_run_py(agent_slug)
    if not os.path.isfile(run_py):
        print(f"❌ No run.py found for agent '{agent_slug}' at {run_py}")
        sys.exit(1)

    # Validate the agent has Notion access (minimum requirement)
    if not can_access(info["key"], "notion", "read"):
        print(f"❌ Agent '{agent_slug}' has no Notion access — cannot execute tasks.")
        sys.exit(1)

    # Build the subprocess command
    cmd = [sys.executable, run_py, "--task", task, "--action", action, *extra]

    print(f"🚀 Dispatching: {agent_slug} → {task} → {action}")
    print(f"   Command: {' '.join(cmd)}")
    print("─" * 65)

    started = datetime.now()
    result = subprocess.run(cmd, check=False)
    elapsed = (datetime.now() - started).total_seconds()

    status = "Complete" if result.returncode == 0 else "Error"
    error_msg = f"exit code {result.returncode}" if result.returncode != 0 else ""

    # Audit to Notion task_log
    try:
        log_task(
            agent="Orchestrator",
            task=f"dispatch:{agent_slug}/{task}/{action}",
            status=status,
            priority="P2",
            output_summary=f"Dispatched to {info['folder']} in {elapsed:.1f}s",
            error=error_msg,
        )
    except Exception as exc:
        print(f"⚠️  Could not log dispatch to Notion: {exc}")

    if result.returncode != 0:
        print(f"\n❌ Agent returned exit code {result.returncode}")
        sys.exit(result.returncode)
    else:
        print(f"\n✅ Done in {elapsed:.1f}s")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hedge Edge — Orchestrator Dispatcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python "Orchestrator Agent/run.py" --list-agents
  python "Orchestrator Agent/run.py" --list-tasks sales
  python "Orchestrator Agent/run.py" --agent sales --task crm-sync --action pipeline-report
  python "Orchestrator Agent/run.py" --agent analytics --task kpi-snapshot --action weekly-report
        """,
    )
    parser.add_argument("--list-agents", action="store_true",
                        help="Show all registered agents")
    parser.add_argument("--list-internal", action="store_true",
                        help="Show Orchestrator internal tasks")
    parser.add_argument("--internal-task", metavar="TASK",
                        help="Run an Orchestrator internal task (route, coordinate, decompose, status)")
    parser.add_argument("--list-tasks", metavar="AGENT",
                        help="Show available tasks for an agent")
    parser.add_argument("--agent", metavar="AGENT",
                        help="Target agent slug (e.g., sales, analytics)")
    parser.add_argument("--task", metavar="TASK",
                        help="Task name to run (e.g., crm-sync, kpi-snapshot)")
    parser.add_argument("--action", metavar="ACTION",
                        help="Action within the task (passed to execution script)")

    args, extra = parser.parse_known_args()

    if args.list_agents:
        cmd_list_agents()
    elif args.list_internal:
        cmd_list_internal_tasks()
    elif args.internal_task and args.action:
        cmd_run_internal(args.internal_task, args.action, extra)
    elif args.list_tasks:
        slug = args.list_tasks.lower().replace("_", "-").replace(" ", "-")
        if slug not in AGENTS:
            print(f"❌ Unknown agent: {slug}")
            print(f"   Available: {', '.join(sorted(AGENTS.keys()))}")
            sys.exit(1)
        cmd_list_tasks(slug)
    elif args.agent and args.task and args.action:
        slug = args.agent.lower().replace("_", "-").replace(" ", "-")
        if slug not in AGENTS:
            print(f"❌ Unknown agent: {slug}")
            print(f"   Available: {', '.join(sorted(AGENTS.keys()))}")
            sys.exit(1)
        cmd_dispatch(slug, args.task, args.action, extra)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
