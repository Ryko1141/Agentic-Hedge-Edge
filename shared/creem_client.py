"""
Hedge Edge — Creem.io Payment Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creem.io API — subscriptions, customers, products, invoices.
Docs: https://docs.creem.io

Usage:
    from shared.creem_client import list_subscriptions, list_customers, get_product
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))


def _config(use_test: bool = False) -> tuple[str, str]:
    """Return (base_url, api_key) for live or test environment."""
    if use_test:
        url = os.getenv("CREEM_TEST_API_URL", "https://test-api.creem.io")
        key = os.getenv("CREEM_TEST_API_KEY")
    else:
        url = os.getenv("CREEM_LIVE_API_URL", "https://api.creem.io")
        key = os.getenv("CREEM_LIVE_API_KEY")
    if not key:
        env = "test" if use_test else "live"
        raise RuntimeError(f"CREEM_{env.upper()}_API_KEY must be set in .env")
    return url, key


def _headers(use_test: bool = False) -> dict:
    _, key = _config(use_test)
    return {"x-api-key": key, "Content-Type": "application/json"}


def _url(path: str, use_test: bool = False) -> str:
    base, _ = _config(use_test)
    return f"{base}/v1{path}"


def list_products(use_test: bool = False) -> list[dict]:
    """List all products."""
    r = requests.get(
        _url("/products", use_test),
        headers=_headers(use_test),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("items", r.json().get("data", []))


def get_product(product_id: str, use_test: bool = False) -> dict:
    """Get a specific product."""
    r = requests.get(
        _url(f"/products/{product_id}", use_test),
        headers=_headers(use_test),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_subscriptions(use_test: bool = False) -> list[dict]:
    """List all subscriptions."""
    r = requests.get(
        _url("/subscriptions", use_test),
        headers=_headers(use_test),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("items", r.json().get("data", []))


def get_subscription(subscription_id: str, use_test: bool = False) -> dict:
    """Get a specific subscription."""
    r = requests.get(
        _url(f"/subscriptions/{subscription_id}", use_test),
        headers=_headers(use_test),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_customers(use_test: bool = False) -> list[dict]:
    """List all customers."""
    r = requests.get(
        _url("/customers", use_test),
        headers=_headers(use_test),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("items", r.json().get("data", []))


def create_checkout_link(
    product_id: str,
    success_url: str,
    cancel_url: Optional[str] = None,
    customer_email: Optional[str] = None,
    use_test: bool = False,
) -> dict:
    """
    Create a checkout session link.
    
    Args:
        product_id: Creem product ID
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect on cancel
        customer_email: Pre-fill customer email
    """
    payload = {"product_id": product_id, "success_url": success_url}
    if cancel_url:
        payload["cancel_url"] = cancel_url
    if customer_email:
        payload["customer_email"] = customer_email
    r = requests.post(
        _url("/checkouts", use_test),
        headers=_headers(use_test),
        json=payload,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def cancel_subscription(subscription_id: str, use_test: bool = False) -> dict:
    """Cancel a subscription."""
    r = requests.post(
        _url(f"/subscriptions/{subscription_id}/cancel", use_test),
        headers=_headers(use_test),
        json={},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()
