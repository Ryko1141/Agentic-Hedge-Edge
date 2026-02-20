#!/usr/bin/env python3
"""
Hedge Edge - Railway Cron: Lead Drip
=====================================
Railway entry point for the lead email drip automation.

Flow per run:
  1. Sync new leads from Notion leads_crm (auto-import)
  2. Send next batch of drip emails (with yesterday guard + dedup)
  3. Enrich Notion email_sends with Resend delivery data
  4. Sync Wave statuses back to Notion leads_crm
  5. Log completion

Railway Config:
  - Service type: Cron job
  - Schedule: 0 9 * * *  (every day at 9:00 UTC)
  - Start command: python scripts/railway_lead_drip.py
  - Health check: exit code 0 = success

Environment Variables (set in Railway dashboard):
  RESEND_API_KEY, NOTION_API_KEY
"""

import os
import sys
from datetime import datetime, timezone

_WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WS)

from dotenv import load_dotenv
load_dotenv(os.path.join(_WS, ".env"), override=True)


def main():
    start = datetime.now(timezone.utc)
    print(f"[{start.strftime('%Y-%m-%d %H:%M UTC')}] Railway Lead Drip - Starting")
    print("=" * 55)

    # Validate env vars
    required = ["RESEND_API_KEY", "NOTION_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    try:
        sys.path.insert(0, os.path.join(_WS, "scripts"))
        import lead_drip

        # Warmup: cap at 50 sends per run
        lead_drip.BATCH_SIZE = 50
        print(f"  Warmup mode: BATCH_SIZE = {lead_drip.BATCH_SIZE}")

        # Step 1+2: Sync Notion leads + send drip batch (with yesterday guard)
        lead_drip.run_drip()

        # Step 3: Enrich Notion with Resend delivery data
        print()
        try:
            lead_drip.enrich_notion_from_resend()
        except Exception as e:
            print(f"  Enrichment failed (non-fatal): {e}")

        # Step 4: Sync Wave statuses to Notion
        print()
        try:
            lead_drip.sync_all_waves()
        except Exception as e:
            print(f"  Wave sync failed (non-fatal): {e}")

        # Step 5: Log to Notion task log
        try:
            from shared.notion_client import log_task
            log_task(
                "Marketing",
                "Lead drip cron run",
                "Complete",
                "P1",
                f"Daily batch completed at {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
            )
        except Exception as e:
            print(f"  Task log failed: {e}")

    except Exception as e:
        print(f"\nLead drip failed: {e}")
        import traceback
        traceback.print_exc()

        # Send failure notification to Outlook
        try:
            sys.path.insert(0, os.path.join(_WS, "scripts"))
            from lead_drip import notify_outlook_reply
            import requests
            h = {"Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}", "Content-Type": "application/json"}
            payload = {
                "from": "Hedge Edge Alerts <alerts@hedgedge.info>",
                "to": ["hedgeedge@outlook.com"],
                "subject": "[Lead Drip FAILED] Railway cron error",
                "text": f"Lead drip cron failed at {datetime.now(timezone.utc).isoformat()}\n\nError: {e}",
                "tags": [{"name": "type", "value": "error-alert"}],
            }
            requests.post("https://api.resend.com/emails", headers=h, json=payload, timeout=15)
        except Exception:
            pass

        sys.exit(1)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"\n[Done] Completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
