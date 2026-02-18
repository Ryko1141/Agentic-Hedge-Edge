"""
LinkedIn OAuth2 Flow
=====================
Opens browser for LinkedIn login, captures auth code,
exchanges for access token + refresh token, saves to .env.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import webbrowser
import sys
import os
import threading

CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', 'YOUR_LINKEDIN_CLIENT_ID')
CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET', 'YOUR_LINKEDIN_CLIENT_SECRET')
REDIRECT_URI = "http://localhost:8090/callback"
# Scopes: openid + profile + email + posting
SCOPES = "openid profile email w_member_social"

auth_code = None
server_ref = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>LinkedIn authorized! You can close this tab.</h1>")
        elif "error" in params:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            error = params.get("error", ["unknown"])[0]
            desc = params.get("error_description", [""])[0]
            self.wfile.write(f"<h1>Error: {error}</h1><p>{desc}</p>".encode())
        else:
            self.send_response(404)
            self.end_headers()

        # Shut down server after handling
        threading.Thread(target=lambda: server_ref.shutdown()).start()

    def log_message(self, format, *args):
        pass


def exchange_code(code):
    """Exchange auth code for access token using requests library."""
    import requests as req_lib
    # Use requests library — handles encoding of == in secret correctly
    resp = req_lib.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    print(f"  Token exchange status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  Response: {resp.text[:300]}")
        # Debug: show what was sent
        print(f"  DEBUG client_id: {CLIENT_ID}")
        print(f"  DEBUG client_secret: {CLIENT_SECRET}")
        print(f"  DEBUG redirect_uri: {REDIRECT_URI}")
    resp.raise_for_status()
    return resp.json()


def get_profile(access_token):
    """Fetch LinkedIn profile using the access token."""
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def save_to_env(access_token, refresh_token=None, expires_in=None):
    """Save tokens to .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "r") as f:
        content = f.read()

    # Add or update LINKEDIN_ACCESS_TOKEN
    if "LINKEDIN_ACCESS_TOKEN=" in content:
        lines = content.split("\n")
        lines = [l for l in lines if not l.startswith("LINKEDIN_ACCESS_TOKEN=")
                 and not l.startswith("LINKEDIN_REFRESH_TOKEN=")
                 and not l.startswith("LINKEDIN_TOKEN_EXPIRES_IN=")]
        content = "\n".join(lines)

    tokens = f"\nLINKEDIN_ACCESS_TOKEN={access_token}"
    if refresh_token:
        tokens += f"\nLINKEDIN_REFRESH_TOKEN={refresh_token}"
    if expires_in:
        tokens += f"\nLINKEDIN_TOKEN_EXPIRES_IN={expires_in}"

    with open(env_path, "w") as f:
        f.write(content.rstrip() + tokens + "\n")


if __name__ == "__main__":

    print("=" * 50)
    print("LinkedIn OAuth2 Flow")
    print("=" * 50)

    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(SCOPES)}"
    )

    print(f"\nOpening browser...")
    print(f"Waiting for authorization...\n")
    webbrowser.open(auth_url)

    server_ref = HTTPServer(("127.0.0.1", 8090), CallbackHandler)
    server_ref.serve_forever()

    if not auth_code:
        print("ERROR: No auth code received.")
        sys.exit(1)

    print(f"Auth code received! Exchanging for tokens...")

    try:
        tokens = exchange_code(auth_code)
    except Exception as e:
        print(f"ERROR exchanging code: {e}")
        if hasattr(e, "read"):
            print(e.read().decode())
        sys.exit(1)

    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in", "")
    scope = tokens.get("scope", "")

    print(f"  Access Token:  {access_token[:20]}...")
    print(f"  Refresh Token: {refresh_token[:20] + '...' if refresh_token else '(none)'}")
    print(f"  Expires In:    {expires_in}s")
    print(f"  Scope:         {scope}")

    # Save tokens
    save_to_env(access_token, refresh_token, expires_in)
    print(f"\nTokens saved to .env!")

    # Fetch profile
    try:
        profile = get_profile(access_token)
        name = profile.get("name", "N/A")
        email = profile.get("email", "N/A")
        sub = profile.get("sub", "N/A")
        print(f"\n  Profile: {name}")
        print(f"  Email:   {email}")
        print(f"  Sub:     {sub}")
        print(f"\n  RESULT: PASS ✅")
    except Exception as e:
        print(f"\n  Could not fetch profile: {e}")
        print(f"  (Token saved — PASS ✅)")
