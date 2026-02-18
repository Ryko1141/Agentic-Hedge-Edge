#!/usr/bin/env python3
"""
status_aggregator.py — Orchestrator Agent Status Reporting

Central task log and cross-agent status dashboard.  Pulls from task_log
to build daily summaries and per-agent status views.

Usage:
    python status_aggregator.py --action agent-status --agent "Sales Agent"
    python status_aggregator.py --action log-task --agent "Sales Agent" --task "Onboarded lead: Acme" --status Complete --priority P2
    python status_aggregator.py --action daily-summary
"""

import sys, os, argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, query_db, log_task as _log_task

AGENTS = [
    "Business Strategist", "Finance", "Sales", "Marketing",
    "Content Engine", "Product", "Community", "Analytics", "Orchestrator",
]


def agent_status(args):
    """Show recent tasks for a specific agent."""
    agent = args.agent or "Sales"
    items = query_db("task_log", filter={
        "property": "Agent", "select": {"equals": agent}
    })
    print("=" * 65)
    print(f"  📋 AGENT STATUS: {agent}")
    print("=" * 65)
    if not items:
        print(f"\n  No tasks logged for {agent}."); return

    items.sort(key=lambda x: x.get("Timestamp", ""), reverse=True)
    shown = items[:20]
    for item in shown:
        icon = "✅" if item.get("Status") == "Complete" else "🔵" if item.get("Status") == "In Progress" else "⬜"
        print(f"\n  {icon} [{item.get('Priority', '?')}] {item.get('Task', '?')}")
        ts = item.get("Timestamp", "?")
        out = item.get("Output Summary", "")
        print(f"    {ts}")
        if out: print(f"    → {out}")

    print(f"\n{'─' * 65}")
    completed = sum(1 for t in items if t.get("Status") == "Complete")
    print(f"  Total tasks: {len(items)} | Completed: {completed}")


def log_task_action(args):
    """Manually log a task to the central task_log."""
    _log_task(
        agent=args.agent,
        task=args.task,
        status=args.status or "Complete",
        priority=args.priority or "P3",
        output_summary=args.output or "",
    )
    print(f"✅ Task logged: [{args.agent}] {args.task}")


def daily_summary(args):
    """Cross-agent summary for today (or specified date)."""
    target_date = args.date or datetime.now().strftime("%Y-%m-%d")
    items = query_db("task_log")

    # Filter to today's tasks (Notion timestamp starts with date)
    todays = [t for t in items if (t.get("Timestamp", "") or "").startswith(target_date)]

    print("=" * 70)
    print(f"  🏢 DAILY SUMMARY — {target_date}")
    print("=" * 70)

    if not todays:
        print(f"\n  No tasks logged for {target_date}."); return

    by_agent = {}
    for t in todays:
        a = t.get("Agent", "Unknown")
        by_agent.setdefault(a, []).append(t)

    for agent in AGENTS:
        tasks = by_agent.get(agent, [])
        if not tasks:
            continue
        completed = sum(1 for t in tasks if t.get("Status") == "Complete")
        print(f"\n  {agent} ({completed}/{len(tasks)} completed)")
        for t in tasks:
            icon = "✅" if t.get("Status") == "Complete" else "🔵"
            print(f"    {icon} {t.get('Task', '?')}")

    # Agents with no activity
    silent = [a for a in AGENTS if a not in by_agent]
    if silent:
        print(f"\n  ⚠️ No activity: {', '.join(silent)}")

    print(f"\n{'─' * 70}")
    total = len(todays)
    completed_total = sum(1 for t in todays if t.get("Status") == "Complete")
    active_agents = len(by_agent)
    print(f"  Tasks: {total} | Completed: {completed_total} | Active agents: {active_agents}/{len(AGENTS)}")
    _log_task("Orchestrator", f"Daily summary {target_date}", "Complete", "P2",
              f"{total} tasks, {active_agents} agents active")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrator Status Aggregation")
    parser.add_argument("--action", required=True,
                        choices=["agent-status", "log-task", "daily-summary"])
    parser.add_argument("--agent")
    parser.add_argument("--task")
    parser.add_argument("--status", default="Complete")
    parser.add_argument("--priority", default="P3")
    parser.add_argument("--output", default="")
    parser.add_argument("--date")
    args = parser.parse_args()
    {"agent-status": agent_status, "log-task": log_task_action,
     "daily-summary": daily_summary}[args.action](args)
