#!/usr/bin/env python3
"""
Hedge Edge — Railway Cron: Email Nurture
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Railway entry point for the email nurture automation.

Runs the full cycle:
  1. Poll Supabase for new waitlist signups
  2. Add new contacts to Resend audience
  3. Send welcome emails immediately
  4. Send drip emails on schedule (Day 1, 3, 5, 7)
  5. Poll Resend for delivery status (delivered/opened/clicked/bounced)
  6. Sync all stats to Notion (email_sends + email_sequences)
  7. Log completion to Orchestrator task log

Railway Config:
  - Service type: Cron job
  - Schedule: 0 */6 * * *  (every 6 hours)
  - Start command: python scripts/railway_email_nurture.py
  - Health check: exit code 0 = success

Environment Variables (set in Railway dashboard):
  RESEND_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
  NOTION_API_KEY, DISCORD_INVITE_URL
"""

import os
import sys
from datetime import datetime, timezone

# Ensure workspace root is importable
_WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WS)

from dotenv import load_dotenv
load_dotenv(os.path.join(_WS, ".env"), override=True)


def main():
    start = datetime.now(timezone.utc)
    print(f"[{start.strftime('%Y-%m-%d %H:%M UTC')}] Railway Email Nurture — Starting")
    print("=" * 55)

    # Validate required env vars
    required = ["RESEND_API_KEY", "NOTION_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        # Try NOTION_TOKEN fallback
        if "NOTION_API_KEY" in missing and os.getenv("NOTION_TOKEN"):
            missing.remove("NOTION_API_KEY")
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    try:
        from shared.email_nurture import run_cycle
        run_cycle(since_minutes=1440)  # 24-hour lookback
    except Exception as e:
        print(f"\n❌ Nurture cycle failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"\n[Done] Completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
