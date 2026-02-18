#!/usr/bin/env python3
"""
Community Manager Agent — Task Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Routes community tasks to execution scripts.

Usage:
    python "Community Manager Agent/run.py" --list-tasks
    python "Community Manager Agent/run.py" --status
    python "Community Manager Agent/run.py" --task feedback --action collect
    python "Community Manager Agent/run.py" --task tickets --action open-list
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

AGENT_NAME = "Community Manager"
AGENT_KEY = "community_manager"

# ──────────────────────────────────────────────
# Task Registry
# ──────────────────────────────────────────────
TASKS: dict[str, dict] = {
    "feedback": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "feedback-collection",
                               "execution", "feedback_collector.py"),
        "description": "Collect and categorize user feedback from multiple channels",
    },
    "tickets": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "support-triage",
                               "execution", "ticket_manager.py"),
        "description": "Manage support tickets — triage, assign, escalate, resolve",
    },
    "events": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "community-events",
                               "execution", "community_events_manager.py"),
        "description": "Plan and manage community events — AMAs, workshops, webinars",
    },
    "discord": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "discord-management",
                               "execution", "discord_manager.py"),
        "description": "Discord server health, moderation, growth, and activity reports",
    },
    "retention": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "retention-engagement",
                               "execution", "retention_engagement.py"),
        "description": "Monitor member retention, engagement campaigns, leaderboards",
    },
    "onboarding": {
        "script": os.path.join(_AGENT_DIR, ".agents", "skills", "user-onboarding",
                               "execution", "user_onboarding.py"),
        "description": "Track user onboarding flow — signup to first hedge",
    },
}


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_list_tasks() -> None:
    print("=" * 60)
    print(f"  🤝 {AGENT_NAME} Agent — Available Tasks")
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
    print(f"  🤝 {AGENT_NAME} Agent — Status")
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
                        help="Task to run (e.g., feedback, tickets)")
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
