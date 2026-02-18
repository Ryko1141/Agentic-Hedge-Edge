#!/usr/bin/env python3
"""
Analytics Agent — Task Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Routes analytics tasks to execution scripts.

Usage:
    python "Analytics Agent/run.py" --list-tasks
    python "Analytics Agent/run.py" --status
    python "Analytics Agent/run.py" --task kpi-snapshot --action weekly-report
    python "Analytics Agent/run.py" --task funnel-calc --action snapshot
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

AGENT_NAME = "Analytics"
AGENT_KEY = "analytics"

# ──────────────────────────────────────────────
# Task Registry
# ──────────────────────────────────────────────
TASKS: dict[str, dict] = {
    "kpi-snapshot": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "kpi-dashboards",
                               "execution", "kpi_snapshot.py"),
        "description": "Take KPI snapshots, weekly reports, and trend analysis",
    },
    "funnel-calc": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "funnel-analytics",
                               "execution", "funnel_calculator.py"),
        "description": "Calculate conversion funnels and cohort metrics",
    },
    "ab-test": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "ab-testing",
                               "execution", "ab_test_manager.py"),
        "description": "Design, monitor, and analyze A/B tests with statistical rigor",
    },
    "attribution": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "attribution-modeling",
                               "execution", "attribution_modeler.py"),
        "description": "Multi-model marketing attribution analysis (first/last/linear)",
    },
    "cohort": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "cohort-analysis",
                               "execution", "cohort_analyzer.py"),
        "description": "Cohort retention analysis, LTV estimation, churn patterns",
    },
    "report": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "reporting-automation",
                               "execution", "report_automator.py"),
        "description": "Automated daily/weekly/monthly business reports",
    },
}


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_list_tasks() -> None:
    print("=" * 60)
    print(f"  📊 {AGENT_NAME} Agent — Available Tasks")
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
    print(f"  📊 {AGENT_NAME} Agent — Status")
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
                        help="Task to run (e.g., kpi-snapshot)")
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
