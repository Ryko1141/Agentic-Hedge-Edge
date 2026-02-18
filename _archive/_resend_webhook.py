"""
Resend Inbound Email Webhook Receiver
======================================
Listens for Resend 'email.received' webhook events.
Auto-fetches full email content via Resend API (webhooks only have metadata).
Used for LinkedIn app verification — captures verification emails.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime

# Load .env manually (no dependencies needed)
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
PORT = 5005


def fetch_email_content(email_id):
    """Fetch full email body from Resend Received Emails API."""
    if not RESEND_API_KEY:
        return "(No RESEND_API_KEY — cannot fetch body)"
    url = f"https://api.resend.com/emails/{email_id}/content"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {RESEND_API_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data
    except urllib.error.HTTPError as e:
        # Try the received-emails endpoint instead
        try:
            url2 = f"https://api.resend.com/received-emails/{email_id}"
            req2 = urllib.request.Request(url2, headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
            })
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                return json.loads(resp2.read())
        except Exception as e2:
            return f"(API error fetching body: {e} / {e2})"
    except Exception as e:
        return f"(Error: {e})"


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            print(f"\n[{datetime.now()}] Received non-JSON POST")
            print(body.decode("utf-8", errors="replace")[:500])
            return

        event_type = payload.get("type", "unknown")
        print(f"\n{'='*60}")
        print(f"  WEBHOOK EVENT: {event_type}")
        print(f"  Received: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        data = payload.get("data", {})

        # Always dump the FULL raw payload so we don't miss anything
        print(f"\n  --- FULL RAW WEBHOOK PAYLOAD ---")
        print(json.dumps(payload, indent=2)[:5000])

        if event_type == "email.received":
            email_id = data.get("email_id", "")
            print(f"\n  Email ID: {email_id}")
            print(f"  From:     {data.get('from', 'N/A')}")
            print(f"  To:       {data.get('to', 'N/A')}")
            print(f"  Subject:  {data.get('subject', 'N/A')}")
            print(f"  Date:     {data.get('created_at', 'N/A')}")

            # Print any body/text/html fields directly from webhook
            for field in ['text', 'html', 'body', 'content', 'message']:
                val = data.get(field)
                if val:
                    print(f"\n  --- {field.upper()} (from webhook) ---")
                    print(f"  {str(val)[:3000]}")

            # Try to fetch full email body via API (may fail on free plan)
            if email_id:
                print(f"\n  Attempting API fetch...")
                content = fetch_email_content(email_id)
                if isinstance(content, dict):
                    text = content.get("text", content.get("body", ""))
                    html = content.get("html", "")
                    if text:
                        print(f"\n  --- TEXT BODY (API) ---")
                        print(f"  {text[:3000]}")
                    if html:
                        print(f"\n  --- HTML BODY (API, first 2000 chars) ---")
                        print(f"  {html[:2000]}")
                else:
                    print(f"  {content}")
        else:
            print(f"  Full payload:")
            print(json.dumps(payload, indent=2)[:2000])

        print(f"{'='*60}\n")
        sys.stdout.flush()

    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Resend webhook receiver is running")

    def log_message(self, format, *args):
        """Suppress default HTTP logs for cleaner output"""
        pass

if __name__ == "__main__":
    print(f"{'='*60}")
    print(f"  Resend Inbound Email Webhook Receiver")
    print(f"  Listening on http://localhost:{PORT}")
    print(f"{'='*60}")
    print(f"  Next steps:")
    print(f"  1. Expose this with a public URL (ngrok, VS Code port forward)")
    print(f"  2. Add that URL to Resend Webhooks page")
    print(f"  3. Select event type: email.received")
    print(f"  4. Send your LinkedIn verification email")
    print(f"{'='*60}")
    print(f"\nWaiting for webhooks...\n")
    sys.stdout.flush()

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
