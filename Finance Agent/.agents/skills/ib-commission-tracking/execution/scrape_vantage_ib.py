#!/usr/bin/env python3
"""
scrape_vantage_ib.py
====================
Playwright-based scraper for the Vantage IB (Introducing Broker) Partner Portal.

Scrapes commission/rebate reports including:
  - Total commission earned
  - Per-client volume (lots traded)
  - Commission per lot
  - Date range
  - Client count

Outputs CSV + JSON to ../resources/

Usage:
    python scrape_vantage_ib.py
    python scrape_vantage_ib.py --date-range 2026-01-01 2026-01-31
    python scrape_vantage_ib.py --no-headless   # visible browser for debugging

Environment variables (loaded from workspace root .env):
    VANTAGE_IB_EMAIL      - IB portal login email
    VANTAGE_IB_PASSWORD   - IB portal login password
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
from shared.notion_client import add_row, log_task

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Workspace root .env location (adjust if your .env lives elsewhere)
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]  # /Orchestrator Hedge Edge
load_dotenv(WORKSPACE_ROOT / ".env")

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOTS_DIR = RESOURCES_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

#  Portal URLs (update if Vantage changes its domain) 
LOGIN_URL = "https://portal.vantagemarkets.com/login"
COMMISSION_REPORT_URL = "https://portal.vantagemarkets.com/reports/commissions"

#  Retry settings 
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

#  Logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vantage_ib_scraper")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_date_range() -> tuple[str, str]:
    """Return (start, end) ISO dates for the current calendar month."""
    today = datetime.utcnow().date()
    start = today.replace(day=1)
    # Last day of month
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _take_error_screenshot(page, label: str = "error") -> Path:
    """Save a timestamped screenshot and return the path."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOTS_DIR / f"vantage_{label}_{ts}.png"
    page.screenshot(path=str(path), full_page=True)
    logger.info("Screenshot saved  %s", path)
    return path


# ---------------------------------------------------------------------------
# Core scraping flow
# ---------------------------------------------------------------------------

def login(page, email: str, password: str) -> None:
    """
    Log into the Vantage IB partner portal.

    UPDATE SELECTORS BELOW if Vantage changes their login page HTML.
    """
    logger.info("Navigating to login page: %s", LOGIN_URL)
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=30_000)

    #  Selectors (update these if the portal HTML changes) 
    EMAIL_SELECTOR = 'input[name="email"], input[type="email"], #email'
    PASSWORD_SELECTOR = 'input[name="password"], input[type="password"], #password'
    SUBMIT_SELECTOR = 'button[type="submit"], input[type="submit"], .login-btn'
    # 

    page.fill(EMAIL_SELECTOR, email)
    page.fill(PASSWORD_SELECTOR, password)
    page.click(SUBMIT_SELECTOR)

    # Wait for navigation after login
    page.wait_for_load_state("networkidle", timeout=30_000)
    logger.info("Login submitted  checking for 2FA")

    _handle_2fa(page)


def _handle_2fa(page) -> None:
    """
    If a 2FA / OTP prompt appears, pause execution and wait for the user
    to complete it manually in the browser window.

    UPDATE SELECTORS BELOW if the 2FA page structure changes.
    """
    #  2FA detection selectors 
    TWO_FA_INDICATORS = [
        'input[name="otp"]',
        'input[name="twoFactorCode"]',
        'input[name="verificationCode"]',
        '[data-testid="2fa-input"]',
        'text="Two-Factor"',
        'text="Verification Code"',
        'text="Enter the code"',
    ]
    # 

    for selector in TWO_FA_INDICATORS:
        try:
            if page.locator(selector).first.is_visible(timeout=3_000):
                logger.warning(
                    "2FA prompt detected! Complete it in the browser window. "
                    "The script will resume automatically once the dashboard loads."
                )
                # Wait up to 5 minutes for the user to complete 2FA
                page.wait_for_url("**/dashboard**", timeout=300_000)
                logger.info("2FA completed  dashboard loaded.")
                return
        except Exception:
            continue

    logger.info("No 2FA prompt detected  proceeding.")


def navigate_to_commissions(page, date_start: str, date_end: str) -> None:
    """
    Navigate to the commission report page and apply the date filter.

    UPDATE SELECTORS BELOW if the commission report page structure changes.
    """
    logger.info("Navigating to commission reports: %s", COMMISSION_REPORT_URL)
    page.goto(COMMISSION_REPORT_URL, wait_until="networkidle", timeout=30_000)

    #  Date range selectors (update if portal changes) 
    DATE_START_SELECTOR = 'input[name="startDate"], input[name="date_from"], #startDate'
    DATE_END_SELECTOR = 'input[name="endDate"], input[name="date_to"], #endDate'
    APPLY_FILTER_SELECTOR = 'button:has-text("Apply"), button:has-text("Filter"), button:has-text("Search")'
    # 

    try:
        page.fill(DATE_START_SELECTOR, date_start)
        page.fill(DATE_END_SELECTOR, date_end)
        page.click(APPLY_FILTER_SELECTOR)
        page.wait_for_load_state("networkidle", timeout=15_000)
        logger.info("Date filter applied: %s  %s", date_start, date_end)
    except Exception as exc:
        logger.warning("Could not apply date filter (may use default): %s", exc)


def scrape_commission_data(page, date_start: str, date_end: str) -> dict:
    """
    Extract commission data from the loaded report page.

    Returns a dict with keys:
        broker, date_range, scraped_at, total_commission, client_count,
        total_lots, avg_commission_per_lot, currency, clients (list)

    UPDATE SELECTORS BELOW if the report table / summary cards change.
    """
    data = {
        "broker": "Vantage",
        "date_range": {"start": date_start, "end": date_end},
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "total_commission": 0.0,
        "client_count": 0,
        "total_lots": 0.0,
        "avg_commission_per_lot": 0.0,
        "currency": "USD",
        "clients": [],
    }

    #  Summary card selectors (update if portal changes) 
    TOTAL_COMMISSION_SELECTOR = (
        '[data-testid="total-commission"], '
        '.total-commission .value, '
        '.summary-card:has-text("Commission") .amount, '
        '.commission-total'
    )
    CLIENT_COUNT_SELECTOR = (
        '[data-testid="client-count"], '
        '.client-count .value, '
        '.summary-card:has-text("Client") .count'
    )
    TOTAL_LOTS_SELECTOR = (
        '[data-testid="total-lots"], '
        '.total-lots .value, '
        '.summary-card:has-text("Lots") .amount'
    )
    #  Client table selectors 
    CLIENT_TABLE_ROWS_SELECTOR = (
        'table.commission-table tbody tr, '
        '[data-testid="commission-table"] tbody tr, '
        '.report-table tbody tr'
    )
    # Column indices (0-based)  adjust to match actual table layout
    COL_CLIENT_ID = 0
    COL_CLIENT_NAME = 1
    COL_LOTS = 2
    COL_COMMISSION = 3
    # 

    # --- Extract summary values ---
    try:
        el = page.locator(TOTAL_COMMISSION_SELECTOR).first
        raw = el.inner_text(timeout=10_000)
        data["total_commission"] = _parse_number(raw)
        logger.info("Total commission: %s", data["total_commission"])
    except Exception as exc:
        logger.warning("Could not read total commission: %s", exc)

    try:
        el = page.locator(CLIENT_COUNT_SELECTOR).first
        raw = el.inner_text(timeout=5_000)
        data["client_count"] = int(_parse_number(raw))
        logger.info("Client count: %s", data["client_count"])
    except Exception as exc:
        logger.warning("Could not read client count: %s", exc)

    try:
        el = page.locator(TOTAL_LOTS_SELECTOR).first
        raw = el.inner_text(timeout=5_000)
        data["total_lots"] = _parse_number(raw)
        logger.info("Total lots: %s", data["total_lots"])
    except Exception as exc:
        logger.warning("Could not read total lots: %s", exc)

    # --- Extract per-client rows ---
    try:
        rows = page.locator(CLIENT_TABLE_ROWS_SELECTOR).all()
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) < 4:
                continue
            client = {
                "client_id": cells[COL_CLIENT_ID].inner_text().strip(),
                "client_name": cells[COL_CLIENT_NAME].inner_text().strip(),
                "lots_traded": _parse_number(cells[COL_LOTS].inner_text()),
                "commission": _parse_number(cells[COL_COMMISSION].inner_text()),
            }
            data["clients"].append(client)
        logger.info("Scraped %d client rows.", len(data["clients"]))
    except Exception as exc:
        logger.warning("Could not scrape client table: %s", exc)

    # Calculate avg commission per lot
    if data["total_lots"] > 0:
        data["avg_commission_per_lot"] = round(
            data["total_commission"] / data["total_lots"], 4
        )

    # Reconcile client count with scraped rows
    if data["clients"] and data["client_count"] == 0:
        data["client_count"] = len(data["clients"])

    return data


def _parse_number(text: str) -> float:
    """Strip currency symbols, commas, whitespace and return a float."""
    cleaned = text.replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_data(data: dict) -> tuple[Path, Path]:
    """Write commission data to CSV and JSON files. Returns (csv_path, json_path)."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = f"vantage_commissions_{ts}"

    # --- JSON ---
    json_path = RESOURCES_DIR / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("JSON exported  %s", json_path)

    # Also write a "latest" symlink-style copy for the aggregator
    latest_json = RESOURCES_DIR / "vantage_commissions_latest.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # --- CSV ---
    csv_path = RESOURCES_DIR / f"{base_name}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "broker", "date_start", "date_end", "client_id",
            "client_name", "lots_traded", "commission", "currency",
        ])
        if data["clients"]:
            for c in data["clients"]:
                writer.writerow([
                    data["broker"],
                    data["date_range"]["start"],
                    data["date_range"]["end"],
                    c["client_id"],
                    c["client_name"],
                    c["lots_traded"],
                    c["commission"],
                    data["currency"],
                ])
        else:
            # Write a summary row when per-client data isn't available
            writer.writerow([
                data["broker"],
                data["date_range"]["start"],
                data["date_range"]["end"],
                "ALL",
                f"{data['client_count']} clients",
                data["total_lots"],
                data["total_commission"],
                data["currency"],
            ])
    logger.info("CSV exported   %s", csv_path)

    return csv_path, json_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Vantage IB Partner Portal commissions."
    )
    parser.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Date range as YYYY-MM-DD YYYY-MM-DD (default: current month)",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run browser in headless mode (default: True). Use --no-headless for visible.",
    )
    args = parser.parse_args()

    date_start, date_end = (
        args.date_range if args.date_range else _default_date_range()
    )
    logger.info("Date range: %s  %s | Headless: %s", date_start, date_end, args.headless)

    # Validate credentials
    email = os.getenv("VANTAGE_IB_EMAIL")
    password = os.getenv("VANTAGE_IB_PASSWORD")
    if not email or not password:
        logger.error(
            "Missing credentials. Set VANTAGE_IB_EMAIL and VANTAGE_IB_PASSWORD "
            "in your .env file at: %s",
            WORKSPACE_ROOT / ".env",
        )
        sys.exit(1)

    # Late import so --help works without Playwright installed
    from playwright.sync_api import sync_playwright

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Attempt %d / %d", attempt, MAX_RETRIES)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=args.headless)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()

                login(page, email, password)
                navigate_to_commissions(page, date_start, date_end)
                data = scrape_commission_data(page, date_start, date_end)
                csv_path, json_path = export_data(data)

                browser.close()

            logger.info(" Scrape completed successfully.")
            logger.info("  CSV   %s", csv_path)
            logger.info("  JSON  %s", json_path)
            log_task("Finance", "Scraped Vantage IB commission data", "Done", "Medium", f"Exported {date_start} to {date_end} commissions to CSV and JSON")
            return  # success  exit retry loop

        except Exception as exc:
            logger.error("Attempt %d failed: %s", attempt, exc, exc_info=True)
            try:
                _take_error_screenshot(page, label=f"attempt{attempt}")
            except Exception:
                pass  # page may already be closed

            if attempt < MAX_RETRIES:
                logger.info("Retrying in %d seconds", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                logger.critical("All %d attempts failed. Exiting.", MAX_RETRIES)
                sys.exit(1)


if __name__ == "__main__":
    main()
