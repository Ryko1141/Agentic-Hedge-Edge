"""
Notion ERP — Schema Setup Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Adds proper column properties to all 26 Notion databases.
Run once to wire up the ERP; safe to re-run (idempotent — existing columns kept).

Usage:
    python -m shared.setup_notion_schemas          # all databases
    python -m shared.setup_notion_schemas task_log  # single database
"""

import os, sys, json, time
import requests
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

# Import database IDs from the shared client
sys.path.insert(0, _ws_root)
from shared.notion_client import DATABASES

_NOTION_VERSION = "2022-06-28"
_API_BASE = "https://api.notion.com/v1"

def _get_token() -> str:
    token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    if not token:
        mcp_path = os.path.join(_ws_root, ".vscode", "mcp.json")
        if os.path.exists(mcp_path):
            with open(mcp_path) as f:
                mcp = json.load(f)
            token = (
                mcp.get("servers", {})
                .get("makenotion/notion-mcp-server", {})
                .get("env", {})
                .get("NOTION_TOKEN")
            )
    if not token:
        raise RuntimeError("No Notion token found")
    return token


# ──────────────────────────────────────────────
# DB_SCHEMAS: property name → Notion property type
# (excludes "Name" title column which already exists)
# ──────────────────────────────────────────────
DB_SCHEMAS = {
    # ── Strategy & OKRs ──────────────────────────
    "okrs": {
        "Objective":     "rich_text",
        "Key Result":    "rich_text",
        "Quarter":       "select",
        "Owner":         "select",
        "Status":        "select",
        "Progress":      "number",
        "Target Value":  "number",
        "Current Value": "number",
        "Due Date":      "date",
    },
    "competitors": {
        "Website":       "url",
        "Category":      "select",
        "Pricing":       "rich_text",
        "Strengths":     "rich_text",
        "Weaknesses":    "rich_text",
        "Platforms":     "multi_select",
        "Threat Level":  "select",
        "Last Reviewed": "date",
        "Notes":         "rich_text",
    },
    "strategic_initiatives": {
        "Description":  "rich_text",
        "Owner":        "select",
        "Status":       "select",
        "Priority":     "select",
        "Category":     "select",
        "Impact":       "select",
        "Start Date":   "date",
        "Target Date":  "date",
        "Outcome":      "rich_text",
    },

    # ── Finance ───────────────────────────────────
    "mrr_tracker": {
        "Date":         "date",
        "MRR":          "number",
        "ARR":          "number",
        "New Subs":     "number",
        "Churned Subs": "number",
        "Net New":      "number",
        "Churn Rate":   "number",
        "ARPU":         "number",
        "Notes":        "rich_text",
    },
    "expense_log": {
        "Amount":    "number",
        "Currency":  "select",
        "Category":  "select",
        "Vendor":    "rich_text",
        "Date":      "date",
        "Recurring": "checkbox",
        "Receipt":   "url",
        "Notes":     "rich_text",
    },
    "ib_commissions": {
        "Broker":         "select",
        "Period":         "rich_text",
        "Lots Traded":    "number",
        "Commission":     "number",
        "Referred Users": "number",
        "Date":           "date",
        "Status":         "select",
        "Notes":          "rich_text",
    },
    "pnl_snapshots": {
        "Date":         "date",
        "Period":       "select",
        "Revenue":      "number",
        "COGS":         "number",
        "Gross Profit": "number",
        "OpEx":         "number",
        "Net Profit":   "number",
        "Notes":        "rich_text",
    },

    # ── Sales Pipeline ────────────────────────────
    "leads_crm": {
        "Email":        "email",
        "Source":       "select",
        "Status":       "select",
        "Value":        "number",
        "Last Contact": "date",
        "Tags":         "multi_select",
        "Assigned To":  "select",
        "Notes":        "rich_text",
    },
    "demo_log": {
        "Lead":       "rich_text",
        "Date":       "date",
        "Duration":   "number",
        "Outcome":    "select",
        "Booked Via": "select",
        "Follow Up":  "date",
        "Notes":      "rich_text",
    },
    "proposals": {
        "Lead":       "rich_text",
        "Tier":       "select",
        "Amount":     "number",
        "Status":     "select",
        "Sent Date":  "date",
        "Expires":    "date",
        "Close Date": "date",
        "Notes":      "rich_text",
    },

    # ── Marketing ─────────────────────────────────
    "campaigns": {
        "Channel":     "select",
        "Status":      "select",
        "Start Date":  "date",
        "End Date":    "date",
        "Budget":      "number",
        "Spend":       "number",
        "Impressions": "number",
        "Clicks":      "number",
        "Conversions": "number",
        "Notes":       "rich_text",
    },
    "email_sequences": {
        "Trigger":          "select",
        "Status":           "select",
        "Emails Count":     "number",
        "Subject Line":     "rich_text",
        "Open Rate":        "number",
        "Click Rate":       "number",
        "Unsubscribe Rate": "number",
        "Last Updated":     "date",
        "Notes":            "rich_text",
    },
    "email_sends": {
        "Recipient":      "email",
        "Template":       "select",
        "Sequence":       "select",
        "Status":         "select",
        "Resend ID":      "rich_text",
        "Day":            "number",
        "Sent At":        "date",
        "Delivered At":   "date",
        "Opened At":      "date",
        "Clicked At":     "date",
        "User ID":        "rich_text",
        "User Name":      "rich_text",
        "Error":          "rich_text",
    },
    "seo_keywords": {
        "Keyword":      "rich_text",
        "Volume":       "number",
        "Difficulty":   "number",
        "Current Rank": "number",
        "Target Page":  "url",
        "Intent":       "select",
        "Status":       "select",
        "Last Checked": "date",
    },
    "landing_page_tests": {
        "Page URL":        "url",
        "Variant":         "select",
        "Hypothesis":      "rich_text",
        "Status":          "select",
        "Start Date":      "date",
        "End Date":        "date",
        "Visitors":        "number",
        "Conversions":     "number",
        "Conversion Rate": "number",
        "Notes":           "rich_text",
    },

    # ── Content ───────────────────────────────────
    "content_calendar": {
        "Platform":     "select",
        "Status":       "select",
        "Publish Date": "date",
        "Topic":        "rich_text",
        "Content Type": "select",
        "URL":          "url",
        "Tags":         "multi_select",
        "Notes":        "rich_text",
    },
    "video_pipeline": {
        "Status":          "select",
        "Platform":        "select",
        "Publish Date":    "date",
        "Script URL":      "url",
        "Video URL":       "url",
        "Duration":        "number",
        "Thumbnail Ready": "checkbox",
        "Notes":           "rich_text",
    },

    # ── Product ───────────────────────────────────
    "feature_roadmap": {
        "Description":    "rich_text",
        "Status":         "select",
        "Priority":       "select",
        "Platform":       "multi_select",
        "Requested By":   "select",
        "Target Release": "rich_text",
        "Votes":          "number",
        "Due Date":       "date",
        "Notes":          "rich_text",
    },
    "bug_tracker": {
        "Description":        "rich_text",
        "Severity":           "select",
        "Status":             "select",
        "Platform":           "select",
        "Reported By":        "rich_text",
        "Steps to Reproduce": "rich_text",
        "Fixed In":           "rich_text",
        "Date Reported":      "date",
    },
    "release_log": {
        "Version":          "rich_text",
        "Release Date":     "date",
        "Platform":         "multi_select",
        "Status":           "select",
        "Changelog":        "rich_text",
        "Breaking Changes": "checkbox",
        "Download URL":     "url",
        "Notes":            "rich_text",
    },

    # ── Community ─────────────────────────────────
    "feedback": {
        "Source":     "select",
        "Category":  "select",
        "Sentiment": "select",
        "Feedback":  "rich_text",
        "User Email": "email",
        "Date":      "date",
        "Actioned":  "checkbox",
        "Notes":     "rich_text",
    },
    "support_tickets": {
        "Status":      "select",
        "Priority":    "select",
        "Category":    "select",
        "User Email":  "email",
        "Channel":     "select",
        "Description": "rich_text",
        "Resolution":  "rich_text",
        "Created":     "date",
        "Resolved":    "date",
    },
    "community_events": {
        "Event Type":  "select",
        "Status":      "select",
        "Date":        "date",
        "Platform":    "select",
        "Attendees":   "number",
        "Description": "rich_text",
        "Link":        "url",
        "Notes":       "rich_text",
    },

    # ── Analytics ─────────────────────────────────
    "kpi_snapshots": {
        "Date":         "date",
        "Period":       "select",
        "MRR":          "number",
        "Active Users": "number",
        "New Signups":  "number",
        "Churn Rate":   "number",
        "CAC":          "number",
        "LTV":          "number",
        "NPS":          "number",
        "Notes":        "rich_text",
    },
    "funnel_metrics": {
        "Date":            "date",
        "Stage":           "select",
        "Count":           "number",
        "Conversion Rate": "number",
        "Source":          "select",
        "Period":          "select",
        "Notes":           "rich_text",
    },

    # ── Partnerships ──────────────────────────────
    "partnerships": {
        "Partner Type":     "select",
        "Status":           "select",
        "Contact Email":    "email",
        "Commission Model": "rich_text",
        "Revenue Share":    "number",
        "Start Date":       "date",
        "Website":          "url",
        "Notes":            "rich_text",
    },

    # ── Orchestrator ──────────────────────────────
    "task_log": {
        "Task":           "rich_text",
        "Agent":          "select",
        "Status":         "select",
        "Priority":       "select",
        "Created":        "date",
        "Completed":      "date",
        "Output Summary": "rich_text",
        "Error":          "rich_text",
    },
}


# ──────────────────────────────────────────────
# Property type → Notion schema definition
# ──────────────────────────────────────────────
def _make_property_def(prop_type: str) -> dict:
    """Convert a simple type name to a Notion property schema object."""
    if prop_type == "rich_text":
        return {"rich_text": {}}
    elif prop_type == "number":
        return {"number": {"format": "number"}}
    elif prop_type == "select":
        return {"select": {"options": []}}
    elif prop_type == "multi_select":
        return {"multi_select": {"options": []}}
    elif prop_type == "date":
        return {"date": {}}
    elif prop_type == "checkbox":
        return {"checkbox": {}}
    elif prop_type == "url":
        return {"url": {}}
    elif prop_type == "email":
        return {"email": {}}
    else:
        raise ValueError(f"Unsupported property type: {prop_type}")


def setup_database(db_key: str, token: str) -> dict:
    """Add schema properties to a single Notion database."""
    db_id = DATABASES.get(db_key)
    if not db_id:
        raise ValueError(f"Unknown database: {db_key}")

    schema = DB_SCHEMAS.get(db_key)
    if not schema:
        raise ValueError(f"No schema defined for: {db_key}")

    # Build properties payload
    properties = {}
    for prop_name, prop_type in schema.items():
        properties[prop_name] = _make_property_def(prop_type)

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }

    resp = requests.patch(
        f"{_API_BASE}/databases/{db_id}",
        headers=headers,
        json={"properties": properties},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def setup_all(target_key: str = None):
    """Set up schemas for all databases (or a single one if target_key given)."""
    token = _get_token()
    keys = [target_key] if target_key else list(DB_SCHEMAS.keys())
    total = len(keys)
    ok = 0
    failed = []

    for i, key in enumerate(keys, 1):
        db_id = DATABASES.get(key, "???")
        schema = DB_SCHEMAS.get(key, {})
        print(f"[{i}/{total}] {key} ({len(schema)} props) ... ", end="", flush=True)
        try:
            result = setup_database(key, token)
            prop_count = len(result.get("properties", {}))
            print(f"✅  ({prop_count} total properties)")
            ok += 1
        except Exception as e:
            print(f"❌  {e}")
            failed.append((key, str(e)))

        # Rate limit: Notion allows 3 req/sec for integrations
        if i < total:
            time.sleep(0.4)

    print(f"\n{'='*50}")
    print(f"Setup complete: {ok}/{total} databases updated")
    if failed:
        print(f"Failed ({len(failed)}):")
        for k, err in failed:
            print(f"  - {k}: {err}")
    return ok, failed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    setup_all(target)
