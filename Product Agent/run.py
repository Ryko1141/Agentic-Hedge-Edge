#!/usr/bin/env python3
"""
Product Agent — Task Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Routes product tasks to execution scripts.

Usage:
    python "Product Agent/run.py" --list-tasks
    python "Product Agent/run.py" --status
    python "Product Agent/run.py" --task bug-triage --action open-list
    python "Product Agent/run.py" --task roadmap --action sync
    python "Product Agent/run.py" --task releases --action latest
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

AGENT_NAME = "Product"
AGENT_KEY = "product"

# ──────────────────────────────────────────────
# Task Registry
# ──────────────────────────────────────────────
TASKS: dict[str, dict] = {
    "bug-triage": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "bug-triage",
                               "execution", "bug_triage_sync.py"),
        "description": "Triage bugs from GitHub issues and sync to Notion tracker",
    },
    "roadmap": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "feature-roadmap",
                               "execution", "roadmap_sync.py"),
        "description": "Sync feature roadmap between GitHub Projects and Notion",
    },
    "releases": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "release-management",
                               "execution", "release_tracker.py"),
        "description": "Track releases, changelogs, and deployment status",
    },
    "integrations": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "platform-integration",
                               "execution", "platform_integrator.py"),
        "description": "Track platform integrations — MT5, MT4, cTrader, broker APIs",
    },
    "qa": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "qa-automation",
                               "execution", "qa_automator.py"),
        "description": "QA test suites, test runs, quality metrics, coverage reports",
    },
    "user-feedback": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "user-feedback",
                               "execution", "user_feedback_sync.py"),
        "description": "Collect, categorize, and action user feedback into roadmap",
    },
}


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_list_tasks() -> None:
    print("=" * 60)
    print(f"  🛠️ {AGENT_NAME} Agent — Available Tasks")
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
    print(f"  🛠️ {AGENT_NAME} Agent — Status")
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
                        help="Task to run (e.g., bug-triage, roadmap, releases)")
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
