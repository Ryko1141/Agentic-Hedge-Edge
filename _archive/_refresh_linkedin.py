"""
LinkedIn Token Refresh
=======================
Refreshes the LinkedIn access token using the refresh token.
Run this periodically (e.g., every 50 days) to keep the token alive.
Can be called by any agent or scheduled task.
"""
import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")

def load_env():
    """Load .env into os.environ and return as dict."""
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
                    os.environ[k.strip()] = v.strip()
    return env

def update_env(key, value):
    """Update a single key in .env (or add it)."""
    with open(ENV_PATH, "r") as f:
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

    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)

def refresh_linkedin_token():
    env = load_env()
    client_id = env.get("LINKEDIN_CLIENT_ID", "")
    client_secret = env.get("LINKEDIN_CLIENT_SECRET", "")
    refresh_token = env.get("LINKEDIN_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        print("ERROR: Missing LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, or LINKEDIN_REFRESH_TOKEN in .env")
        return False

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Refreshing LinkedIn token...")

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8080/callback",
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
        error_body = ""
        if hasattr(e, "read"):
            error_body = e.read().decode()
        print(f"ERROR: {e}")
        if error_body:
            print(f"  Response: {error_body[:300]}")
        return False

    new_access = tokens.get("access_token", "")
    new_refresh = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in", "")

    if not new_access:
        print(f"ERROR: No access_token in response: {tokens}")
        return False

    # Update .env
    update_env("LINKEDIN_ACCESS_TOKEN", new_access)
    if new_refresh:
        update_env("LINKEDIN_REFRESH_TOKEN", new_refresh)
    if expires_in:
        update_env("LINKEDIN_TOKEN_EXPIRES_IN", str(expires_in))

    print(f"  New access token:  {new_access[:20]}...")
    if new_refresh:
        print(f"  New refresh token: {new_refresh[:20]}...")
    print(f"  Expires in:        {expires_in}s (~{int(expires_in)//86400} days)")
    print(f"  Saved to .env ✅")

    # Verify the new token works
    try:
        req2 = urllib.request.Request(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            profile = json.loads(resp2.read())
            print(f"  Verified: {profile.get('name', 'OK')}")
    except Exception as e:
        print(f"  Warning: Could not verify token: {e}")

    return True

if __name__ == "__main__":
    success = refresh_linkedin_token()
    sys.exit(0 if success else 1)
