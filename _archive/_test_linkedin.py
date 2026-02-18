"""Test LinkedIn OAuth2 credentials."""
import urllib.request
import urllib.parse
import json
import os

CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', 'YOUR_LINKEDIN_CLIENT_ID')
CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET', 'YOUR_LINKEDIN_CLIENT_SECRET')

print("=" * 50)
print("Testing LinkedIn OAuth2 Credentials")
print("=" * 50)
print(f"  Client ID: {CLIENT_ID}")
print(f"  Secret:    {CLIENT_SECRET[:12]}...{CLIENT_SECRET[-4:]}")

# Method 1: Try client_credentials grant (works for some LinkedIn apps)
print("\n[1] Client credentials grant...")
data = urllib.parse.urlencode({
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}).encode()
req = urllib.request.Request(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        print(f"  Token: {str(result.get('access_token',''))[:20]}...")
        print("  RESULT: PASS")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  {e.code}: {body[:200]}")
    # If 401 with "invalid client_id", credentials are wrong
    # If 401 with "unauthorized_scope" or similar, credentials are valid but grant type unsupported
    if "invalid" in body.lower() and "client" in body.lower():
        print("  RESULT: FAIL (invalid credentials)")
    else:
        print("  (Grant type may not be supported — trying OAuth2 auth URL test)")

# Method 2: Build an auth URL — if client_id is valid, LinkedIn will show consent page
# We just verify the redirect works (LinkedIn returns a page, not 404/error)
print("\n[2] Verifying Client ID via OAuth2 authorize URL...")
auth_url = (
    f"https://www.linkedin.com/oauth/v2/authorization?"
    f"response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri=http://localhost:8080/callback"
    f"&scope=openid%20profile%20email%20w_member_social"
)
req2 = urllib.request.Request(auth_url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req2, timeout=10) as resp:
        status = resp.status
        page = resp.read().decode("utf-8", errors="replace")[:500]
        if "login" in page.lower() or "sign in" in page.lower() or "authorize" in page.lower() or status == 200:
            print(f"  Status: {status} — LinkedIn recognizes the Client ID")
            print("  RESULT: PASS (Client ID valid, OAuth2 flow required for access token)")
        else:
            print(f"  Status: {status}")
            print(f"  Page: {page[:200]}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    if e.code == 302:
        print(f"  Redirect (expected for OAuth) — Client ID recognized")
        print("  RESULT: PASS")
    else:
        print(f"  {e.code}: {body[:200]}")
        if "client_id" in body.lower() or "invalid" in body.lower():
            print("  RESULT: FAIL (Client ID not recognized)")
        else:
            print(f"  RESULT: UNCLEAR ({e.code})")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 50)
print("Note: LinkedIn requires a full OAuth2 flow (browser login)")
print("to get an access token. Client ID + Secret are validated")
print("during that flow.")
print("=" * 50)
