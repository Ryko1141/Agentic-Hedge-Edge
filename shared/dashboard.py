"""
Hedge Edge — Analytics Dashboard Aggregator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pulls metrics from all integrated services into a single summary.

Usage (import):
    from shared.dashboard import get_erp_summary, get_service_health, get_business_metrics, generate_report

Usage (CLI):
    python -m shared.dashboard            # Readable markdown report
    python -m shared.dashboard --json     # JSON output
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv

# ── Environment ───────────────────────────────────────
_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

# Lazy-import shared modules to avoid circular-import issues and to keep
# this file usable even if some client modules are broken.

def _import_notion():
    from shared.notion_client import get_notion, DATABASES, query_db
    return get_notion, DATABASES, query_db


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. ERP Summary — row counts across key Notion databases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ERP_TABLES = [
    "task_log",
    "leads_crm",
    "feature_roadmap",
    "bug_tracker",
    "support_tickets",
    "content_calendar",
    "campaigns",
]


def get_erp_summary() -> dict:
    """
    Count rows in key Notion ERP databases.

    Returns:
        {
            "task_log": 42,
            "leads_crm": 18,
            ...
            "_errors": {"bug_tracker": "timeout"}   # only if failures
        }
    """
    _, DATABASES, query_db = _import_notion()
    counts: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for table in _ERP_TABLES:
        try:
            rows = query_db(table, page_size=100)
            counts[table] = len(rows)
        except Exception as exc:
            counts[table] = None
            errors[table] = str(exc)[:200]

    if errors:
        counts["_errors"] = errors
    return counts


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Service Health — lightweight ping for each external API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _ping(label: str, fn) -> dict:
    """Run *fn*, measure latency, return status dict."""
    t0 = time.perf_counter()
    try:
        fn()
        latency_ms = round((time.perf_counter() - t0) * 1000)
        return {"status": "up", "latency_ms": latency_ms}
    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000)
        return {"status": "down", "latency_ms": latency_ms, "error": str(exc)[:200]}


def _check_notion() -> None:
    get_notion, DATABASES, _ = _import_notion()
    client = get_notion()
    client.databases.retrieve(database_id=DATABASES["task_log"])


def _check_discord() -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not url and not token:
        raise RuntimeError("No DISCORD_WEBHOOK_URL or DISCORD_BOT_TOKEN configured")
    # If bot token exists, do a lightweight /users/@me call
    if token:
        r = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
        r.raise_for_status()
    # Otherwise just confirm the env var is set (don't POST to webhook)


def _check_shortio() -> None:
    key = os.getenv("SHORTIO_API_KEY", "")
    if not key:
        raise RuntimeError("SHORTIO_API_KEY not set")
    r = requests.get(
        "https://api.short.io/api/domains",
        headers={"Authorization": key, "Accept": "application/json"},
        timeout=10,
    )
    r.raise_for_status()


def _check_cloudflare() -> None:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "")
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN not set")
    if not zone_id:
        raise RuntimeError("CLOUDFLARE_ZONE_ID not set")
    r = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )
    r.raise_for_status()


def _check_github() -> None:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")
    r = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    r.raise_for_status()


def _check_resend() -> None:
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError("RESEND_API_KEY not set")
    r = requests.get(
        "https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {key}"},
        timeout=10,
    )
    r.raise_for_status()


def _check_vercel() -> None:
    token = os.getenv("VERCEL_TOKEN", "")
    if not token:
        raise RuntimeError("VERCEL_TOKEN not set")
    r = requests.get(
        "https://api.vercel.com/v9/projects",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()


_HEALTH_CHECKS = [
    ("Notion",     _check_notion),
    ("Discord",    _check_discord),
    ("Short.io",   _check_shortio),
    ("Cloudflare", _check_cloudflare),
    ("GitHub",     _check_github),
    ("Resend",     _check_resend),
    ("Vercel",     _check_vercel),
]


def get_service_health() -> dict:
    """
    Ping each external service and return status + latency.

    Returns:
        {
            "Notion":     {"status": "up", "latency_ms": 320},
            "Discord":    {"status": "down", "latency_ms": 5010, "error": "..."},
            ...
            "_summary": {"up": 5, "down": 2, "total": 7}
        }
    """
    results: dict[str, Any] = {}
    for label, fn in _HEALTH_CHECKS:
        results[label] = _ping(label, fn)

    up = sum(1 for v in results.values() if isinstance(v, dict) and v.get("status") == "up")
    down = len(_HEALTH_CHECKS) - up
    results["_summary"] = {"up": up, "down": down, "total": len(_HEALTH_CHECKS)}
    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Business Metrics — KPIs pulled from Notion ERP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_business_metrics() -> dict:
    """
    Query Notion for headline business KPIs:
        - latest MRR (from mrr_tracker, most recent row)
        - total lead count (leads_crm)
        - open bug count (bug_tracker, Status != Done)
        - active campaigns (campaigns, Status == Active)
        - pending support tickets (support_tickets, Status != Resolved/Closed)

    Returns dict with each metric or None on failure.
    """
    _, DATABASES, query_db = _import_notion()
    metrics: dict[str, Any] = {}
    errors: dict[str, str] = {}

    # ── Latest MRR ──
    try:
        rows = query_db(
            "mrr_tracker",
            sorts=[{"property": "Date", "direction": "descending"}],
            page_size=1,
        )
        if rows:
            # Try common column names for the MRR value
            mrr = rows[0].get("MRR") or rows[0].get("Amount") or rows[0].get("Value")
            mrr_date = rows[0].get("Date") or rows[0].get("Month")
            metrics["mrr"] = {"value": mrr, "as_of": str(mrr_date) if mrr_date else None}
        else:
            metrics["mrr"] = {"value": None, "as_of": None}
    except Exception as exc:
        metrics["mrr"] = None
        errors["mrr"] = str(exc)[:200]

    # ── Lead Count ──
    try:
        rows = query_db("leads_crm", page_size=100)
        metrics["lead_count"] = len(rows)
    except Exception as exc:
        metrics["lead_count"] = None
        errors["lead_count"] = str(exc)[:200]

    # ── Open Bugs ──
    try:
        rows = query_db("bug_tracker", page_size=100)
        open_bugs = [r for r in rows if (r.get("Status") or "").lower() not in ("done", "closed", "resolved")]
        metrics["open_bugs"] = len(open_bugs)
    except Exception as exc:
        metrics["open_bugs"] = None
        errors["open_bugs"] = str(exc)[:200]

    # ── Active Campaigns ──
    try:
        rows = query_db("campaigns", page_size=100)
        active = [r for r in rows if (r.get("Status") or "").lower() == "active"]
        metrics["active_campaigns"] = len(active)
    except Exception as exc:
        metrics["active_campaigns"] = None
        errors["active_campaigns"] = str(exc)[:200]

    # ── Pending Support Tickets ──
    try:
        rows = query_db("support_tickets", page_size=100)
        pending = [r for r in rows if (r.get("Status") or "").lower() not in ("resolved", "closed", "done")]
        metrics["pending_support_tickets"] = len(pending)
    except Exception as exc:
        metrics["pending_support_tickets"] = None
        errors["pending_support_tickets"] = str(exc)[:200]

    if errors:
        metrics["_errors"] = errors
    return metrics


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Report Generator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_report() -> str:
    """
    Pull all dashboard data and format into a readable Markdown report.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    lines.append("# Hedge Edge — Dashboard Report")
    lines.append(f"_Generated: {now}_\n")

    # ── Service Health ──
    lines.append("## Service Health\n")
    health = get_service_health()
    summary = health.pop("_summary", {})
    for svc, info in health.items():
        if not isinstance(info, dict):
            continue
        status_icon = "✅" if info["status"] == "up" else "❌"
        latency = f'{info["latency_ms"]}ms'
        err = f' — {info["error"]}' if info.get("error") else ""
        lines.append(f"| {status_icon} **{svc}** | {info['status'].upper()} | {latency}{err} |")

    up = summary.get("up", "?")
    total = summary.get("total", "?")
    lines.append(f"\n**{up}/{total} services operational**\n")

    # ── ERP Summary ──
    lines.append("## ERP Database Counts\n")
    erp = get_erp_summary()
    erp_errors = erp.pop("_errors", {})
    lines.append("| Database | Rows |")
    lines.append("|----------|------|")
    for table, count in erp.items():
        display = str(count) if count is not None else "⚠️ error"
        lines.append(f"| {table} | {display} |")
    if erp_errors:
        lines.append(f"\n_Errors: {json.dumps(erp_errors, default=str)}_\n")

    # ── Business Metrics ──
    lines.append("## Business Metrics\n")
    bm = get_business_metrics()
    bm_errors = bm.pop("_errors", {})

    mrr_info = bm.get("mrr")
    if isinstance(mrr_info, dict) and mrr_info.get("value") is not None:
        lines.append(f"- **MRR**: ${mrr_info['value']:,.2f}" if isinstance(mrr_info["value"], (int, float))
                      else f"- **MRR**: {mrr_info['value']}")
        if mrr_info.get("as_of"):
            lines[-1] += f" (as of {mrr_info['as_of']})"
    else:
        lines.append("- **MRR**: _no data_")

    def _metric_line(label: str, key: str):
        val = bm.get(key)
        if val is not None:
            lines.append(f"- **{label}**: {val}")
        else:
            lines.append(f"- **{label}**: _no data_")

    _metric_line("Leads", "lead_count")
    _metric_line("Open Bugs", "open_bugs")
    _metric_line("Active Campaigns", "active_campaigns")
    _metric_line("Pending Support Tickets", "pending_support_tickets")

    if bm_errors:
        lines.append(f"\n_Errors: {json.dumps(bm_errors, default=str)}_\n")

    lines.append("---")
    lines.append(f"_Report complete. {now}_")
    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. CLI Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cli():
    parser = argparse.ArgumentParser(
        description="Hedge Edge Analytics Dashboard",
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="Output raw JSON instead of Markdown report",
    )
    args = parser.parse_args()

    if args.as_json:
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "service_health": get_service_health(),
            "erp_summary": get_erp_summary(),
            "business_metrics": get_business_metrics(),
        }
        print(json.dumps(data, indent=2, default=str))
    else:
        print(generate_report())


if __name__ == "__main__":
    _cli()
