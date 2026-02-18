"""
Hedge Edge — Cal.com Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cal.com v2 API — event types, bookings, availability.
Docs: https://cal.com/docs/api-reference/v2

Usage:
    from shared.calcom_client import list_event_types, list_bookings, create_booking
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))


def _base_url() -> str:
    return os.getenv("CAL_API_URL", "https://api.cal.eu")


def _headers() -> dict:
    key = os.getenv("CAL_API_KEY")
    if not key:
        raise RuntimeError("CAL_API_KEY must be set in .env")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "cal-api-version": "2024-08-13",
    }


def list_event_types() -> list[dict]:
    """List all event types (demo calls, discovery calls, etc.)."""
    r = requests.get(
        f"{_base_url()}/v2/event-types",
        headers=_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def get_event_type(event_type_id: int) -> dict:
    """Get details of a specific event type."""
    r = requests.get(
        f"{_base_url()}/v2/event-types/{event_type_id}",
        headers=_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", {})


def list_bookings(status: str = "upcoming") -> list[dict]:
    """
    List bookings.
    
    Args:
        status: 'upcoming', 'recurring', 'past', 'cancelled', 'unconfirmed'
    """
    r = requests.get(
        f"{_base_url()}/v2/bookings",
        headers=_headers(),
        params={"status": status},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def get_booking(booking_uid: str) -> dict:
    """Get a specific booking by UID."""
    r = requests.get(
        f"{_base_url()}/v2/bookings/{booking_uid}",
        headers=_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", {})


def cancel_booking(booking_uid: str, reason: str = "") -> dict:
    """Cancel a booking."""
    payload = {}
    if reason:
        payload["cancellationReason"] = reason
    r = requests.delete(
        f"{_base_url()}/v2/bookings/{booking_uid}",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_availability(event_type_id: int, start_time: str, end_time: str) -> dict:
    """
    Check availability slots.
    
    Args:
        event_type_id: Event type ID
        start_time: ISO datetime string
        end_time: ISO datetime string
    """
    r = requests.get(
        f"{_base_url()}/v2/slots/available",
        headers=_headers(),
        params={
            "startTime": start_time,
            "endTime": end_time,
            "eventTypeId": event_type_id,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("data", {})
