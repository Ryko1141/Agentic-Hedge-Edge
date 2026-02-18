"""
Hedge Edge — Scheduled Tasks Runner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs periodic maintenance tasks. Meant to be triggered by:
  - Windows Task Scheduler (local dev)
  - Railway cron job (production)
  - Manual invocation

Tasks:
  1. LinkedIn token refresh (if <14 days remaining)
  2. Short.io domain health check
  3. Cloudflare zone health check

Usage:
    python -m shared.scheduled_tasks              # Run all
    python -m shared.scheduled_tasks --task token  # Just LinkedIn refresh
"""

import argparse
import os
import sys
from datetime import datetime

_WS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WS_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_WS_ROOT, ".env"), override=True)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def task_linkedin_refresh():
    """Refresh LinkedIn token if needed."""
    print(f"\n[{_ts()}] ── LinkedIn Token Check ──")
    from shared.linkedin_refresh import refresh_if_needed
    result = refresh_if_needed(threshold_days=14)
    if result:
        print(f"  Refreshed — new token valid ~{result['days_left']} days")
    return True


def task_shortio_health():
    """Check Short.io domain status."""
    print(f"\n[{_ts()}] ── Short.io Health Check ──")
    from shared.shortio_client import list_domains
    domains = list_domains()
    for d in domains:
        state = d.get("state", "unknown")
        hostname = d.get("hostname", "?")
        print(f"  {hostname}: {state}")
        if state != "configured":
            print(f"  ⚠ Domain not configured!")
    return True


def task_cloudflare_health():
    """Check Cloudflare zone status."""
    print(f"\n[{_ts()}] ── Cloudflare Health Check ──")
    from shared.cloudflare_client import verify_token, list_zones
    try:
        status = verify_token()
        print(f"  Token: {status.get('status', 'unknown')}")
    except Exception as e:
        print(f"  Token error: {e}")
        return False

    zones = list_zones()
    for z in zones:
        print(f"  {z['name']}: {z['status']}")
    return True


def task_email_nurture():
    """Run full email nurture cycle: new signups → drips → delivery status → Notion sync."""
    print(f"\n[{_ts()}] ── Email Nurture Cycle ──")
    from shared.email_nurture import run_cycle
    try:
        run_cycle(since_minutes=1440)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def task_lead_decay():
    """Run weekly lead score decay for inactive leads."""
    print(f"\n[{_ts()}] ── Lead Score Decay ──")
    import subprocess
    script = os.path.join(_WS_ROOT, "Marketing Agent", ".agents", "skills",
                          "lead-generation", "execution", "lead_generator.py")
    result = subprocess.run([sys.executable, script, "--action", "decay"], check=False)
    print(f"  {'OK' if result.returncode == 0 else 'FAILED'}")
    return result.returncode == 0


def task_kpi_snapshot():
    """Take automated KPI snapshot."""
    print(f"\n[{_ts()}] ── KPI Snapshot ──")
    import subprocess
    script = os.path.join(_WS_ROOT, "Analytics Agent", ".agents", "skills",
                          "kpi-dashboards", "execution", "kpi_snapshot.py")
    result = subprocess.run([sys.executable, script, "--action", "take-snapshot",
                              "--metric", "daily_health", "--value", "1",
                              "--period", datetime.now().strftime("%Y-%m-%d")], check=False)
    print(f"  {'OK' if result.returncode == 0 else 'FAILED'}")
    return result.returncode == 0


def task_daily_digest():
    """Generate automated daily digest report."""
    print(f"\n[{_ts()}] ── Daily Digest ──")
    import subprocess
    script = os.path.join(_WS_ROOT, "Analytics Agent", ".agents", "skills",
                          "reporting-automation", "execution", "report_automator.py")
    result = subprocess.run([sys.executable, script, "--action", "daily-digest"], check=False)
    print(f"  {'OK' if result.returncode == 0 else 'FAILED'}")
    return result.returncode == 0


def task_pipeline_hygiene():
    """Run sales pipeline stale deal detection."""
    print(f"\n[{_ts()}] ── Pipeline Hygiene ──")
    import subprocess
    script = os.path.join(_WS_ROOT, "Sales Agent", ".agents", "skills",
                          "sales-pipeline", "execution", "sales_pipeline.py")
    result = subprocess.run([sys.executable, script, "--action", "stale-deals"], check=False)
    print(f"  {'OK' if result.returncode == 0 else 'FAILED'}")
    return result.returncode == 0


def task_status_report():
    """Run Orchestrator status aggregation across all agents."""
    print(f"\n[{_ts()}] ── Status Aggregation ──")
    import subprocess
    script = os.path.join(_WS_ROOT, "Orchestrator Agent", ".agents", "skills",
                          "status-reporting", "execution", "status_aggregator.py")
    result = subprocess.run([sys.executable, script, "--action", "full-report"], check=False)
    print(f"  {'OK' if result.returncode == 0 else 'FAILED'}")
    return result.returncode == 0


TASKS = {
    "token":      ("LinkedIn token refresh", task_linkedin_refresh),
    "shortio":    ("Short.io health check", task_shortio_health),
    "cloudflare": ("Cloudflare health check", task_cloudflare_health),
    "nurture":    ("Email nurture cycle", task_email_nurture),
    "lead-decay": ("Lead score decay (weekly)", task_lead_decay),
    "kpi":        ("KPI snapshot", task_kpi_snapshot),
    "digest":     ("Daily digest report", task_daily_digest),
    "pipeline":   ("Pipeline hygiene", task_pipeline_hygiene),
    "status":     ("Status aggregation", task_status_report),
}


def run_all():
    """Run all scheduled tasks."""
    print(f"{'=' * 50}")
    print(f"  Hedge Edge — Scheduled Tasks")
    print(f"  {_ts()}")
    print(f"{'=' * 50}")

    results = {}
    for key, (name, fn) in TASKS.items():
        try:
            ok = fn()
            results[key] = "OK" if ok else "WARN"
        except Exception as e:
            print(f"  ERROR in {name}: {e}")
            results[key] = "ERROR"

    print(f"\n{'─' * 50}")
    print("  Summary:")
    for key, status in results.items():
        name = TASKS[key][0]
        icon = "✓" if status == "OK" else "⚠" if status == "WARN" else "✗"
        print(f"    [{icon}] {name}: {status}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Hedge Edge Scheduled Tasks")
    parser.add_argument("--task", choices=list(TASKS.keys()), help="Run a specific task")
    args = parser.parse_args()

    if args.task:
        name, fn = TASKS[args.task]
        print(f"Running: {name}")
        fn()
    else:
        run_all()


if __name__ == "__main__":
    main()
