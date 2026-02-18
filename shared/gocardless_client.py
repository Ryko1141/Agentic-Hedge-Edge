"""
Hedge Edge — GoCardless Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GoCardless API — payments, mandates, customers, payouts.
Docs: https://developer.gocardless.com/api-reference

Usage:
    from shared.gocardless_client import list_payments, list_customers, create_payment
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))


def _base_url() -> str:
    env = os.getenv("GOCARDLESS_ENVIRONMENT", "live")
    if env == "sandbox":
        return "https://api-sandbox.gocardless.com"
    return "https://api.gocardless.com"


def _headers() -> dict:
    token = os.getenv("GOCARDLESS_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("GOCARDLESS_ACCESS_TOKEN must be set in .env")
    return {
        "Authorization": f"Bearer {token}",
        "GoCardless-Version": "2015-07-06",
        "Content-Type": "application/json",
    }


def list_payments(limit: int = 50, status: Optional[str] = None) -> list[dict]:
    """
    List payments.
    
    Args:
        limit: Max results
        status: Filter: 'pending_customer_approval', 'pending_submission',
                'submitted', 'confirmed', 'paid_out', 'cancelled', 'failed'
    """
    params = {"limit": limit}
    if status:
        params["status"] = status
    r = requests.get(
        f"{_base_url()}/payments",
        headers=_headers(),
        params=params,
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("payments", [])


def get_payment(payment_id: str) -> dict:
    """Get a specific payment."""
    r = requests.get(f"{_base_url()}/payments/{payment_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("payments", {})


def list_customers(limit: int = 50) -> list[dict]:
    """List customers."""
    r = requests.get(
        f"{_base_url()}/customers",
        headers=_headers(),
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("customers", [])


def list_mandates(limit: int = 50, status: Optional[str] = None) -> list[dict]:
    """List direct debit mandates."""
    params = {"limit": limit}
    if status:
        params["status"] = status
    r = requests.get(
        f"{_base_url()}/mandates",
        headers=_headers(),
        params=params,
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("mandates", [])


def list_payouts(limit: int = 20) -> list[dict]:
    """List payouts to bank account."""
    r = requests.get(
        f"{_base_url()}/payouts",
        headers=_headers(),
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("payouts", [])


def create_payment(amount: int, currency: str, mandate_id: str,
                   description: str = "", metadata: dict = None) -> dict:
    """
    Create a payment (direct debit collection).
    
    Args:
        amount: Amount in pence/cents (e.g., 2900 = £29.00)
        currency: 'GBP', 'EUR', 'USD'
        mandate_id: Customer's mandate ID
        description: Payment description
        metadata: Optional metadata dict
    """
    payload = {
        "payments": {
            "amount": amount,
            "currency": currency,
            "links": {"mandate": mandate_id},
            "description": description,
        }
    }
    if metadata:
        payload["payments"]["metadata"] = metadata
    r = requests.post(
        f"{_base_url()}/payments",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("payments", {})


def cancel_payment(payment_id: str) -> dict:
    """Cancel a pending payment."""
    r = requests.post(
        f"{_base_url()}/payments/{payment_id}/actions/cancel",
        headers=_headers(),
        json={},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("payments", {})
