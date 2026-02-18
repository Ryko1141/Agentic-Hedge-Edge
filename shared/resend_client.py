"""
Hedge Edge — Resend Email Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email sending, batch campaigns, and audience management via Resend API.
Docs: https://resend.com/docs/api-reference

Usage:
    from shared.resend_client import send_email, send_batch, list_emails
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://api.resend.com"


def _headers() -> dict:
    key = os.getenv("RESEND_API_KEY")
    if not key:
        raise RuntimeError("RESEND_API_KEY must be set in .env")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    from_addr: str = "Hedge Edge <hello@hedgedge.info>",
    reply_to: Optional[str] = None,
    tags: Optional[list[dict]] = None,
) -> dict:
    """
    Send a single email.
    
    Args:
        to: Recipient email(s)
        subject: Email subject
        html: HTML body content
        from_addr: Sender address (must be verified domain)
        reply_to: Reply-to email
        tags: List of {"name": "key", "value": "val"} for tracking
    """
    payload = {
        "from": from_addr,
        "to": [to] if isinstance(to, str) else to,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if tags:
        payload["tags"] = tags
    r = requests.post(f"{BASE_URL}/emails", headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def send_batch(emails: list[dict]) -> dict:
    """
    Send a batch of emails (up to 100).
    Each item: {"from", "to", "subject", "html", ...}
    """
    r = requests.post(f"{BASE_URL}/emails/batch", headers=_headers(), json=emails, timeout=30)
    r.raise_for_status()
    return r.json()


def get_email(email_id: str) -> dict:
    """Get email delivery status by ID."""
    r = requests.get(f"{BASE_URL}/emails/{email_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def list_domains() -> list[dict]:
    """List verified sending domains."""
    r = requests.get(f"{BASE_URL}/domains", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])


# ──────────────────────────────────────────────
# Audience / Contact Management
# ──────────────────────────────────────────────

def create_audience(name: str) -> dict:
    """Create a new audience list."""
    r = requests.post(
        f"{BASE_URL}/audiences",
        headers=_headers(),
        json={"name": name},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_audiences() -> list[dict]:
    """List all audiences."""
    r = requests.get(f"{BASE_URL}/audiences", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])


def add_contact(audience_id: str, email: str, first_name: str = "",
                last_name: str = "", unsubscribed: bool = False) -> dict:
    """Add a contact to an audience."""
    payload = {"email": email, "unsubscribed": unsubscribed}
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    r = requests.post(
        f"{BASE_URL}/audiences/{audience_id}/contacts",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_contacts(audience_id: str) -> list[dict]:
    """List contacts in an audience."""
    r = requests.get(
        f"{BASE_URL}/audiences/{audience_id}/contacts",
        headers=_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", [])
