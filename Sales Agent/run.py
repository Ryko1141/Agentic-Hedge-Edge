#!/usr/bin/env python3
"""
Sales Agent — Task Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Routes sales tasks to execution scripts.

Usage:
    python "Sales Agent/run.py" --list-tasks
    python "Sales Agent/run.py" --status
    python "Sales Agent/run.py" --task crm-sync --action pipeline-report
    python "Sales Agent/run.py" --task demo-track --action upcoming
    python "Sales Agent/run.py" --task proposal --action list
"""

import sys
import os
import subprocess
import argparse

# ── Ensure workspace root is on sys.path ──────────────────────
_WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _WORKSPACE)

from shared.notion_client import log_task
from shared.api_registry import get_agent_apis

AGENT_NAME = "Sales"
AGENT_KEY = "sales"

# ──────────────────────────────────────────────
# Task Registry
# ──────────────────────────────────────────────
TASKS: dict[str, dict] = {
    "crm-sync": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "crm-management",
                               "execution", "crm_sync.py"),
        "description": "Manage the Leads CRM — add leads, update stages, pipeline reports",
    },
    "demo-track": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "demo-management",
                               "execution", "demo_tracker.py"),
        "description": "Track demo bookings, outcomes, and follow-ups",
    },
    "proposal": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "proposal-generation",
                               "execution", "proposal_manager.py"),
        "description": "Generate and manage sales proposals",
    },
    "call-schedule": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "call-scheduling",
                               "execution", "call_scheduler.py"),
        "description": "Schedule demo calls, track outcomes, manage follow-ups",
    },
    "lead-qualify": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "lead-qualification",
                               "execution", "lead_qualifier.py"),
        "description": "Qualify leads using BANT + trading-specific signals",
    },
    "pipeline": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "sales-pipeline",
                               "execution", "sales_pipeline.py"),
        "description": "Full sales pipeline — stage tracking, velocity, forecasting",
    },
}


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_list_tasks() -> None:
    print("=" * 60)
    print(f"  💼 {AGENT_NAME} Agent — Available Tasks")
    print("=" * 60)
    for name, info in sorted(TASKS.items()):
        exists = "✅" if os.path.isfile(info["script"]) else "❌"
        print(f"\n  {exists} {name}")
        print(f"     {info['description']}")
    print(f"\n{'─' * 60}")
    print(f"  {len(TASKS)} tasks registered")


def cmd_status() -> None:
    apis = get_agent_apis(AGENT_KEY)
    ready = sum(1 for t in TASKS.values() if os.path.isfile(t["script"]))
    print("=" * 60)
    print(f"  💼 {AGENT_NAME} Agent — Status")
    print("=" * 60)
    print(f"\n  Tasks: {ready}/{len(TASKS)} ready")
    print(f"  APIs:  {', '.join(f'{k} ({v})' for k, v in sorted(apis.items()))}")
    for name, info in sorted(TASKS.items()):
        exists = "✅" if os.path.isfile(info["script"]) else "❌"
        print(f"  {exists} {name}")
    print()


def cmd_run(task: str, action: str, extra: list[str]) -> None:
    info = TASKS.get(task)
    if not info:
        print(f"❌ Unknown task: {task}")
        print(f"   Available: {', '.join(sorted(TASKS.keys()))}")
        sys.exit(1)

    script = info["script"]
    if not os.path.isfile(script):
        print(f"❌ Script not found: {script}")
        sys.exit(1)

    cmd = [sys.executable, script, "--action", action, *extra]
    result = subprocess.run(cmd, check=False)

    status = "Complete" if result.returncode == 0 else "Error"
    try:
        log_task(
            agent=AGENT_NAME,
            task=f"{task}/{action}",
            status=status,
            priority="P2",
            output_summary=f"Ran {task} --action {action}",
            error=f"exit code {result.returncode}" if result.returncode != 0 else "",
        )
    except Exception as exc:
        print(f"⚠️  Could not log to Notion: {exc}")

    if result.returncode != 0:
        sys.exit(result.returncode)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{AGENT_NAME} Agent — Task Dispatcher",
    )
    parser.add_argument("--list-tasks", action="store_true",
                        help="Show available tasks")
    parser.add_argument("--status", action="store_true",
                        help="Show agent status summary")
    parser.add_argument("--task", metavar="TASK",
                        help="Task to run (e.g., crm-sync, demo-track, proposal)")
    parser.add_argument("--action", metavar="ACTION",
                        help="Action within the task")

    args, extra = parser.parse_known_args()

    if args.list_tasks:
        cmd_list_tasks()
    elif args.status:
        cmd_status()
    elif args.task and args.action:
        cmd_run(args.task, args.action, extra)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
