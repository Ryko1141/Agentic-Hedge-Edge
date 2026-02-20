#!/usr/bin/env python3
"""
Hedge Edge - Lead Drip Automation
==================================
Sends the 5-email lead sequence from Notion to contacts in the Resend audience.

Strategy (Hybrid):
  Emails 1-3: Plain text, personal, no links (Primary inbox)
  Emails 4-5: Plain text with links (conversion)

Flow:
  1. Read email templates from Notion (email_sequences DB)
  2. Read contacts from Resend "Hedge Edge Waitlist" audience
  3. Sync new leads from Notion leads_crm (auto-import)
  4. Check state file: which email has each contact received?
  4. Send next email in sequence to contacts who are due
  5. Rate limit to 50 sends per email per run
  6. Log each send to Notion email_sends DB
  7. Update state file

Usage:
  python scripts/lead_drip.py --action run          # Send next batch
  python scripts/lead_drip.py --action status        # Show drip status
  python scripts/lead_drip.py --action preview       # Preview emails without sending
  python scripts/lead_drip.py --action import-csv --file contacts.csv  # Import contacts
  python scripts/lead_drip.py --action reset         # Reset all state (dangerous)

Railway Cron: 0 9 * * *  (every day at 9:00 UTC)
"""

import os
import sys
import json
import csv
import time
import argparse
from datetime import datetime, timezone, timedelta

_WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WS)

from dotenv import load_dotenv
load_dotenv(os.path.join(_WS, ".env"), override=True)

import requests

#  Config 
AUDIENCE_ID = "17895b10-363b-47d7-9784-477131568f7f"
# Sender addresses  one per email for deliverability
SENDERS = {
    1: "Ryan from Hedge Edge <ryan@hedgedge.info>",
    2: "Ryan @ Hedge Edge <insider@hedgedge.info>",
    3: "The Hedge Edge Team <team@hedgedge.info>",
    4: "Ryan @ Hedge Edge <alerts@hedgedge.info>",
    5: "Hedge Edge Deals <deals@hedgedge.info>",
}
DEFAULT_SENDER = SENDERS[1]
REPLY_TO = "hedgeedge@outlook.com"
BATCH_SIZE = 50          # Max sends per email per run
DAILY_CAP = 50           # Max total sends per day (warmup: 50 -> 100 -> 250 -> full)
SEND_DELAY = 1.2         # Seconds between sends (Resend: 2 req/s limit)
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lead_drip_state.json")

# Notion page IDs for each lead email (and their code block IDs)
LEAD_EMAILS = [
    {"num": 1, "page_id": "30c652ea-6c6d-8051-84c5-fe1a86e93108", "block_id": "30c652ea-6c6d-8026-b8ea-f50ed52a0e32"},
    {"num": 2, "page_id": "30c652ea-6c6d-80a5-a0e5-c907c3e7d20e", "block_id": "30c652ea-6c6d-8173-a18c-df53ea4db1ca"},
    {"num": 3, "page_id": "30c652ea-6c6d-80ca-90a5-da58b86d0cd7", "block_id": "30c652ea-6c6d-8190-9cb5-d1864fcb2b4e"},
    {"num": 4, "page_id": "30c652ea-6c6d-80e6-8fe7-cd3f9fde3594", "block_id": "30c652ea-6c6d-8179-b3ef-d862adc2f7ab"},
    {"num": 5, "page_id": "30c652ea-6c6d-800a-a32f-f5e35640fb96", "block_id": "30c652ea-6c6d-81a6-9dd3-d8bd178a4472"},
]

#  State Management 

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"contacts": {}, "runs": [], "total_sent": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

#  Notion Helpers 

def _notion_headers():
    return {
        "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

def fetch_email_template(email_def):
    """Fetch subject + body from Notion for a lead email."""
    h = _notion_headers()
    
    # Get subject from page properties
    r = requests.get(f"https://api.notion.com/v1/pages/{email_def['page_id']}", headers=h, timeout=10)
    props = r.json().get("properties", {})
    subject = "".join(t.get("plain_text", "") for t in props.get("Subject Line", {}).get("rich_text", []))
    
    # Get body from code block
    r2 = requests.get(f"https://api.notion.com/v1/blocks/{email_def['block_id']}", headers=h, timeout=10)
    block = r2.json()
    body_raw = "".join(t.get("plain_text", "") for t in block.get("code", {}).get("rich_text", []))
    
    # Extract just the email body (skip format/from/subject metadata lines)
    lines = body_raw.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("Hey ") or line.startswith("Hey,"):
            body_start = i
            break
    
    body = "\n".join(lines[body_start:]).strip()
    return {"subject": subject, "body": body, "num": email_def["num"]}

def log_send_to_notion(subject, recipient, email_num, resend_id, error=""):
    """Log a send to the Notion email_sends DB."""
    try:
        from shared.notion_client import add_row, DATABASES
        db_id = DATABASES.get("email_sends")
        if not db_id:
            return
        
        props = {
            "Subject": subject,
            "Recipient": recipient,
            "Status": "Error" if error else "Sent",
            "Resend ID": resend_id or "",
            "Sequence": "lead-drip",
            "Template": f"lead_email_{email_num}",
            "Day": email_num,
        }
        if error:
            props["Notes"] = error
        
        add_row("email_sends", props)
    except Exception as e:
        pass  # Non-blocking: don't let logging crash the send loop

def update_notion_wave(email, email_num):
    """Update the Wave field on the leads_crm row for this contact."""
    try:
        from shared.notion_client import query_db
        h = _notion_headers()
        wave_name = f"Lead email {email_num}" if email_num <= 5 else "Complete"
        
        # Find the lead in Notion
        filter_payload = {
            "filter": {"property": "Email", "email": {"equals": email}},
            "page_size": 1,
        }
        from shared.notion_client import DATABASES
        db_id = DATABASES.get("leads_crm")
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=h, json=filter_payload, timeout=10,
        )
        results = r.json().get("results", [])
        if results:
            page_id = results[0]["id"]
            requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=h,
                json={"properties": {"Wave": {"select": {"name": wave_name}}}},
                timeout=10,
            )
    except Exception as e:
        print(f"    (Wave sync failed: {e})")

def sync_all_waves():
    """Sync all Wave statuses from local state to Notion leads_crm. Efficient batch approach."""
    print("=" * 55)
    print("  LEAD DRIP - Syncing Waves to Notion")
    print("=" * 55)

    state = load_state()
    contacts = state.get("contacts", {})
    h = _notion_headers()
    from shared.notion_client import DATABASES
    db_id = DATABASES.get("leads_crm")

    # Step 1: Batch query ALL Lead Drip contacts from Notion (paginated)
    print("  Fetching all leads from Notion...")
    all_pages = []
    start_cursor = None
    while True:
        payload = {
            "filter": {"property": "Tags", "multi_select": {"contains": "Lead Drip"}},
            "page_size": 100,
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor
        try:
            r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                              headers=h, json=payload, timeout=20)
            data = r.json()
            all_pages.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
        except Exception as e:
            print(f"  Query error: {e}")
            break
        time.sleep(0.3)

    print(f"  Found {len(all_pages)} Lead Drip contacts in Notion")

    # Step 2: Build email -> (page_id, current_wave) map
    notion_map = {}
    for page in all_pages:
        props = page.get("properties", {})
        email = props.get("Email", {}).get("email")
        if not email:
            continue
        wave_sel = props.get("Wave", {}).get("select")
        current_wave = wave_sel.get("name", "") if wave_sel else ""
        notion_map[email.strip().lower()] = {"page_id": page["id"], "wave": current_wave}

    # Step 3: Compute diffs and patch only changed contacts
    updated = 0
    skipped = 0
    for email, cstate in contacts.items():
        last = cstate.get("last_sent") or 0
        if last == 0:
            target_wave = "Not Started"
        elif last >= 5:
            target_wave = "Complete"
        else:
            target_wave = f"Lead email {last}"

        notion_entry = notion_map.get(email.strip().lower())
        if not notion_entry:
            skipped += 1
            continue

        if notion_entry["wave"] == target_wave:
            continue  # Already correct

        try:
            requests.patch(
                f"https://api.notion.com/v1/pages/{notion_entry['page_id']}",
                headers=h,
                json={"properties": {"Wave": {"select": {"name": target_wave}}}},
                timeout=15,
            )
            updated += 1
            if updated % 10 == 0:
                print(f"  ...synced {updated}")
            time.sleep(0.35)
        except Exception as e:
            print(f"  Wave sync error for {email}: {e}")

    print(f"\n  Synced {updated} wave updates to Notion (skipped {skipped} not in Notion).")

#  Resend Helpers 

def _resend_headers():
    return {
        "Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}",
        "Content-Type": "application/json",
    }

def get_audience_contacts():
    """Fetch all contacts from the Resend Waitlist audience."""
    r = requests.get(
        f"https://api.resend.com/audiences/{AUDIENCE_ID}/contacts",
        headers=_resend_headers(),
        timeout=15,
    )
    data = r.json().get("data", [])
    # Filter out unsubscribed
    return [c for c in data if not c.get("unsubscribed")]

def add_contact_to_audience(email, first_name="", last_name=""):
    """Add a contact to the Resend audience."""
    payload = {
        "email": email,
        "unsubscribed": False,
    }
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    
    r = requests.post(
        f"https://api.resend.com/audiences/{AUDIENCE_ID}/contacts",
        headers=_resend_headers(),
        json=payload,
        timeout=10,
    )
    return r.status_code == 200, r.json()

def send_plain_email(to, subject, body, email_num):
    """Send a plain text email via Resend."""
    payload = {
        "from": SENDERS.get(email_num, DEFAULT_SENDER),
        "to": [to],
        "reply_to": REPLY_TO,
        "subject": subject,
        "text": body,
        "tags": [
            {"name": "sequence", "value": "lead-drip"},
            {"name": "email_num", "value": str(email_num)},
        ],
    }
    r = requests.post(
        "https://api.resend.com/emails",
        headers=_resend_headers(),
        json=payload,
        timeout=15,
    )
    return r.status_code == 200, r.json()



def get_recent_sends():
    """Query Resend for all emails sent. Returns set of (recipient_lower, subject) for dedup."""
    h = _resend_headers()
    already_sent = set()
    cursor = None
    for _ in range(50):
        params = {}
        if cursor:
            params["starting_after"] = cursor
        try:
            r = requests.get("https://api.resend.com/emails", headers=h, params=params, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            batch = data.get("data", [])
            for e in batch:
                to_list = e.get("to", [])
                subj = e.get("subject", "")
                for recip in (to_list if isinstance(to_list, list) else [to_list]):
                    already_sent.add((recip.strip().lower(), subj))
            if not data.get("has_more") or not batch:
                break
            cursor = batch[-1]["id"]
        except Exception as ex:
            print(f"    Dedup fetch error: {ex}")
            break
    return already_sent



def was_sent_yesterday(email, state):
    """Check if this contact received any email in the last 24 hours."""
    contact_state = state.get("contacts", {}).get(email, {})
    sends = contact_state.get("sends", [])
    if not sends:
        return False
    now = datetime.now(timezone.utc)
    for send in sends:
        sent_at_str = send.get("sent_at", "")
        if not sent_at_str:
            continue
        try:
            sent_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00"))
            if (now - sent_at).total_seconds() < 86400:  # 24 hours
                return True
        except (ValueError, TypeError):
            continue
    return False


def enrich_notion_from_resend():
    """Poll Resend for delivery status and enrich Notion email_sends DB.
    Optimized: batch-fetches Resend data first, then updates Notion with retries.
    """
    print("=" * 55)
    print("  LEAD DRIP - Enriching Notion from Resend")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    from shared.notion_client import DATABASES
    import time as _time
    h_notion = _notion_headers()
    h_resend = _resend_headers()
    db_id = DATABASES.get("email_sends")

    # Step 1: Query email_sends rows (lead-drip with Resend ID)
    all_rows = []
    start_cursor = None
    while True:
        payload = {
            "filter": {"and": [
                {"property": "Sequence", "select": {"equals": "lead-drip"}},
                {"property": "Resend ID", "rich_text": {"is_not_empty": True}},
            ]},
            "page_size": 100,
        }
        if start_cursor:
            payload["start_cursor"] = start_cursor
        try:
            r = requests.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers=h_notion, json=payload, timeout=(5, 20),
            )
            data = r.json()
            all_rows.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
        except Exception as e:
            print(f"  Query page error: {e}")
            break
        _time.sleep(0.3)

    print(f"  Found {len(all_rows)} email_sends rows")

    # Step 2: Filter to unenriched rows
    to_enrich = []
    already = 0
    for row in all_rows:
        props = row.get("properties", {})
        resend_id_rt = props.get("Resend ID", {}).get("rich_text", [])
        resend_id = "".join(t.get("plain_text", "") for t in resend_id_rt).strip()
        if not resend_id:
            continue
        current_status = props.get("Status", {}).get("select", {})
        status_name = current_status.get("name", "") if current_status else ""
        if status_name in ("Delivered", "Opened", "Clicked", "Bounced", "Complained"):
            already += 1
            continue
        to_enrich.append((row, resend_id))

    print(f"  Already enriched: {already}, to process: {len(to_enrich)}")
    if not to_enrich:
        print("  Nothing to enrich.")
        return

    # Step 3: Batch-fetch Resend statuses (no Notion calls)
    print(f"  Fetching {len(to_enrich)} statuses from Resend...")
    resend_data = {}
    for i, (row, resend_id) in enumerate(to_enrich):
        try:
            r2 = requests.get(
                f"https://api.resend.com/emails/{resend_id}",
                headers=h_resend, timeout=(5, 10),
            )
            if r2.status_code == 200:
                resend_data[resend_id] = r2.json()
        except Exception:
            pass
        if (i + 1) % 20 == 0:
            print(f"    Fetched {i+1}/{len(to_enrich)}")
        _time.sleep(0.5)

    print(f"  Got {len(resend_data)}/{len(to_enrich)} statuses")

    # Step 4: Update Notion rows with retry
    status_map = {
        "sent": "Sent", "delivered": "Delivered", "delivery_delayed": "Delayed",
        "opened": "Opened", "clicked": "Clicked", "bounced": "Bounced",
        "complained": "Complained",
    }
    enriched = 0
    errors = 0
    now_iso = datetime.now(timezone.utc).isoformat()[:19] + ".000Z"

    print("  Updating Notion...")
    for row, resend_id in to_enrich:
        email_data = resend_data.get(resend_id)
        if not email_data:
            continue
        last_event = email_data.get("last_event", "sent")
        created_at = email_data.get("created_at", "")
        new_status = status_map.get(last_event, "Sent")
        update_props = {"Status": {"select": {"name": new_status}}}
        props = row.get("properties", {})
        sent_at = props.get("Sent At", {}).get("date")
        if not sent_at and created_at:
            update_props["Sent At"] = {"date": {"start": created_at[:19] + ".000Z"}}
        if last_event in ("delivered", "opened", "clicked"):
            update_props["Delivered At"] = {"date": {"start": created_at[:19] + ".000Z"}}
        if last_event in ("opened", "clicked"):
            update_props["Opened At"] = {"date": {"start": now_iso}}
        if last_event == "clicked":
            update_props["Clicked At"] = {"date": {"start": now_iso}}
        if last_event in ("bounced", "complained"):
            update_props["Error"] = {"rich_text": [{"text": {"content": last_event}}]}

        for attempt in range(2):
            try:
                resp = requests.patch(
                    f"https://api.notion.com/v1/pages/{row['id']}",
                    headers=h_notion,
                    json={"properties": update_props},
                    timeout=(5, 15),
                )
                if resp.status_code == 200:
                    enriched += 1
                    break
                elif resp.status_code == 429:
                    _time.sleep(2)
                else:
                    errors += 1
                    break
            except Exception:
                if attempt == 0:
                    _time.sleep(1)
                else:
                    errors += 1

        if (enriched + errors) % 10 == 0 and (enriched + errors) > 0:
            print(f"    Progress: {enriched} enriched, {errors} errors")
        _time.sleep(0.35)

    print(f"\n  Done! Enriched: {enriched} | Already: {already} | Errors: {errors}")
    print("=" * 55)



def notify_outlook_reply(subject, from_email, body_preview=""):
    """Send a notification to hedgeedge@outlook.com when a reply is detected."""
    h = _resend_headers()
    text = f"""New reply to lead drip email!

From: {from_email}
Subject: {subject}
Preview: {body_preview[:500] if body_preview else '(no preview)'}

---
Check your inbox and follow up promptly.
This is an automated notification from Hedge Edge Lead Drip.
"""
    payload = {
        "from": "Hedge Edge Alerts <alerts@hedgedge.info>",
        "to": ["hedgeedge@outlook.com"],
        "subject": f"[Lead Reply] {from_email} responded to: {subject[:50]}",
        "text": text,
        "tags": [
            {"name": "sequence", "value": "lead-drip-notification"},
            {"name": "type", "value": "reply-alert"},
        ],
    }
    try:
        r = requests.post("https://api.resend.com/emails", headers=h, json=payload, timeout=15)
        if r.status_code == 200:
            print(f"    Notification sent to hedgeedge@outlook.com for reply from {from_email}")
        else:
            print(f"    Notification failed: {r.text}")
    except Exception as e:
        print(f"    Notification error: {e}")

def sync_notion_leads():
    """Query Notion leads_crm for 'Lead Drip' tagged contacts and add any new ones to Resend + state."""
    print("\n  Syncing new leads from Notion...")
    try:
        from shared.notion_client import DATABASES
        h = _notion_headers()
        db_id = DATABASES.get("leads_crm")

        # Query all Lead Drip tagged contacts from Notion
        all_notion_leads = []
        start_cursor = None
        while True:
            payload = {
                "filter": {
                    "property": "Tags",
                    "multi_select": {"contains": "Lead Drip"},
                },
                "page_size": 100,
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor
            r = requests.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers=h, json=payload, timeout=15,
            )
            data = r.json()
            all_notion_leads.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")

        # Extract email + name from each lead
        notion_contacts = []
        for page in all_notion_leads:
            props = page.get("properties", {})
            email_prop = props.get("Email", {}).get("email")
            if not email_prop:
                continue
            first = "".join(t.get("plain_text", "") for t in props.get("First Name", {}).get("rich_text", []))
            last = "".join(t.get("plain_text", "") for t in props.get("Last Name", {}).get("rich_text", []))
            name_title = "".join(t.get("plain_text", "") for t in props.get("Name", {}).get("title", []))
            notion_contacts.append({
                "email": email_prop.strip().lower(),
                "first_name": first.strip() or name_title.split()[0] if name_title else "",
                "last_name": last.strip(),
                "full_name": f"{first} {last}".strip() or name_title,
            })

        print(f"  Notion leads_crm has {len(notion_contacts)} Lead Drip contacts")

        # Compare against local state
        state = load_state()
        existing = set(state["contacts"].keys())
        new_leads = [c for c in notion_contacts if c["email"] not in existing]

        if not new_leads:
            print("  No new leads to import.")
            return 0

        print(f"  Found {len(new_leads)} NEW leads - adding to Resend + state...")
        added = 0
        for lead in new_leads:
            # Add to Resend audience
            try:
                add_contact_to_audience(lead["email"], lead["first_name"], lead["last_name"])
            except Exception:
                pass  # Duplicate is fine

            # Add to local state
            state["contacts"][lead["email"]] = {
                "name": lead["full_name"],
                "last_sent": 0,
                "sends": [],
            }
            added += 1
            if added % 25 == 0:
                print(f"    ...added {added}/{len(new_leads)}")
            time.sleep(0.4)

        save_state(state)
        print(f"  Imported {added} new leads from Notion.")
        return added

    except Exception as e:
        print(f"  Notion lead sync error: {e}")
        import traceback
        traceback.print_exc()
        return 0



def rebuild_state_from_notion():
    """Rebuild local state from Notion Wave data. Used when state file is missing (Railway ephemeral containers)."""
    print("  Rebuilding state from Notion Wave data...")
    try:
        from shared.notion_client import DATABASES
        h = _notion_headers()
        db_id = DATABASES.get("leads_crm")

        all_leads = []
        start_cursor = None
        while True:
            payload = {
                "filter": {"property": "Tags", "multi_select": {"contains": "Lead Drip"}},
                "page_size": 100,
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor
            r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                              headers=h, json=payload, timeout=15)
            data = r.json()
            all_leads.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")

        state = {"contacts": {}, "runs": [], "total_sent": 0}
        for page in all_leads:
            props = page.get("properties", {})
            email = props.get("Email", {}).get("email")
            if not email:
                continue

            wave_sel = props.get("Wave", {}).get("select")
            wave_name = wave_sel.get("name", "") if wave_sel else ""

            last_sent = 0
            if wave_name.startswith("Lead email "):
                try:
                    last_sent = int(wave_name.split()[-1])
                except ValueError:
                    pass
            elif wave_name == "Complete":
                last_sent = 5

            first = "".join(t.get("plain_text", "") for t in props.get("First Name", {}).get("rich_text", []))
            last = "".join(t.get("plain_text", "") for t in props.get("Last Name", {}).get("rich_text", []))
            full_name = f"{first} {last}".strip()

            state["contacts"][email.strip().lower()] = {
                "name": full_name,
                "last_sent": last_sent,
                "sends": [],
            }

        save_state(state)
        print(f"  Rebuilt state: {len(state['contacts'])} contacts from Notion")
        return state
    except Exception as e:
        print(f"  State rebuild failed: {e}")
        return {"contacts": {}, "runs": [], "total_sent": 0}

#  Core Actions 

def run_drip():
    """Main drip action: send next email to each contact who is due."""
    print("=" * 55)
    print("  LEAD DRIP - Sending batch")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)
    
    # 0. Sync new leads from Notion leads_crm
    sync_notion_leads()

    # 1. Fetch contacts from Resend
    print("\n  Fetching contacts from Resend audience...")
    contacts = get_audience_contacts()
    if not contacts:
        print("  No contacts in audience. Import contacts first.")
        print("  Use: python scripts/lead_drip.py --action import-csv --file contacts.csv")
        return
    print(f"  Found {len(contacts)} active contacts")
    
    # 2. Load state (rebuild from Notion if no local state  e.g. Railway)
    state = load_state()
    if not state.get("contacts"):
        state = rebuild_state_from_notion()
    
    # 3. Determine which contacts need which email
    sends_by_email = {i: [] for i in range(1, 6)}  # email_num -> [contact]
    already_complete = 0
    
    for contact in contacts:
        email = contact["email"]
        contact_state = state["contacts"].get(email, {"last_sent": 0, "sends": []})
        next_email = (contact_state.get("last_sent") or 0) + 1
        
        if next_email > 5:
            already_complete += 1
            continue
        
        name = (contact.get("first_name") or "").strip()
        sends_by_email[next_email].append({"email": email, "name": name})
    
    print(f"  Already completed sequence: {already_complete}")
    print(f"\n  Queue:")
    for num in range(1, 6):
        print(f"    Email {num}: {len(sends_by_email[num])} contacts pending")
    
    # 4. Fetch email templates from Notion
    print("\n  Loading email templates from Notion...")
    templates = {}
    for email_def in LEAD_EMAILS:
        tpl = fetch_email_template(email_def)
        templates[tpl["num"]] = tpl
        print(f"    Email {tpl['num']}: \"{tpl['subject'][:50]}\"")
    
    # 4b. Dedup: fetch all prior sends from Resend
    print("\n  Loading Resend send history for dedup protection...")
    already_sent_set = get_recent_sends()
    print(f"    {len(already_sent_set)} prior send records loaded")

    # 5. Send emails (up to BATCH_SIZE per email number, capped at DAILY_CAP)
    total_sent = 0
    total_failed = 0
    skipped = 0
    run_log = {"timestamp": datetime.now(timezone.utc).isoformat(), "sent": 0, "failed": 0, "details": []}
    
    for email_num in range(1, 6):
        if total_sent >= DAILY_CAP:
            print(f"\n  Daily cap ({DAILY_CAP}) reached. Stopping.")
            break
        batch = sends_by_email[email_num][:BATCH_SIZE]
        if not batch:
            continue
        
        tpl = templates[email_num]
        print(f"\n  --- Email {email_num}: \"{tpl['subject'][:45]}\" ({len(batch)} sends) ---")
        
        for contact in batch:
            addr = contact["email"]
            name = contact["name"] or "there"
            
            # Personalize body
            body = tpl["body"].replace("{{Name}}", name)
            
            # Dedup: skip if Resend already sent this exact email to this recipient
            if (addr.lower(), tpl["subject"]) in already_sent_set:
                print(f"    SKIP {addr} (already sent)")
                skipped += 1
                continue

            # Yesterday guard: skip if contact got an email in the last 24h
            if was_sent_yesterday(addr, state):
                print(f"    SKIP {addr} (sent within last 24h)")
                skipped += 1
                continue

            # Daily cap
            if total_sent >= DAILY_CAP:
                print(f"    Daily cap ({DAILY_CAP}) reached.")
                break

            # Send
            ok, result = send_plain_email(addr, tpl["subject"], body, email_num)
            
            if ok:
                resend_id = result.get("id", "")
                total_sent += 1
                
                # Update state
                if addr not in state["contacts"]:
                    state["contacts"][addr] = {"last_sent": 0, "sends": []}
                state["contacts"][addr]["last_sent"] = email_num
                state["contacts"][addr]["sends"].append({
                    "email_num": email_num,
                    "resend_id": resend_id,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                })
                

                # Save state IMMEDIATELY (before any Notion calls)
                save_state(state)

                run_log["details"].append({"email": addr, "num": email_num, "status": "sent", "id": resend_id})
                print(f"    OK  {addr}")

                # Log to Notion (best-effort, non-blocking)
                try:
                    log_send_to_notion(tpl["subject"], addr, email_num, resend_id)
                except Exception:
                    pass
            else:
                total_failed += 1
                error = result.get("message", str(result))
                try:
                    log_send_to_notion(tpl["subject"], addr, email_num, "", error=error)
                except Exception:
                    pass
                run_log["details"].append({"email": addr, "num": email_num, "status": "failed", "error": error})
                print(f"    FAIL  {addr}: {error}")

            time.sleep(SEND_DELAY)

    run_log["sent"] = total_sent
    run_log["failed"] = total_failed
    state["runs"].append(run_log)
    state["total_sent"] = state.get("total_sent", 0) + total_sent
    save_state(state)
    
    # 7. Summary
    print(f"\n  {'=' * 40}")
    print(f"  BATCH COMPLETE")
    print(f"  Sent: {total_sent}  |  Failed: {total_failed}  |  Skipped (dedup): {skipped}")
    print(f"  Total lifetime sends: {state['total_sent']}")
    print(f"  {'=' * 40}")


def show_status():
    """Show current drip status."""
    state = load_state()
    contacts = state.get("contacts", {})
    
    print("=" * 55)
    print("  LEAD DRIP STATUS")
    print("=" * 55)
    print(f"\n  Tracked contacts: {len(contacts)}")
    print(f"  Total lifetime sends: {state.get('total_sent', 0)}")
    print(f"  Total runs: {len(state.get('runs', []))}")
    
    # Distribution
    dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for c in contacts.values():
        ls = c.get("last_sent", 0)
        dist[ls] = dist.get(ls, 0) + 1
    
    print(f"\n  Sequence progress:")
    print(f"    Not started:  {dist[0]}")
    for i in range(1, 6):
        pct = f" ({dist[i]/len(contacts)*100:.0f}%)" if contacts else ""
        print(f"    Email {i} sent: {dist[i]}{pct}")
    
    # Last run
    runs = state.get("runs", [])
    if runs:
        last = runs[-1]
        print(f"\n  Last run: {last.get('timestamp', '?')[:19]}")
        print(f"    Sent: {last.get('sent', 0)}  Failed: {last.get('failed', 0)}")
    
    # Audience check
    print(f"\n  Checking Resend audience...")
    try:
        audience_contacts = get_audience_contacts()
        print(f"  Resend contacts: {len(audience_contacts)}")
        untracked = [c for c in audience_contacts if c["email"] not in contacts]
        if untracked:
            print(f"  New (untracked): {len(untracked)} - will receive Email 1 on next run")
    except Exception as e:
        print(f"  Could not fetch audience: {e}")


def preview_emails():
    """Preview all 5 email templates without sending."""
    print("=" * 55)
    print("  LEAD DRIP - Email Preview")
    print("=" * 55)
    
    for email_def in LEAD_EMAILS:
        tpl = fetch_email_template(email_def)
        link_flag = "NO LINKS" if tpl["num"] <= 3 else "HAS LINK"
        print(f"\n  {'' * 50}")
        sender = SENDERS.get(tpl["num"], DEFAULT_SENDER)
        print(f"  EMAIL {tpl['num']} [{link_flag}]")
        print(f"  From: {sender}")
        print(f"  Subject: {tpl['subject']}")
        print(f"  {'' * 50}")
        # Show first 200 chars of body
        print(f"  {tpl['body'][:200]}...")
        print(f"  [{len(tpl['body'])} chars total]")


def import_csv(filepath):
    """Import contacts from CSV into Resend audience."""
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return
    
    print(f"  Importing from: {filepath}")
    added = 0
    skipped = 0
    failed = 0
    
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Support common column names
        for row in reader:
            email = (row.get("email") or row.get("Email") or row.get("EMAIL") or "").strip()
            if not email or "@" not in email:
                skipped += 1
                continue
            
            first = (row.get("first_name") or row.get("First Name") or row.get("name") or row.get("Name") or "").strip()
            last = (row.get("last_name") or row.get("Last Name") or "").strip()
            
            # Split single "name" field into first/last
            if first and not last and " " in first:
                parts = first.split(" ", 1)
                first = parts[0]
                last = parts[1]
            
            ok, result = add_contact_to_audience(email, first, last)
            if ok:
                added += 1
                print(f"    + {email} ({first} {last})")
            else:
                # Check if duplicate (already exists)
                msg = result.get("message", "")
                if "already exists" in msg.lower():
                    skipped += 1
                else:
                    failed += 1
                    print(f"    FAIL {email}: {msg}")
            
            time.sleep(0.5)  # Rate limit
    
    print(f"\n  Import complete: {added} added, {skipped} skipped, {failed} failed")


def reset_state():
    """Reset all drip state. Dangerous!"""
    confirm = input("  This will reset ALL drip tracking. Type 'RESET' to confirm: ")
    if confirm.strip() == "RESET":
        save_state({"contacts": {}, "runs": [], "total_sent": 0})
        print("  State reset.")
    else:
        print("  Cancelled.")


#  CLI 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hedge Edge Lead Drip Automation")
    parser.add_argument("--action", required=True,
                        choices=["run", "status", "preview", "import-csv", "reset", "sync-waves", "enrich"])
    parser.add_argument("--file", help="CSV file path for import-csv action")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Max sends per email per run (default: 50)")
    args = parser.parse_args()
    
    if args.batch_size:
        BATCH_SIZE = args.batch_size
    
    print()
    if args.action == "run":
        run_drip()
    elif args.action == "status":
        show_status()
    elif args.action == "preview":
        preview_emails()
    elif args.action == "import-csv":
        if not args.file:
            print("  --file required for import-csv action")
            sys.exit(1)
        import_csv(args.file)
    elif args.action == "sync-waves":
        sync_all_waves()
    elif args.action == "enrich":
        enrich_notion_from_resend()
    elif args.action == "reset":
        reset_state()
    print()
