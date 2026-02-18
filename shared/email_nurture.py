"""
Hedge Edge — Email Nurture System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Automated email sequences triggered by new Supabase signups.
All sends are logged to Notion (email_sends DB) with Resend delivery metrics.

Flow:
    1. Poll Supabase for new profiles (created in last N minutes)
    2. Add to Resend "Hedge Edge Waitlist" audience
    3. Send welcome email immediately → log to Notion
    4. Drip emails sent on schedule (Day 1, 3, 5, 7) → log to Notion
    5. Poll Resend for delivery status → update Notion rows

Usage:
    # One-time setup: create audience
    python email_nurture.py --action setup

    # Process new signups (run on cron / scheduled task)
    python email_nurture.py --action process-new

    # Send drip emails to existing contacts (run daily)
    python email_nurture.py --action send-drips

    # Update delivery status from Resend (run hourly)
    python email_nurture.py --action update-status

    # Full cycle: process + drips + status (Railway cron)
    python email_nurture.py --action run-cycle

    # Send a specific email to a specific address (testing)
    python email_nurture.py --action send-test --email you@example.com --template welcome

    # View stats
    python email_nurture.py --action stats
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.resend_client import (
    send_email, get_email, list_audiences, create_audience,
    add_contact, list_contacts,
)

from dotenv import load_dotenv
load_dotenv()

# ─── Config ───────────────────────────────────────────

AUDIENCE_NAME = "Hedge Edge Waitlist"
FROM_ADDR = "Hedge Edge <hello@hedgedge.info>"
REPLY_TO = "hedgeedgebusiness@gmail.com"
TRACKING_FILE = os.path.join(os.path.dirname(__file__), "_email_nurture_state.json")

DISCORD_INVITE = os.getenv("DISCORD_INVITE_URL", "https://discord.gg/jVFVc2pQWE")
SITE_URL = "https://hedgedge.info"


# ─── State management ────────────────────────────────

def load_state() -> dict:
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, "r") as f:
            return json.load(f)
    return {"audience_id": None, "processed_users": {}, "drip_log": {}}


def save_state(state: dict):
    with open(TRACKING_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ─── Notion client loader ────────────────────────────

_nc_module = None

def _get_notion_client():
    """Import shared.notion_client lazily, avoiding name shadow with pip notion_client pkg."""
    global _nc_module
    if _nc_module is None:
        # shared/ dir shadows pip's notion_client package.
        # Temporarily remove it from sys.path so our file can import the pip package.
        shared_dir = os.path.dirname(os.path.abspath(__file__))
        removed = []
        for p in list(sys.path):
            if os.path.normcase(os.path.abspath(p)) == os.path.normcase(shared_dir):
                sys.path.remove(p)
                removed.append(p)
        # Also clear any partial cache
        for key in list(sys.modules.keys()):
            if key == "notion_client" and hasattr(sys.modules[key], '__file__') and \
               sys.modules[key].__file__ and 'shared' in sys.modules[key].__file__:
                del sys.modules[key]
        try:
            import importlib.util
            nc_path = os.path.join(shared_dir, "notion_client.py")
            spec = importlib.util.spec_from_file_location("shared.notion_client", nc_path)
            _nc_module = importlib.util.module_from_spec(spec)
            sys.modules["shared.notion_client"] = _nc_module
            spec.loader.exec_module(_nc_module)
        finally:
            # Restore paths
            for p in removed:
                if p not in sys.path:
                    sys.path.insert(0, p)
    return _nc_module


# ─── Notion logging ──────────────────────────────────

def _log_send_to_notion(
    subject: str,
    recipient: str,
    template_key: str,
    sequence: str,
    resend_id: str,
    day: int,
    user_id: str = "",
    user_name: str = "",
    error: str = "",
) -> Optional[str]:
    """Log an email send to Notion email_sends DB. Returns Notion page ID."""
    try:
        nc = _get_notion_client()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        status = "failed" if error else "sent"
        page = nc.add_row("email_sends", {
            "Subject":    subject,
            "Recipient":  recipient,
            "Template":   template_key,
            "Sequence":   sequence,
            "Status":     status,
            "Resend ID":  resend_id,
            "Day":        day,
            "Sent At":    now_iso,
            "User ID":    user_id,
            "User Name":  user_name,
            "Error":      error[:2000] if error else "",
        })
        return page.get("id")
    except Exception as e:
        print(f"  ⚠️  Notion log failed: {e}")
        return None


def _update_notion_status(page_id: str, status: str, **extra_fields):
    """Update a Notion email_sends row with delivery status."""
    try:
        nc = _get_notion_client()
        updates = {"Status": status}
        for field, val in extra_fields.items():
            if val:
                updates[field] = val
        nc.update_row(page_id, "email_sends", updates)
    except Exception as e:
        print(f"  ⚠️  Notion update failed: {e}")


def update_delivery_status():
    """Poll Resend for delivery status and update Notion rows."""
    state = load_state()
    pending = state.get("pending_status", {})

    if not pending:
        print("  ℹ️  No emails pending status update.")
        return

    updated = 0
    completed_ids = []

    for resend_id, info in pending.items():
        try:
            email_data = get_email(resend_id)
            last_event = email_data.get("last_event", "sent")

            # Map Resend events to our status
            status_map = {
                "sent": "sent",
                "delivered": "delivered",
                "delivery_delayed": "sent",
                "opened": "opened",
                "clicked": "clicked",
                "bounced": "bounced",
                "complained": "complained",
            }
            new_status = status_map.get(last_event, "sent")
            notion_page_id = info.get("notion_page_id")

            if notion_page_id:
                extra = {}
                # Capture timestamps from Resend
                if new_status in ("delivered", "opened", "clicked"):
                    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    if new_status == "delivered":
                        extra["Delivered At"] = ts
                    elif new_status == "opened":
                        extra["Delivered At"] = info.get("delivered_at") or ts
                        extra["Opened At"] = ts
                    elif new_status == "clicked":
                        extra["Delivered At"] = info.get("delivered_at") or ts
                        extra["Opened At"] = info.get("opened_at") or ts
                        extra["Clicked At"] = ts

                if new_status == "bounced":
                    extra["Error"] = "Bounced"
                elif new_status == "complained":
                    extra["Error"] = "Spam complaint"

                _update_notion_status(notion_page_id, new_status, **extra)
                updated += 1

                # Track progressive timestamps
                if new_status == "delivered":
                    info["delivered_at"] = extra.get("Delivered At")
                elif new_status == "opened":
                    info["opened_at"] = extra.get("Opened At")

            # Terminal states -> remove from pending
            if new_status in ("bounced", "complained", "clicked"):
                completed_ids.append(resend_id)
            # "opened" and "clicked" are terminal enough after 7 days
            sent_str = info.get("sent_at", "")
            if sent_str:
                try:
                    sent_time = datetime.fromisoformat(sent_str.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - sent_time).days > 7:
                        completed_ids.append(resend_id)
                except:
                    pass

        except Exception as e:
            print(f"  ⚠️  Status check failed for {resend_id}: {e}")

    # Clean up completed
    for rid in completed_ids:
        pending.pop(rid, None)

    save_state(state)
    print(f"  Updated {updated} email statuses, {len(completed_ids)} completed")


# ─── Email Templates ─────────────────────────────────

def _base_wrapper(content: str) -> str:
    """Wrap content in branded email template."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ margin: 0; padding: 0; background: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  .container {{ max-width: 600px; margin: 0 auto; background: #111111; border-radius: 12px; overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 32px 24px; text-align: center; }}
  .header h1 {{ color: #ffffff; font-size: 28px; margin: 0; font-weight: 700; }}
  .header p {{ color: rgba(255,255,255,0.85); font-size: 14px; margin: 8px 0 0 0; }}
  .body {{ padding: 32px 24px; color: #e5e5e5; line-height: 1.7; font-size: 15px; }}
  .body h2 {{ color: #10b981; font-size: 20px; margin: 24px 0 12px 0; }}
  .body h3 {{ color: #ffffff; font-size: 17px; margin: 20px 0 8px 0; }}
  .body a {{ color: #10b981; text-decoration: none; }}
  .body a:hover {{ text-decoration: underline; }}
  .cta {{ display: inline-block; background: #10b981; color: #ffffff !important; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; text-decoration: none !important; margin: 16px 0; }}
  .highlight {{ background: #1a1a2e; border-left: 3px solid #10b981; padding: 16px; margin: 16px 0; border-radius: 0 8px 8px 0; }}
  .stat {{ display: inline-block; text-align: center; padding: 12px 20px; }}
  .stat-num {{ font-size: 28px; font-weight: 700; color: #10b981; display: block; }}
  .stat-label {{ font-size: 12px; color: #999; text-transform: uppercase; }}
  .footer {{ padding: 24px; text-align: center; border-top: 1px solid #222; color: #666; font-size: 12px; }}
  .footer a {{ color: #888; }}
  .emoji {{ font-size: 20px; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 8px 0; }}
</style>
</head>
<body>
<div style="padding: 20px; background: #0a0a0a;">
  <div class="container">
    <div class="header">
      <h1>🛡️ Hedge Edge</h1>
      <p>Protect Your Prop Firm Challenges</p>
    </div>
    <div class="body">
      {content}
    </div>
    <div class="footer">
      <p>Hedge Edge Ltd · London, UK</p>
      <p><a href="{SITE_URL}">hedgedge.info</a> · <a href="{DISCORD_INVITE}">Discord</a></p>
      <p style="margin-top: 12px;"><a href="{{{{unsubscribe_url}}}}">Unsubscribe</a></p>
    </div>
  </div>
</div>
</body>
</html>"""


# ─── Segment-aware template system ────────────────────
# Import 20 segment-tailored templates (4 segments × 5 emails)
from shared.email_templates import ALL_SEGMENTS, DEFAULT_SEGMENT

# Unified template keys across all segments
TEMPLATE_KEYS = ["welcome", "day1_education", "day3_broker", "day5_product", "day7_offer"]

# Legacy key mapping (for existing drips_sent lists in state file)
_LEGACY_KEY_MAP = {
    "day1_how_it_works": "day1_education",
    "day3_broker_setup": "day3_broker",
    "day5_first_hedge": "day5_product",
    "day7_exclusive": "day7_offer",
}

# Valid segment identifiers
VALID_SEGMENTS = list(ALL_SEGMENTS.keys())


def get_templates(segment: str | None = None) -> dict:
    """Return the 5-template dict for a given segment. Falls back to default."""
    seg = segment if segment in ALL_SEGMENTS else DEFAULT_SEGMENT
    raw = ALL_SEGMENTS[seg]["templates"]
    # Wrap each template's raw html lambda with the branded email shell
    wrapped = {}
    for key, tpl in raw.items():
        original_fn = tpl["html"]
        wrapped[key] = {
            **tpl,
            "html": lambda name, _fn=original_fn: _base_wrapper(_fn(name)),
        }
    return wrapped


# Keep a flat TEMPLATES dict for backward compatibility (uses default segment)
TEMPLATES = get_templates(DEFAULT_SEGMENT)


def _normalise_key(key: str) -> str:
    """Map legacy template keys to current ones."""
    return _LEGACY_KEY_MAP.get(key, key)


# ─── Supabase helper ─────────────────────────────────

def get_new_signups(since_minutes: int = 60) -> list[dict]:
    """Get profiles created in the last N minutes."""
    try:
        from shared.supabase_client import get_supabase
        sb = get_supabase(use_service_role=True)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).isoformat()
        result = sb.table("profiles").select("id, full_name, created_at").gte("created_at", cutoff).execute()
        return result.data or []
    except Exception as e:
        print(f"  ⚠️  Supabase query failed: {e}")
        return []


def get_all_profiles() -> list[dict]:
    """Get all profiles for bulk sync."""
    try:
        from shared.supabase_client import get_supabase
        sb = get_supabase(use_service_role=True)
        result = sb.table("profiles").select("id, full_name, created_at").order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"  ⚠️  Supabase query failed: {e}")
        return []


def get_user_email(user_id: str) -> Optional[str]:
    """Get email from auth.users via service role."""
    try:
        from shared.supabase_client import get_supabase
        sb = get_supabase(use_service_role=True)
        # Use the admin API to get user by ID
        user = sb.auth.admin.get_user_by_id(user_id)
        return user.user.email if user and user.user else None
    except Exception as e:
        print(f"  ⚠️  Auth lookup failed for {user_id}: {e}")
        return None


# ─── Core actions ─────────────────────────────────────

def setup_audience():
    """Create the Resend audience (one-time setup)."""
    state = load_state()

    # Check if audience already exists
    audiences = list_audiences()
    for a in audiences:
        if a.get("name") == AUDIENCE_NAME:
            state["audience_id"] = a["id"]
            save_state(state)
            print(f"  ✅ Audience already exists: {AUDIENCE_NAME} (ID: {a['id']})")
            return a["id"]

    # Create new
    result = create_audience(AUDIENCE_NAME)
    audience_id = result.get("id")
    state["audience_id"] = audience_id
    save_state(state)
    print(f"  ✅ Created audience: {AUDIENCE_NAME} (ID: {audience_id})")
    return audience_id


def process_new_signups(since_minutes: int = 1440, segment: str | None = None):
    """Find new signups and send welcome emails.
    
    Args:
        since_minutes: Look back this many minutes for new signups.
        segment: Lead segment tag (e.g. 'unsuccessful_unaware'). Determines which
                 email templates to send. Defaults to DEFAULT_SEGMENT if omitted.
    """
    seg = segment if segment in ALL_SEGMENTS else DEFAULT_SEGMENT
    templates = get_templates(seg)
    state = load_state()
    audience_id = state.get("audience_id")

    if not audience_id:
        print("  ❌ No audience ID. Run --action setup first.")
        return

    profiles = get_new_signups(since_minutes)
    if not profiles:
        print(f"  ℹ️  No new signups in the last {since_minutes} minutes.")
        return

    print(f"  Found {len(profiles)} profiles in last {since_minutes} minutes")
    new_count = 0

    for profile in profiles:
        user_id = profile["id"]
        name = profile.get("full_name", "").split()[0] or "Trader"

        # Skip if already processed
        if user_id in state.get("processed_users", {}):
            continue

        # Get email from auth
        email = get_user_email(user_id)
        if not email:
            print(f"  ⚠️  No email for user {user_id}, skipping")
            continue

        # Add to Resend audience
        try:
            first = name
            last = " ".join(profile.get("full_name", "").split()[1:]) or ""
            add_contact(audience_id, email, first_name=first, last_name=last)
            print(f"  ✅ Added to audience: {email}")
        except Exception as e:
            print(f"  ⚠️  Audience add failed for {email}: {e}")

        # Send welcome email
        try:
            template = templates["welcome"]
            result = send_email(
                to=email,
                subject=template["subject"],
                html=template["html"](name),
                from_addr=FROM_ADDR,
                reply_to=REPLY_TO,
                tags=[
                    {"name": "sequence", "value": "waitlist-nurture"},
                    {"name": "email_type", "value": "welcome"},
                    {"name": "day", "value": "0"},
                    {"name": "segment", "value": seg},
                ],
            )
            resend_id = result.get("id", "")
            print(f"  ✅ Welcome email sent to {email} (ID: {resend_id}) [segment={seg}]")

            # Log to Notion
            notion_page_id = _log_send_to_notion(
                subject=template["subject"],
                recipient=email,
                template_key="welcome",
                sequence="waitlist-nurture",
                resend_id=resend_id,
                day=0,
                user_id=user_id,
                user_name=profile.get("full_name", ""),
            )

            # Track for delivery status polling
            if resend_id:
                state.setdefault("pending_status", {})[resend_id] = {
                    "notion_page_id": notion_page_id,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "email": email,
                    "template": "welcome",
                }
        except Exception as e:
            print(f"  ❌ Welcome email failed for {email}: {e}")
            _log_send_to_notion(
                subject=templates["welcome"]["subject"],
                recipient=email,
                template_key="welcome",
                sequence="waitlist-nurture",
                resend_id="",
                day=0,
                user_id=user_id,
                user_name=profile.get("full_name", ""),
                error=str(e),
            )

        # Track
        state["processed_users"][user_id] = {
            "email": email,
            "name": name,
            "segment": seg,
            "signed_up": profile.get("created_at"),
            "welcome_sent": datetime.now(timezone.utc).isoformat(),
            "drips_sent": ["welcome"],
        }
        new_count += 1

    save_state(state)
    print(f"\n  Processed {new_count} new signups")


def send_drips():
    """Send scheduled drip emails based on signup date."""
    state = load_state()
    processed = state.get("processed_users", {})

    if not processed:
        print("  ℹ️  No users to drip. Process new signups first.")
        return

    now = datetime.now(timezone.utc)
    sent_count = 0

    # Drip schedule: template_key → delay_days
    drip_schedule = [
        ("day1_education", 1),
        ("day3_broker", 3),
        ("day5_product", 5),
        ("day7_offer", 7),
    ]

    for user_id, user_data in processed.items():
        email = user_data.get("email")
        name = user_data.get("name", "Trader")
        seg = user_data.get("segment", DEFAULT_SEGMENT)
        templates = get_templates(seg)
        drips_sent = [_normalise_key(k) for k in user_data.get("drips_sent", [])]
        signup_str = user_data.get("welcome_sent") or user_data.get("signed_up")

        if not signup_str or not email:
            continue

        # Parse signup time
        try:
            signup_time = datetime.fromisoformat(signup_str.replace("Z", "+00:00"))
        except:
            continue

        days_since = (now - signup_time).total_seconds() / 86400

        for template_key, delay in drip_schedule:
            if template_key in drips_sent:
                continue  # Already sent

            if days_since >= delay:
                template = templates[template_key]
                try:
                    result = send_email(
                        to=email,
                        subject=template["subject"],
                        html=template["html"](name),
                        from_addr=FROM_ADDR,
                        reply_to=REPLY_TO,
                        tags=[
                            {"name": "sequence", "value": "waitlist-nurture"},
                            {"name": "email_type", "value": template_key},
                            {"name": "day", "value": str(delay)},
                            {"name": "segment", "value": seg},
                        ],
                    )
                    resend_id = result.get("id", "")
                    drips_sent.append(template_key)
                    sent_count += 1
                    print(f"  ✅ Sent '{template_key}' to {email} (Day {delay})")

                    # Log to Notion
                    notion_page_id = _log_send_to_notion(
                        subject=template["subject"],
                        recipient=email,
                        template_key=template_key,
                        sequence="waitlist-nurture",
                        resend_id=resend_id,
                        day=delay,
                        user_id=user_id,
                        user_name=name,
                    )

                    # Track for delivery status polling
                    if resend_id:
                        state.setdefault("pending_status", {})[resend_id] = {
                            "notion_page_id": notion_page_id,
                            "sent_at": datetime.now(timezone.utc).isoformat(),
                            "email": email,
                            "template": template_key,
                        }
                except Exception as e:
                    print(f"  ❌ Failed '{template_key}' to {email}: {e}")
                    _log_send_to_notion(
                        subject=templates[template_key]["subject"],
                        recipient=email,
                        template_key=template_key,
                        sequence="waitlist-nurture",
                        resend_id="",
                        day=delay,
                        user_id=user_id,
                        user_name=name,
                        error=str(e),
                    )

        user_data["drips_sent"] = drips_sent

    save_state(state)
    print(f"\n  Sent {sent_count} drip emails")


def send_test(email: str, template_key: str = "welcome", segment: str | None = None):
    """Send a test email to verify templates.
    
    Args:
        email: Recipient address.
        template_key: One of TEMPLATE_KEYS.
        segment: Lead segment tag. Defaults to DEFAULT_SEGMENT.
    """
    seg = segment if segment in ALL_SEGMENTS else DEFAULT_SEGMENT
    template_key = _normalise_key(template_key)
    templates = get_templates(seg)

    if template_key not in templates:
        print(f"  ❌ Unknown template: {template_key}")
        print(f"  Available: {', '.join(TEMPLATE_KEYS)}")
        print(f"  Segments: {', '.join(VALID_SEGMENTS)}")
        return

    template = templates[template_key]
    try:
        result = send_email(
            to=email,
            subject=f"[TEST] {template['subject']}",
            html=template["html"]("TestUser"),
            from_addr=FROM_ADDR,
            reply_to=REPLY_TO,
            tags=[{"name": "type", "value": "test"}, {"name": "template", "value": template_key}],
        )
        resend_id = result.get("id", "")
        print(f"  ✅ Test email sent: '{template_key}' → {email}")
        print(f"     Resend ID: {resend_id}")

        # Log to Notion
        notion_page_id = _log_send_to_notion(
            subject=f"[TEST] {template['subject']}",
            recipient=email,
            template_key=template_key,
            sequence="test",
            resend_id=resend_id,
            day=template.get("delay_days", 0),
        )

        # Track for status polling
        if resend_id:
            state = load_state()
            state.setdefault("pending_status", {})[resend_id] = {
                "notion_page_id": notion_page_id,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "email": email,
                "template": template_key,
            }
            save_state(state)
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        _log_send_to_notion(
            subject=f"[TEST] {template['subject']}",
            recipient=email,
            template_key=template_key,
            sequence="test",
            resend_id="",
            day=template.get("delay_days", 0),
            error=str(e),
        )


def show_stats():
    """Show nurture system stats and sync summary to Notion email_sequences."""
    state = load_state()
    processed = state.get("processed_users", {})

    print("=" * 55)
    print("  📧 EMAIL NURTURE STATS")
    print("=" * 55)
    print(f"\n  Audience ID: {state.get('audience_id', 'Not set')}")
    print(f"  Total processed: {len(processed)}")
    print(f"  Pending status checks: {len(state.get('pending_status', {}))}")

    if processed:
        # Count drips (normalise legacy keys)
        drip_counts = {k: 0 for k in ["welcome"] + TEMPLATE_KEYS[1:]}
        seg_counts = {}
        for user in processed.values():
            seg = user.get("segment", DEFAULT_SEGMENT)
            seg_counts[seg] = seg_counts.get(seg, 0) + 1
            for d in user.get("drips_sent", []):
                nk = _normalise_key(d)
                if nk in drip_counts:
                    drip_counts[nk] += 1

        print(f"\n  Drip funnel:")
        for key, count in drip_counts.items():
            pct = f" ({count/len(processed):.0%})" if processed else ""
            print(f"    {key}: {count}{pct}")

        # Segment breakdown
        if seg_counts:
            print(f"\n  Segment breakdown:")
            for seg_name, cnt in sorted(seg_counts.items(), key=lambda x: -x[1]):
                label = ALL_SEGMENTS.get(seg_name, {}).get("segment_label", seg_name)
                print(f"    {label}: {cnt}")

        # Recent signups
        print(f"\n  Recent signups:")
        recent = sorted(processed.values(), key=lambda x: x.get("welcome_sent", ""), reverse=True)[:5]
        for u in recent:
            print(f"    {u.get('email', '?')} — {u.get('name', '?')} — drips: {len(u.get('drips_sent', []))}/5")

    # Try to get Resend audience stats
    try:
        audiences = list_audiences()
        for a in audiences:
            if a.get("id") == state.get("audience_id"):
                print(f"\n  Resend audience: {a.get('name', '?')}")
                break
    except:
        pass

    # Try Resend contact count
    try:
        if state.get("audience_id"):
            contacts = list_contacts(state["audience_id"])
            print(f"  Resend contacts: {len(contacts)}")
    except:
        pass

    # Sync aggregate metrics to Notion email_sequences DB
    _sync_sequence_metrics(processed)


def _sync_sequence_metrics(processed: dict):
    """Sync aggregate nurture metrics to the Notion email_sequences DB."""
    if not processed:
        return
    try:
        nc = _get_notion_client()
        total = len(processed)

        # Query Notion for delivery stats
        sends = nc.query_db("email_sends")
        delivered = sum(1 for s in sends if s.get("Status") in ("delivered", "opened", "clicked"))
        opened = sum(1 for s in sends if s.get("Status") in ("opened", "clicked"))
        clicked = sum(1 for s in sends if s.get("Status") == "clicked")
        total_sends = len(sends)

        open_rate = opened / total_sends if total_sends else 0
        click_rate = clicked / total_sends if total_sends else 0

        # Find or create the "Waitlist Nurture" sequence row
        seqs = nc.query_db("email_sequences", filter={
            "property": "Name", "title": {"equals": "Waitlist Nurture"}
        })
        metrics = {
            "Status":      "Active",
            "Emails Count": 20,  # 4 segments × 5 emails
            "Open Rate":    round(open_rate, 4),
            "Click Rate":   round(click_rate, 4),
            "Last Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        if seqs:
            nc.update_row(seqs[0]["_id"], "email_sequences", metrics)
            print(f"\n  📊 Synced to Notion: {total_sends} sends, {open_rate:.0%} open, {click_rate:.0%} click")
        else:
            row = {"Name": "Waitlist Nurture", "Trigger": "Signup", **metrics}
            nc.add_row("email_sequences", row)
            print(f"\n  📊 Created Notion sequence row: Waitlist Nurture")
    except Exception as e:
        print(f"  ⚠️  Notion metrics sync failed: {e}")


def run_cycle(since_minutes: int = 1440):
    """Full automation cycle: process new → drips → status updates → stats.
    This is the action Railway cron should call."""
    print("=" * 55)
    print("  🔄 EMAIL NURTURE CYCLE")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    # 1. Ensure audience exists
    print("\n── Step 1: Audience check ──")
    setup_audience()

    # 2. Process new signups
    print(f"\n── Step 2: New signups (last {since_minutes} min) ──")
    process_new_signups(since_minutes)

    # 3. Send drip emails
    print("\n── Step 3: Drip emails ──")
    send_drips()

    # 4. Update delivery status from Resend
    print("\n── Step 4: Delivery status ──")
    update_delivery_status()

    # 5. Stats + Notion sync
    print("\n── Step 5: Stats ──")
    show_stats()

    # 6. Log to task log
    try:
        nc = _get_notion_client()
        state = load_state()
        n_users = len(state.get("processed_users", {}))
        n_pending = len(state.get("pending_status", {}))
        nc.log_task(
            "Marketing",
            "Email nurture cycle",
            "Complete",
            "P1",
            f"Users: {n_users}, Pending status: {n_pending}",
        )
    except Exception as e:
        print(f"  ⚠️  Task log failed: {e}")

    print("\n  ✅ Cycle complete")


# ─── CLI ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hedge Edge Email Nurture System")
    parser.add_argument("--action", required=True,
                        choices=["setup", "process-new", "send-drips", "update-status",
                                 "run-cycle", "send-test", "stats"])
    parser.add_argument("--email", help="Email for test send")
    parser.add_argument("--template", default="welcome",
                        help="Template key for test send")
    parser.add_argument("--segment", default=None,
                        choices=VALID_SEGMENTS,
                        help="Lead segment (e.g. unsuccessful_unaware, successful_unaware, aware_not_hedging, active_hedger)")
    parser.add_argument("--since", type=int, default=1440,
                        help="Look back N minutes for new signups (default: 1440 = 24hr)")
    args = parser.parse_args()

    print()
    if args.action == "setup":
        print("Setting up Resend audience...")
        setup_audience()
    elif args.action == "process-new":
        print(f"Processing new signups (last {args.since} min)...")
        process_new_signups(args.since, segment=args.segment)
    elif args.action == "send-drips":
        print("Sending scheduled drip emails...")
        send_drips()
    elif args.action == "update-status":
        print("Updating delivery status from Resend...")
        update_delivery_status()
    elif args.action == "run-cycle":
        run_cycle(args.since)
    elif args.action == "send-test":
        if not args.email:
            print("  ❌ --email required for test send")
            sys.exit(1)
        send_test(args.email, args.template, segment=args.segment)
    elif args.action == "stats":
        show_stats()
    print()
