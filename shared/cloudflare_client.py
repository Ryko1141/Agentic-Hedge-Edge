"""
Hedge Edge — Cloudflare Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REST client for Cloudflare DNS, CDN, caching, security & analytics.

Capabilities:
    • List / manage zones (domains)
    • CRUD DNS records (A, AAAA, CNAME, MX, TXT, etc.)
    • Purge cache (entire zone or individual URLs)
    • Firewall / WAF rule management
    • Zone analytics (requests, bandwidth, threats)
    • Page rules management
    • SSL/TLS settings
    • Worker routes (if Workers enabled)

Auth: Account-scoped bearer token (CLOUDFLARE_API_TOKEN).
      Requires CLOUDFLARE_ACCOUNT_ID for zone listing.
      Optional CLOUDFLARE_ZONE_ID for default zone (hedgedge.info).
Docs: https://developers.cloudflare.com/api

Usage:
    from shared.cloudflare_client import (
        list_zones, list_dns_records, create_dns_record,
        purge_cache, get_zone_analytics,
    )
"""

import os, requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────
API_TOKEN  = os.getenv("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
ZONE_ID    = os.getenv("CLOUDFLARE_ZONE_ID", "")
BASE_URL   = "https://api.cloudflare.com/client/v4"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type":  "application/json",
}


def _get(path: str, params: dict | None = None) -> dict:
    """GET request helper. Returns full API response body."""
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        errors = body.get("errors", [])
        raise RuntimeError(f"Cloudflare API error: {errors}")
    return body


def _post(path: str, payload: dict | None = None) -> dict:
    """POST request helper."""
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=payload or {}, timeout=15)
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"Cloudflare API error: {body.get('errors', [])}")
    return body


def _put(path: str, payload: dict | None = None) -> dict:
    """PUT request helper."""
    r = requests.put(f"{BASE_URL}{path}", headers=HEADERS, json=payload or {}, timeout=15)
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"Cloudflare API error: {body.get('errors', [])}")
    return body


def _patch(path: str, payload: dict | None = None) -> dict:
    """PATCH request helper."""
    r = requests.patch(f"{BASE_URL}{path}", headers=HEADERS, json=payload or {}, timeout=15)
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"Cloudflare API error: {body.get('errors', [])}")
    return body


def _delete(path: str, payload: dict | None = None) -> dict:
    """DELETE request helper."""
    r = requests.delete(f"{BASE_URL}{path}", headers=HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"Cloudflare API error: {body.get('errors', [])}")
    return body


# ── Token / User ──────────────────────────────────────

def verify_token() -> dict:
    """
    Verify the API token is valid and active.
    Uses account-scoped endpoint for account-level tokens.
    """
    if ACCOUNT_ID:
        return _get(f"/accounts/{ACCOUNT_ID}/tokens/verify")["result"]
    return _get("/user/tokens/verify")["result"]


def get_account_id() -> str:
    """Return the configured Cloudflare account ID."""
    return ACCOUNT_ID


def get_default_zone_id() -> str:
    """Return the configured default zone ID (hedgedge.info)."""
    return ZONE_ID


# ── Zones (Domains) ──────────────────────────────────

def list_zones(
    name: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> list[dict]:
    """
    List all zones (domains) on the account.

    Args:
        name:     Filter by domain name.
        status:   Filter by status (active, pending, initializing, moved, deleted).
        page:     Pagination page number.
        per_page: Results per page (max 50).

    Returns:
        List of zone dicts with: id, name, status, plan, name_servers, etc.
    """
    params: dict = {"page": page, "per_page": per_page}
    if ACCOUNT_ID:
        params["account.id"] = ACCOUNT_ID
    if name:
        params["name"] = name
    if status:
        params["status"] = status
    return _get("/zones", params)["result"]


def get_zone(zone_id: str) -> dict:
    """Get details for a specific zone."""
    return _get(f"/zones/{zone_id}")["result"]


def get_zone_by_name(domain: str) -> dict | None:
    """Look up a zone by domain name. Returns zone dict or None."""
    zones = list_zones(name=domain)
    return zones[0] if zones else None


# ── DNS Records ───────────────────────────────────────

def list_dns_records(
    zone_id: str,
    record_type: str | None = None,
    name: str | None = None,
    page: int = 1,
    per_page: int = 100,
) -> list[dict]:
    """
    List DNS records for a zone.

    Args:
        zone_id:     The zone ID.
        record_type: Filter by type (A, AAAA, CNAME, MX, TXT, etc.).
        name:        Filter by record name (e.g. "sub.example.com").

    Returns:
        List of DNS record dicts.
    """
    params: dict = {"page": page, "per_page": per_page}
    if record_type:
        params["type"] = record_type
    if name:
        params["name"] = name
    return _get(f"/zones/{zone_id}/dns_records", params)["result"]


def create_dns_record(
    zone_id: str,
    record_type: str,
    name: str,
    content: str,
    *,
    ttl: int = 1,
    proxied: bool = False,
    priority: int | None = None,
    comment: str | None = None,
) -> dict:
    """
    Create a DNS record.

    Args:
        zone_id:     The zone ID.
        record_type: Record type (A, AAAA, CNAME, MX, TXT, SRV, etc.).
        name:        Record name (e.g. "@" for root, "sub" for subdomain).
        content:     Record value (IP address, hostname, text, etc.).
        ttl:         TTL in seconds. 1 = automatic.
        proxied:     Whether to proxy through Cloudflare (orange cloud).
        priority:    Priority (required for MX records).
        comment:     Optional comment for the record.

    Returns:
        Created DNS record dict.
    """
    payload: dict = {
        "type":    record_type,
        "name":    name,
        "content": content,
        "ttl":     ttl,
        "proxied": proxied,
    }
    if priority is not None:
        payload["priority"] = priority
    if comment:
        payload["comment"] = comment

    return _post(f"/zones/{zone_id}/dns_records", payload)["result"]


def update_dns_record(
    zone_id: str,
    record_id: str,
    **fields,
) -> dict:
    """
    Update a DNS record.

    Args:
        zone_id:   The zone ID.
        record_id: The DNS record ID.
        **fields:  Fields to update (type, name, content, ttl, proxied, etc.).

    Returns:
        Updated DNS record dict.
    """
    return _put(f"/zones/{zone_id}/dns_records/{record_id}", fields)["result"]


def delete_dns_record(zone_id: str, record_id: str) -> dict:
    """Delete a DNS record."""
    return _delete(f"/zones/{zone_id}/dns_records/{record_id}")["result"]


# ── Cache ─────────────────────────────────────────────

def purge_cache(zone_id: str, purge_everything: bool = True) -> dict:
    """
    Purge the entire zone cache.

    Args:
        zone_id:          The zone ID.
        purge_everything: If True, purges all cached content.

    Returns:
        Purge result.
    """
    return _post(f"/zones/{zone_id}/purge_cache", {
        "purge_everything": purge_everything,
    })["result"]


def purge_cache_urls(zone_id: str, urls: list[str]) -> dict:
    """
    Purge specific URLs from cache.

    Args:
        zone_id: The zone ID.
        urls:    List of URLs to purge (max 30 per call).

    Returns:
        Purge result.
    """
    return _post(f"/zones/{zone_id}/purge_cache", {"files": urls[:30]})["result"]


# ── SSL/TLS ──────────────────────────────────────────

def get_ssl_setting(zone_id: str) -> dict:
    """Get the SSL/TLS encryption mode for a zone."""
    return _get(f"/zones/{zone_id}/settings/ssl")["result"]


def set_ssl_setting(zone_id: str, value: str) -> dict:
    """
    Set SSL/TLS mode.

    Args:
        zone_id: The zone ID.
        value:   Mode — "off", "flexible", "full", "strict".
    """
    return _patch(f"/zones/{zone_id}/settings/ssl", {"value": value})["result"]


# ── Security / Firewall ──────────────────────────────

def get_security_level(zone_id: str) -> dict:
    """Get the security level setting for a zone."""
    return _get(f"/zones/{zone_id}/settings/security_level")["result"]


def set_security_level(zone_id: str, value: str) -> dict:
    """
    Set zone security level.

    Args:
        value: "off", "essentially_off", "low", "medium", "high", "under_attack".
    """
    return _patch(f"/zones/{zone_id}/settings/security_level", {"value": value})["result"]


# ── Page Rules ────────────────────────────────────────

def list_page_rules(zone_id: str) -> list[dict]:
    """List all page rules for a zone."""
    return _get(f"/zones/{zone_id}/pagerules")["result"]


def create_page_rule(
    zone_id: str,
    targets: list[dict],
    actions: list[dict],
    status: str = "active",
    priority: int = 1,
) -> dict:
    """
    Create a page rule.

    Args:
        zone_id:  The zone ID.
        targets:  URL match patterns, e.g. [{"target":"url","constraint":{"operator":"matches","value":"*example.com/*"}}]
        actions:  Actions to take, e.g. [{"id":"forwarding_url","value":{"url":"https://...", "status_code":301}}]
        status:   "active" or "disabled".
        priority: Rule priority (1 = highest).
    """
    return _post(f"/zones/{zone_id}/pagerules", {
        "targets":  targets,
        "actions":  actions,
        "status":   status,
        "priority": priority,
    })["result"]


# ── Analytics ─────────────────────────────────────────

def get_zone_analytics(
    zone_id: str,
    since: str = "-1440",
    until: str = "0",
) -> dict:
    """
    Get zone analytics (requests, bandwidth, threats, pageviews).

    Args:
        zone_id: The zone ID.
        since:   Start time — negative minutes from now (e.g. "-1440" = last 24h)
                 or ISO 8601 datetime.
        until:   End time — "0" for now, or ISO 8601 datetime.

    Returns:
        Analytics dashboard data with totals and time series.
    """
    return _get(f"/zones/{zone_id}/analytics/dashboard", {
        "since": since,
        "until": until,
    })["result"]


# ── Zone Settings ─────────────────────────────────────

def get_zone_settings(zone_id: str) -> list[dict]:
    """Get all settings for a zone (minification, caching, security, etc.)."""
    return _get(f"/zones/{zone_id}/settings")["result"]


def update_zone_setting(zone_id: str, setting_id: str, value) -> dict:
    """
    Update a single zone setting.

    Args:
        zone_id:    The zone ID.
        setting_id: Setting name (e.g. "always_use_https", "minify", "cache_level").
        value:      New value for the setting.
    """
    return _patch(f"/zones/{zone_id}/settings/{setting_id}", {"value": value})["result"]


# ── Convenience Helpers ───────────────────────────────

def add_a_record(zone_id: str, name: str, ip: str, proxied: bool = True) -> dict:
    """Shortcut: create an A record pointing to an IP."""
    return create_dns_record(zone_id, "A", name, ip, proxied=proxied)


def add_cname_record(zone_id: str, name: str, target: str, proxied: bool = True) -> dict:
    """Shortcut: create a CNAME record."""
    return create_dns_record(zone_id, "CNAME", name, target, proxied=proxied)


def add_txt_record(zone_id: str, name: str, content: str) -> dict:
    """Shortcut: create a TXT record (never proxied)."""
    return create_dns_record(zone_id, "TXT", name, content, proxied=False)


def add_mx_record(zone_id: str, name: str, mail_server: str, priority: int = 10) -> dict:
    """Shortcut: create an MX record."""
    return create_dns_record(zone_id, "MX", name, mail_server, priority=priority)


def get_status_summary() -> dict:
    """
    Quick overview: all zones with their status and plan.
    Useful for dashboards and health checks.
    """
    zones = list_zones()
    return {
        "total_zones": len(zones),
        "zones": [
            {
                "name":   z["name"],
                "id":     z["id"],
                "status": z["status"],
                "plan":   z.get("plan", {}).get("name", "unknown"),
                "ns":     z.get("name_servers", []),
            }
            for z in zones
        ],
    }
