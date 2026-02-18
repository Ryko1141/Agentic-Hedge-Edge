"""
Hedge Edge — LinkedIn Token Auto-Refresh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Refreshes the LinkedIn OAuth2 access token using the refresh token.
Updates .env in-place. Run on a schedule (every 50 days) or on-demand.

Access token lifetime:  ~60 days (5,183,999 seconds)
Refresh token lifetime: ~365 days

Usage:
    python -m shared.linkedin_refresh          # Refresh + verify
    python -m shared.linkedin_refresh --check  # Check expiry only

Called by:
    shared/scheduled_tasks.py (automated)
    Any agent needing LinkedIn access (pre-flight check)
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

_WS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_WS_ROOT, ".env")


def _load_env() -> dict[str, str]:
    """Load .env into dict (does not pollute os.environ)."""
    env = {}
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def _update_env(key: str, value: str) -> None:
    """Update or add a key in .env."""
    with open(_ENV_PATH, "r") as f:
        lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(_ENV_PATH, "w") as f:
        f.writelines(new_lines)


def check_expiry() -> dict:
    """
    Check how much time is left on the access token.
    Returns dict with days_left, expires_in, needs_refresh.
    """
    env = _load_env()
    expires_in = int(env.get("LINKEDIN_TOKEN_EXPIRES_IN", "0"))
    days = expires_in // 86400
    return {
        "expires_in_seconds": expires_in,
        "days_left": days,
        "needs_refresh": days < 14,  # Refresh if <14 days left
        "token_prefix": env.get("LINKEDIN_ACCESS_TOKEN", "")[:12] + "...",
    }


def refresh() -> dict:
    """
    Refresh the LinkedIn access token. Returns new token info dict.
    Raises RuntimeError on failure.
    """
    env = _load_env()
    client_id = env.get("LINKEDIN_CLIENT_ID", "")
    client_secret = env.get("LINKEDIN_CLIENT_SECRET", "")
    refresh_token = env.get("LINKEDIN_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "Missing LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, "
            "or LINKEDIN_REFRESH_TOKEN in .env"
        )

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] Refreshing LinkedIn token...")

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()

    req = urllib.request.Request(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tokens = json.loads(resp.read())
    except Exception as e:
        body = ""
        if hasattr(e, "read"):
            body = e.read().decode()[:300]
        raise RuntimeError(f"Token exchange failed: {e}\n{body}") from e

    new_access = tokens.get("access_token", "")
    new_refresh = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in", 0)

    if not new_access:
        raise RuntimeError(f"No access_token in response: {tokens}")

    # Save to .env
    _update_env("LINKEDIN_ACCESS_TOKEN", new_access)
    if new_refresh:
        _update_env("LINKEDIN_REFRESH_TOKEN", new_refresh)
    if expires_in:
        _update_env("LINKEDIN_TOKEN_EXPIRES_IN", str(expires_in))

    days = int(expires_in) // 86400
    print(f"  Access token:  {new_access[:20]}...")
    print(f"  Refresh token: {new_refresh[:20]}..." if new_refresh else "  Refresh token: unchanged")
    print(f"  Expires in:    {expires_in}s (~{days} days)")
    print(f"  Saved to .env")

    # Verify
    try:
        req2 = urllib.request.Request(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            profile = json.loads(resp2.read())
            name = profile.get("name", "verified")
            print(f"  Verified: {name}")
    except Exception as e:
        print(f"  Warning: verification failed: {e}")

    return {
        "access_token": new_access[:20] + "...",
        "refresh_token": (new_refresh[:20] + "...") if new_refresh else None,
        "expires_in": expires_in,
        "days_left": days,
    }


def refresh_if_needed(threshold_days: int = 14) -> dict | None:
    """Refresh only if the token expires within threshold_days."""
    info = check_expiry()
    if info["days_left"] < threshold_days:
        print(f"Token expires in {info['days_left']} days — refreshing...")
        return refresh()
    print(f"Token OK — {info['days_left']} days remaining, no refresh needed.")
    return None


if __name__ == "__main__":
    if "--check" in sys.argv:
        info = check_expiry()
        print(f"LinkedIn token: {info['token_prefix']}")
        print(f"  Days left:     {info['days_left']}")
        print(f"  Needs refresh: {info['needs_refresh']}")
    else:
        result = refresh()
        print(f"\nDone — new token valid for ~{result['days_left']} days.")
