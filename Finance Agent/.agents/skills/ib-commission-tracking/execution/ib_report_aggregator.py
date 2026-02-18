#!/usr/bin/env python3
"""
ib_report_aggregator.py
=======================
Reads the latest Vantage and BlackBull IB commission JSON outputs from
../resources/ and produces:

  1. A unified combined JSON    ../resources/ib-combined.json
  2. A Markdown summary report  ../resources/ib-commission-summary.md

Metrics calculated:
  - Total IB revenue (across all brokers)
  - Revenue by broker
  - Average commission per lot
  - Total lots referred
  - Month-over-month growth (if previous-month data exists)

Usage:
    python ib_report_aggregator.py
    python ib_report_aggregator.py --vantage path/to/vantage.json --blackbull path/to/blackbull.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, log_task

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

# Default "latest" file paths produced by the scrapers
DEFAULT_VANTAGE_JSON = RESOURCES_DIR / "vantage_commissions_latest.json"
DEFAULT_BLACKBULL_JSON = RESOURCES_DIR / "blackbull_commissions_latest.json"

OUTPUT_COMBINED_JSON = RESOURCES_DIR / "ib-combined.json"
OUTPUT_SUMMARY_MD = RESOURCES_DIR / "ib-commission-summary.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ib_aggregator")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_broker_json(path: Path) -> Optional[dict]:
    """Load and validate a broker commission JSON file."""
    if not path.exists():
        logger.warning("File not found (will be skipped): %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        required = {"broker", "total_commission", "total_lots", "client_count", "date_range"}
        if not required.issubset(data.keys()):
            logger.warning("JSON missing required keys in %s  found: %s", path, set(data.keys()))
            return None
        logger.info("Loaded %s data from %s", data["broker"], path)
        return data
    except (json.JSONDecodeError, IOError) as exc:
        logger.error("Failed to read %s: %s", path, exc)
        return None


def _find_previous_month_data(broker_name: str) -> Optional[dict]:
    """
    Attempt to find a previous month's JSON for MoM growth calculation.
    Looks for timestamped files in the resources directory.
    """
    pattern = f"{broker_name.lower()}_commissions_*.json"
    files = sorted(RESOURCES_DIR.glob(pattern))
    # Exclude the 'latest' file
    files = [f for f in files if "latest" not in f.name]
    if len(files) >= 2:
        # Assume second-to-last is previous period
        try:
            with open(files[-2], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(broker_datasets: list[dict]) -> dict:
    """
    Combine multiple broker datasets into a unified report.

    Returns a dictionary with combined metrics and per-broker breakdowns.
    """
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "brokers_included": [],
        "summary": {
            "total_ib_revenue": 0.0,
            "total_lots_referred": 0.0,
            "total_clients": 0,
            "avg_commission_per_lot": 0.0,
            "currency": "USD",
        },
        "by_broker": [],
        "all_clients": [],
        "mom_growth": {},
    }

    total_commission = 0.0
    total_lots = 0.0
    total_clients = 0

    for ds in broker_datasets:
        broker_name = ds["broker"]
        report["brokers_included"].append(broker_name)

        broker_commission = ds.get("total_commission", 0.0)
        broker_lots = ds.get("total_lots", 0.0)
        broker_clients = ds.get("client_count", 0)
        broker_avg = ds.get("avg_commission_per_lot", 0.0)

        total_commission += broker_commission
        total_lots += broker_lots
        total_clients += broker_clients

        broker_entry = {
            "broker": broker_name,
            "total_commission": broker_commission,
            "total_lots": broker_lots,
            "client_count": broker_clients,
            "avg_commission_per_lot": broker_avg,
            "date_range": ds.get("date_range", {}),
            "scraped_at": ds.get("scraped_at", ""),
        }
        report["by_broker"].append(broker_entry)

        # Merge client-level data
        for client in ds.get("clients", []):
            client_entry = {**client, "broker": broker_name}
            report["all_clients"].append(client_entry)

        # Month-over-month growth
        prev = _find_previous_month_data(broker_name)
        if prev and prev.get("total_commission", 0) > 0:
            prev_comm = prev["total_commission"]
            growth_pct = round(
                ((broker_commission - prev_comm) / prev_comm) * 100, 2
            )
            report["mom_growth"][broker_name] = {
                "previous_commission": prev_comm,
                "current_commission": broker_commission,
                "growth_percent": growth_pct,
            }
            logger.info(
                "%s MoM growth: %.2f%% ($%.2f  $%.2f)",
                broker_name, growth_pct, prev_comm, broker_commission,
            )

    # Roll-up summary
    report["summary"]["total_ib_revenue"] = round(total_commission, 2)
    report["summary"]["total_lots_referred"] = round(total_lots, 2)
    report["summary"]["total_clients"] = total_clients
    if total_lots > 0:
        report["summary"]["avg_commission_per_lot"] = round(
            total_commission / total_lots, 4
        )

    return report


# ---------------------------------------------------------------------------
# Client analytics with pandas
# ---------------------------------------------------------------------------

def build_client_dataframe(report: dict) -> Optional[pd.DataFrame]:
    """Convert the all_clients list into a pandas DataFrame for analysis."""
    if not report["all_clients"]:
        return None
    df = pd.DataFrame(report["all_clients"])
    df["lots_traded"] = pd.to_numeric(df["lots_traded"], errors="coerce").fillna(0)
    df["commission"] = pd.to_numeric(df["commission"], errors="coerce").fillna(0)
    return df


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def write_combined_json(report: dict) -> Path:
    """Write the combined report to JSON."""
    with open(OUTPUT_COMBINED_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Combined JSON  %s", OUTPUT_COMBINED_JSON)
    return OUTPUT_COMBINED_JSON


def write_summary_markdown(report: dict) -> Path:
    """Generate a human-readable Markdown summary report."""
    s = report["summary"]
    lines = [
        "# Hedge Edge  IB Commission Summary Report",
        "",
        f"> Generated: {report['generated_at']}",
        "",
        "---",
        "",
        "## Overall Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| **Total IB Revenue** |  |",
        f"| **Total Lots Referred** | {s['total_lots_referred']:,.2f} |",
        f"| **Total Clients** | {s['total_clients']} |",
        f"| **Avg Commission / Lot** |  |",
        f"| **Currency** | {s['currency']} |",
        f"| **Brokers Included** | {', '.join(report['brokers_included'])} |",
        "",
        "---",
        "",
        "## Revenue by Broker",
        "",
        "| Broker | Commission | Lots | Clients | Avg $/Lot | Period |",
        "|--------|-----------|------|---------|-----------|--------|",
    ]

    for b in report["by_broker"]:
        dr = b.get("date_range", {})
        period = f"{dr.get('start', '?')}  {dr.get('end', '?')}"
        lines.append(
            f"| {b['broker']} "
            f"|  "
            f"| {b['total_lots']:,.2f} "
            f"| {b['client_count']} "
            f"|  "
            f"| {period} |"
        )

    # Revenue share percentages
    if s["total_ib_revenue"] > 0:
        lines += ["", "### Revenue Share", ""]
        for b in report["by_broker"]:
            pct = (b["total_commission"] / s["total_ib_revenue"]) * 100
            lines.append(f"- **{b['broker']}**: {pct:.1f}%")

    # Month-over-month growth
    if report["mom_growth"]:
        lines += ["", "---", "", "## Month-over-Month Growth", ""]
        lines.append("| Broker | Previous | Current | Growth |")
        lines.append("|--------|----------|---------|--------|")
        for broker, g in report["mom_growth"].items():
            sign = "+" if g["growth_percent"] >= 0 else ""
            lines.append(
                f"| {broker} "
                f"|  "
                f"|  "
                f"| {sign}{g['growth_percent']:.2f}% |"
            )

    # Top clients table (if client-level data exists)
    if report["all_clients"]:
        df = build_client_dataframe(report)
        if df is not None and not df.empty:
            lines += ["", "---", "", "## Top 10 Clients by Commission", ""]
            lines.append("| Broker | Client ID | Client Name | Lots | Commission |")
            lines.append("|--------|-----------|-------------|------|-----------|")
            top = df.nlargest(10, "commission")
            for _, row in top.iterrows():
                lines.append(
                    f"| {row['broker']} "
                    f"| {row['client_id']} "
                    f"| {row['client_name']} "
                    f"| {row['lots_traded']:,.2f} "
                    f"|  |"
                )

    lines += [
        "",
        "---",
        "",
        "*Report auto-generated by Hedge Edge Finance Agent  IB Commission Tracker*",
        "",
    ]

    md_content = "\n".join(lines)
    with open(OUTPUT_SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Markdown summary  %s", OUTPUT_SUMMARY_MD)
    return OUTPUT_SUMMARY_MD


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate Vantage + BlackBull IB commission data."
    )
    parser.add_argument(
        "--vantage",
        type=Path,
        default=DEFAULT_VANTAGE_JSON,
        help="Path to Vantage commission JSON (default: latest in resources/)",
    )
    parser.add_argument(
        "--blackbull",
        type=Path,
        default=DEFAULT_BLACKBULL_JSON,
        help="Path to BlackBull commission JSON (default: latest in resources/)",
    )
    args = parser.parse_args()

    # Load available broker data
    datasets = []
    for label, path in [("Vantage", args.vantage), ("BlackBull", args.blackbull)]:
        data = load_broker_json(path)
        if data:
            datasets.append(data)
        else:
            logger.warning("Skipping %s  no data available at %s", label, path)

    if not datasets:
        logger.error(
            "No broker data found. Run the scraper scripts first:\n"
            "  python scrape_vantage_ib.py\n"
            "  python scrape_blackbull_ib.py"
        )
        sys.exit(1)

    logger.info("Aggregating data from %d broker(s)", len(datasets))

    report = aggregate(datasets)
    write_combined_json(report)
    write_summary_markdown(report)

    log_task("Finance", "Aggregated IB commission reports", "Done", "Medium", f"Combined data from {len(datasets)} broker(s) into unified report")

    # Print quick summary to stdout
    s = report["summary"]
    print("\n" + "=" * 60)
    print("  HEDGE EDGE  IB COMMISSION SUMMARY")
    print("=" * 60)
    print(f"  Total IB Revenue:      ")
    print(f"  Total Lots Referred:   {s['total_lots_referred']:>12,.2f}")
    print(f"  Total Clients:         {s['total_clients']:>12}")
    print(f"  Avg Commission/Lot:    ")
    print(f"  Brokers:               {', '.join(report['brokers_included'])}")
    for broker, g in report.get("mom_growth", {}).items():
        sign = "+" if g["growth_percent"] >= 0 else ""
        print(f"  {broker} MoM Growth:  {sign}{g['growth_percent']:.2f}%")
    print("=" * 60)
    print(f"  JSON   {OUTPUT_COMBINED_JSON}")
    print(f"  MD     {OUTPUT_SUMMARY_MD}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
