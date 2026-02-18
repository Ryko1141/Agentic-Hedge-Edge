"""
Hedge Edge — Supabase Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shared Supabase access for user data, subscriptions, and auth.

Usage:
    from shared.supabase_client import get_supabase, query_users, get_subscription
"""

import os
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("pip install supabase — required for Supabase access")


_client: Optional[Client] = None


def get_supabase(use_service_role: bool = False) -> Client:
    """Return a cached Supabase client."""
    global _client
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") if use_service_role
        else os.getenv("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
    if _client is None:
        _client = create_client(url, key)
    return _client


def query_users(limit: int = 100, offset: int = 0) -> list[dict]:
    """Query user profiles."""
    sb = get_supabase(use_service_role=True)
    return sb.table("profiles").select("*").range(offset, offset + limit - 1).execute().data


def get_subscription(user_id: str) -> Optional[dict]:
    """Get a user's current subscription."""
    sb = get_supabase(use_service_role=True)
    result = sb.table("subscriptions").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def count_active_subs() -> int:
    """Count active subscriptions."""
    sb = get_supabase(use_service_role=True)
    result = sb.table("subscriptions").select("id", count="exact").eq("status", "active").execute()
    return result.count or 0


def get_user_by_email(email: str) -> Optional[dict]:
    """Lookup user by email."""
    sb = get_supabase(use_service_role=True)
    result = sb.table("profiles").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None
