"""
Hedge Edge — Cloudflare Hardening Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Audits and hardens the hedgedge.info Cloudflare zone.
Checks what's accessible via API and provides a manual checklist for the rest.

Usage:
    python -m shared.cloudflare_harden          # audit + checklist
    python -m shared.cloudflare_harden --apply  # apply what we can via API
"""

import os
import sys
import json

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ws_root)

from shared.cloudflare_client import (
    ZONE_ID,
    verify_token,
    list_zones,
    list_dns_records,
    get_zone_analytics,
    _get,
    _patch,
)


# ──────────────────────────────────────────────
# Security Checklist (for settings needing dashboard access)
# ──────────────────────────────────────────────
SECURITY_CHECKLIST = [
    ("SSL/TLS Mode",            "Full (Strict)",       "SSL/TLS → Overview → Full (strict)"),
    ("Always Use HTTPS",        "On",                  "SSL/TLS → Edge Certificates → Always Use HTTPS"),
    ("Minimum TLS Version",     "1.2",                 "SSL/TLS → Edge Certificates → Minimum TLS Version"),
    ("HSTS",                    "Enabled (6 months)",  "SSL/TLS → Edge Certificates → HTTP Strict Transport Security"),
    ("Automatic HTTPS Rewrites","On",                  "SSL/TLS → Edge Certificates → Automatic HTTPS Rewrites"),
    ("Opportunistic Encryption","On",                  "SSL/TLS → Edge Certificates → Opportunistic Encryption"),
    ("Browser Integrity Check", "On",                  "Security → Settings → Browser Integrity Check"),
    ("Security Level",          "Medium",              "Security → Settings → Security Level"),
    ("Bot Fight Mode",          "On",                  "Security → Bots → Bot Fight Mode"),
    ("Brotli Compression",     "On",                   "Speed → Optimization → Content Optimization → Brotli"),
    ("Auto Minify",            "HTML+CSS+JS",          "Speed → Optimization → Content Optimization → Auto Minify"),
    ("HTTP/2",                 "On",                   "Speed → Optimization → Protocol Optimization → HTTP/2"),
    ("Email Obfuscation",     "On",                    "Scrape Shield → Email Address Obfuscation"),
    ("Server-side Excludes",  "On",                    "Scrape Shield → Server-side Excludes"),
]


def audit_api_accessible(zone_id: str = None) -> dict:
    """
    Check what we CAN access with the current API token.
    Returns a dict of accessible services and their status.
    """
    zone_id = zone_id or ZONE_ID
    results = {}

    # Token validity
    try:
        token_info = verify_token()
        results["token"] = {"status": "active", "id": token_info.get("id", "?")}
    except Exception as e:
        results["token"] = {"status": "error", "error": str(e)[:100]}

    # Zone info
    try:
        zones = list_zones()
        our_zone = next((z for z in zones if z["id"] == zone_id), None)
        if our_zone:
            results["zone"] = {
                "name": our_zone["name"],
                "status": our_zone["status"],
                "plan": our_zone.get("plan", {}).get("name", "unknown"),
                "name_servers": our_zone.get("name_servers", []),
            }
        else:
            results["zone"] = {"status": "not_found"}
    except Exception as e:
        results["zone"] = {"status": "error", "error": str(e)[:100]}

    # DNS records
    try:
        records = list_dns_records(zone_id)
        results["dns"] = {
            "total": len(records),
            "types": {},
        }
        for r in records:
            rtype = r["type"]
            results["dns"]["types"][rtype] = results["dns"]["types"].get(rtype, 0) + 1
    except Exception as e:
        results["dns"] = {"status": "error", "error": str(e)[:100]}

    # Zone settings (might be 403)
    try:
        settings = _get(f"/zones/{zone_id}/settings")["result"]
        settings_map = {s["id"]: s.get("value") for s in settings}
        results["settings_access"] = True
        results["settings"] = settings_map
    except Exception:
        results["settings_access"] = False

    # Analytics
    try:
        analytics = get_zone_analytics(zone_id, since="-1440")
        totals = analytics.get("totals", {})
        req = totals.get("requests", {})
        results["analytics_24h"] = {
            "total_requests": req.get("all", 0),
            "cached": req.get("cached", 0),
            "uncached": req.get("uncached", 0),
            "threats": totals.get("threats", {}).get("all", 0),
        }
    except Exception as e:
        results["analytics_24h"] = {"status": "error", "error": str(e)[:100]}

    return results


def harden_with_api(zone_id: str = None, dry_run: bool = True) -> list[dict]:
    """
    If we have settings access, apply hardening via API.
    Returns list of actions taken.
    """
    zone_id = zone_id or ZONE_ID
    actions = []

    # Check if we have settings access
    try:
        settings = _get(f"/zones/{zone_id}/settings")["result"]
        settings_map = {s["id"]: s.get("value") for s in settings}
    except Exception:
        return [{"setting": "all", "action": "skipped", "reason": "No Zone Settings API access (403). Use Cloudflare dashboard."}]

    desired = {
        "ssl":                      "strict",
        "always_use_https":         "on",
        "security_level":           "low",      # Low — minimal friction for landing page visitors
        "browser_check":            "on",
        "min_tls_version":          "1.2",
        "brotli":                   "on",
        "http2":                    "on",
        "opportunistic_encryption": "on",
        "automatic_https_rewrites": "on",
        "minify":                   {"css": "on", "html": "on", "js": "on"},
    }

    for setting_id, desired_val in desired.items():
        current = settings_map.get(setting_id)
        if isinstance(desired_val, dict):
            match = all(current.get(k) == v for k, v in desired_val.items()) if isinstance(current, dict) else False
        else:
            match = str(current) == str(desired_val)

        if match:
            actions.append({"setting": setting_id, "current": current, "status": "ok"})
            continue

        if dry_run:
            actions.append({"setting": setting_id, "current": current, "desired": desired_val, "action": "would_fix"})
        else:
            try:
                _patch(f"/zones/{zone_id}/settings/{setting_id}", {"value": desired_val})
                actions.append({"setting": setting_id, "current": current, "desired": desired_val, "action": "fixed"})
            except Exception as e:
                actions.append({"setting": setting_id, "action": "failed", "error": str(e)[:100]})

    return actions


def print_report(zone_id: str = None, apply: bool = False):
    """Full audit + checklist report."""
    zone_id = zone_id or ZONE_ID

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   Cloudflare Security Hardening — hedgedge.info      ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # 1. API-accessible audit
    print("━━━ API Token & Zone Status ━━━")
    info = audit_api_accessible(zone_id)

    token = info.get("token", {})
    print(f"  {'✅' if token.get('status')=='active' else '❌'}  Token: {token.get('status', 'unknown')}")

    zone = info.get("zone", {})
    print(f"  {'✅' if zone.get('status')=='active' else '⚠️'}  Zone: {zone.get('name', '?')} ({zone.get('status', '?')}) — Plan: {zone.get('plan', '?')}")

    dns = info.get("dns", {})
    if "total" in dns:
        types_str = ", ".join(f"{t}:{c}" for t, c in sorted(dns["types"].items()))
        print(f"  ✅  DNS Records: {dns['total']} total ({types_str})")

    analytics = info.get("analytics_24h", {})
    if "total_requests" in analytics:
        print(f"  📊  Last 24h: {analytics['total_requests']} requests, {analytics['cached']} cached, {analytics['threats']} threats")

    settings_access = info.get("settings_access", False)
    print(f"  {'✅' if settings_access else '🔒'}  Zone Settings API: {'accessible' if settings_access else 'not accessible (need Zone Settings permission)'}")

    # 2. Apply hardening if we have settings access
    if settings_access:
        print("\n━━━ Security Settings ━━━")
        actions = harden_with_api(zone_id, dry_run=not apply)
        for a in actions:
            s = a["setting"]
            if a.get("status") == "ok":
                print(f"  ✅  {s}: {a['current']}")
            elif a.get("action") == "would_fix":
                print(f"  ⚠️   {s}: {a['current']} → {a['desired']}  (run with --apply)")
            elif a.get("action") == "fixed":
                print(f"  🔧  {s}: APPLIED → {a['desired']}")
            elif a.get("action") == "failed":
                print(f"  ❌  {s}: {a.get('error', '')}")

    # 3. Manual checklist (always shown)
    print("\n━━━ Security Checklist (Cloudflare Dashboard) ━━━")
    print("  Recommended settings to verify in the Cloudflare dashboard:")
    print(f"  Dashboard URL: https://dash.cloudflare.com/{zone_id}\n")

    for setting, recommended, location in SECURITY_CHECKLIST:
        if settings_access and setting.lower().replace(" ", "_").replace("/", "") in info.get("settings", {}):
            continue  # Already checked via API
        print(f"  ☐  {setting:30s} → {recommended:20s}  ({location})")

    print("\n  💡 To enable API-based hardening, update the Cloudflare API token")
    print("     permissions to include 'Zone → Zone Settings → Edit'\n")


def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Cloudflare Security Hardening")
    parser.add_argument("--apply", action="store_true", help="Apply fixes via API (if accessible)")
    parser.add_argument("--json", action="store_true", help="Output audit as JSON")
    args = parser.parse_args()

    if args.json:
        info = audit_api_accessible()
        print(json.dumps(info, indent=2, default=str))
    else:
        print_report(apply=args.apply)


if __name__ == "__main__":
    _cli()
