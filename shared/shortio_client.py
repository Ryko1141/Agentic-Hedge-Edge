"""
Hedge Edge — Short.io Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REST client for Short.io link shortening and analytics.

Capabilities:
    • Create, update, delete short links
    • List links by domain, lookup by original URL
    • Archive / unarchive links
    • Link click statistics (by period)
    • Domain listing and stats
    • QR code generation
    • Bulk link creation (up to 1000)
    • UTM parameter management

Auth: Secret API key (SHORTIO_API_KEY).
Docs: https://developers.short.io/reference

NOTE: A domain must be configured in the Short.io dashboard before
      links can be created.  Use list_domains() to check.

Usage:
    from shared.shortio_client import (
        list_domains, create_link, list_links,
        get_link_stats, delete_link,
    )
"""

import os, requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────
API_KEY       = os.getenv("SHORTIO_API_KEY", "")
BASE_URL      = "https://api.short.io"
STATS_URL     = "https://api-v2.short.io"
SHORTIO_DOMAIN = os.getenv("SHORTIO_DOMAIN", "")   # Set after adding a domain

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type":  "application/json",
    "Accept":        "application/json",
}


def _get(url: str, params: dict | None = None) -> dict | list:
    """GET request helper."""
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(url: str, payload: dict | None = None) -> dict:
    """POST request helper."""
    r = requests.post(url, headers=HEADERS, json=payload or {}, timeout=15)
    r.raise_for_status()
    return r.json()


def _delete(url: str) -> bool:
    """DELETE request helper. Returns True on success."""
    r = requests.delete(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return True


# ── Domains ───────────────────────────────────────────

def list_domains() -> list[dict]:
    """
    List all domains on the account.

    Returns list of dicts with: id, hostname, state, linkType, etc.
    """
    return _get(f"{BASE_URL}/api/domains")


def _default_domain() -> str:
    """Return SHORTIO_DOMAIN env var, or first domain from account."""
    if SHORTIO_DOMAIN:
        return SHORTIO_DOMAIN
    domains = list_domains()
    if not domains:
        raise RuntimeError(
            "No domains configured. Add a domain at https://app.short.io "
            "or set SHORTIO_DOMAIN in .env"
        )
    return domains[0]["hostname"]


# ── Link CRUD ─────────────────────────────────────────

def create_link(
    original_url: str,
    *,
    domain: str | None = None,
    path: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
    ttl: str | None = None,
    expires_at: str | None = None,
    expired_url: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_term: str | None = None,
    utm_content: str | None = None,
    allow_duplicates: bool = False,
    folder_id: str | None = None,
    cloaking: bool = False,
    redirect_type: int | None = None,
) -> dict:
    """
    Create a shortened link.

    Args:
        original_url: The long URL to shorten (required).
        domain:       Short domain hostname. Defaults to SHORTIO_DOMAIN or first domain.
        path:         Custom slug (e.g. "my-link"). Auto-generated if omitted.
        title:        Link title for display / SEO.
        tags:         List of string tags.
        ttl:          Time-to-live (ISO string or ms).
        expires_at:   Expiration date (ISO string or ms).
        expired_url:  Redirect URL after expiration.
        utm_*:        UTM tracking parameters appended to destination.
        allow_duplicates: Allow multiple short links to same URL.
        folder_id:    Folder ID to organise link.
        cloaking:     Show short URL in browser bar (iframe).
        redirect_type: HTTP redirect code (301, 302, 307, 308).

    Returns:
        Full link object with shortURL, idString, path, etc.
    """
    payload: dict = {
        "domain":          domain or _default_domain(),
        "originalURL":     original_url,
        "allowDuplicates": allow_duplicates,
        "cloaking":        cloaking,
    }
    if path is not None:
        payload["path"] = path
    if title is not None:
        payload["title"] = title
    if tags:
        payload["tags"] = tags
    if ttl is not None:
        payload["ttl"] = ttl
    if expires_at is not None:
        payload["expiresAt"] = expires_at
    if expired_url is not None:
        payload["expiredURL"] = expired_url
    if utm_source:
        payload["utmSource"] = utm_source
    if utm_medium:
        payload["utmMedium"] = utm_medium
    if utm_campaign:
        payload["utmCampaign"] = utm_campaign
    if utm_term:
        payload["utmTerm"] = utm_term
    if utm_content:
        payload["utmContent"] = utm_content
    if folder_id:
        payload["folderId"] = folder_id
    if redirect_type:
        payload["redirectType"] = redirect_type

    return _post(f"{BASE_URL}/links", payload)


def create_links_bulk(
    links: list[dict],
    domain: str | None = None,
) -> dict:
    """
    Create up to 1000 links in one call.

    Args:
        links:  List of dicts, each with at least {"originalURL": "..."}.
                Optional keys: path, title, tags, utm*, etc.
        domain: Domain hostname (applied to all links).

    Returns:
        API response with created links.
    """
    d = domain or _default_domain()
    for link in links:
        link.setdefault("domain", d)
    return _post(f"{BASE_URL}/links/bulk", {"links": links})


def update_link(link_id: str, **updates) -> dict:
    """
    Update an existing short link.

    Args:
        link_id:  The link's idString.
        **updates: Any writable link fields (originalURL, path, title,
                   tags, utm*, expiresAt, cloaking, etc.).

    Returns:
        Updated link object.
    """
    return _post(f"{BASE_URL}/links/{link_id}", updates)


def get_link(link_id: str) -> dict:
    """Get full link info by link ID (idString)."""
    return _get(f"{BASE_URL}/links/{link_id}")


def get_link_by_url(original_url: str, domain: str | None = None) -> dict:
    """Look up a short link by its original (long) URL."""
    return _get(f"{BASE_URL}/links/by-original-url", {
        "domain":      domain or _default_domain(),
        "originalURL": original_url,
    })


def get_link_by_path(path: str, domain: str | None = None) -> dict:
    """Look up a short link by its slug/path."""
    return _get(f"{BASE_URL}/links/expand", {
        "domain": domain or _default_domain(),
        "path":   path,
    })


def delete_link(link_id: str) -> bool:
    """Delete a short link. Returns True on success."""
    return _delete(f"{BASE_URL}/links/{link_id}")


def delete_links_bulk(link_ids: list[str]) -> bool:
    """Delete multiple links by their idStrings."""
    r = requests.delete(
        f"{BASE_URL}/links/delete-bulk",
        headers=HEADERS,
        json={"link_ids": link_ids},
        timeout=15,
    )
    r.raise_for_status()
    return True


# ── Archive / Unarchive ──────────────────────────────

def archive_link(link_id: str) -> dict:
    """Archive a short link (hides from default list)."""
    return _post(f"{BASE_URL}/links/archive", {"link_id": link_id})


def unarchive_link(link_id: str) -> dict:
    """Unarchive a short link."""
    return _post(f"{BASE_URL}/links/unarchive", {"link_id": link_id})


# ── Link List ─────────────────────────────────────────

def list_links(
    domain_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "createdAt",
    order_dir: str = "desc",
    tag: str | None = None,
) -> list[dict]:
    """
    List short links for a domain.

    Args:
        domain_id: Numeric domain ID. If None, uses first domain's ID.
        limit:     Max results (default 50, max 150).
        offset:    Pagination offset.
        order_by:  Sort field (createdAt, clicks).
        order_dir: Sort direction (asc/desc).
        tag:       Filter by tag.

    Returns:
        List of link objects.
    """
    if domain_id is None:
        domains = list_domains()
        if not domains:
            return []
        domain_id = domains[0]["id"]

    params: dict = {
        "domain_id": domain_id,
        "limit":     min(limit, 150),
        "offset":    offset,
        "orderBy":   order_by,
        "orderDir":  order_dir,
    }
    if tag:
        params["tag"] = tag

    resp = _get(f"{BASE_URL}/api/links", params)
    # API returns {"links": [...], "count": N} or just a list
    if isinstance(resp, dict):
        return resp.get("links", [])
    return resp


# ── Statistics ────────────────────────────────────────

def get_link_stats(
    link_id: str,
    period: str = "total",
    tz_offset: int = 0,
    start_date: int | None = None,
    end_date: int | None = None,
) -> dict:
    """
    Get click statistics for a link.

    Args:
        link_id:    The link's idString.
        period:     One of: today, yesterday, total, week, month,
                    lastmonth, last7, last30, custom.
        tz_offset:  Timezone offset in minutes.
        start_date: For custom period — start in epoch ms.
        end_date:   For custom period — end in epoch ms.

    Returns:
        Dict with totalClicks, humanClicks, browser[], country[],
        city[], os[], referer[], clickStatistics, etc.
    """
    params: dict = {"period": period, "tzOffset": str(tz_offset)}
    if period == "custom":
        if start_date:
            params["startDate"] = str(start_date)
        if end_date:
            params["endDate"] = str(end_date)

    return _get(f"{STATS_URL}/statistics/link/{link_id}", params)


def get_domain_stats(
    domain_id: int | None = None,
    period: str = "total",
    tz_offset: int = 0,
) -> dict:
    """
    Get click statistics for an entire domain.

    Args:
        domain_id: Numeric domain ID. If None, uses first domain.
        period:    One of: today, yesterday, total, week, month, etc.
        tz_offset: Timezone offset in minutes.

    Returns:
        Aggregated click stats for the domain.
    """
    if domain_id is None:
        domains = list_domains()
        if not domains:
            return {}
        domain_id = domains[0]["id"]

    return _get(
        f"{STATS_URL}/statistics/domain/{domain_id}",
        {"period": period, "tzOffset": str(tz_offset)},
    )


# ── QR Code ───────────────────────────────────────────

def generate_qr_code(link_id: str, **options) -> dict:
    """
    Generate a QR code for a short link.

    Args:
        link_id:  The link's idString.
        **options: Optional QR customization (size, format, etc.).

    Returns:
        QR code response (typically includes image URL or base64).
    """
    return _post(f"{BASE_URL}/links/qr/{link_id}", options or {})


# ── Clickstream (Premium) ────────────────────────────

def get_clickstream(
    link_id: str,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    Get raw click-level data for a link (premium feature).

    Returns individual click events with timestamp, IP, UA, referer, etc.
    """
    return _get(
        f"{STATS_URL}/statistics/link/{link_id}/clickstream",
        {"limit": limit, "offset": offset},
    )
