"""Google Sheets OAuth2 flow — gets a refresh token for Sheets API."""
import http.server
import urllib.request
import urllib.parse
import json
import ssl
import webbrowser

env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

CLIENT_ID = env['GOOGLE_SHEETS_CLIENT_ID']
CLIENT_SECRET = env['GOOGLE_SHEETS_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8080'
SCOPES = ' '.join([
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly',
])

auth_params = urllib.parse.urlencode({
    'client_id': CLIENT_ID,
    'redirect_uri': REDIRECT_URI,
    'response_type': 'code',
    'scope': SCOPES,
    'access_type': 'offline',
    'prompt': 'consent',
})
auth_url = f'https://accounts.google.com/o/oauth2/v2/auth?{auth_params}'

print('=' * 50)
print('Google Sheets OAuth2 Flow')
print('=' * 50)
print()
print('Opening browser...')

auth_code = None

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Success!</h1><p>Close this tab.</p></body></html>')
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, format, *args):
        pass

server = http.server.HTTPServer(('localhost', 8080), OAuthHandler)
webbrowser.open(auth_url)
print('Waiting for authorization...')
server.handle_request()
server.server_close()

if not auth_code:
    print('ERROR: No auth code received.')
    exit(1)

print('Auth code received! Exchanging for tokens...')

ctx = ssl.create_default_context()
data = urllib.parse.urlencode({
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'code': auth_code,
    'grant_type': 'authorization_code',
    'redirect_uri': REDIRECT_URI,
}).encode()

try:
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    resp = urllib.request.urlopen(req, context=ctx)
    tokens = json.loads(resp.read())

    access_token = tokens.get('access_token', '')
    refresh_token = tokens.get('refresh_token', '')

    print(f'  Access Token: {access_token[:20]}...')
    print(f'  Refresh Token: {refresh_token[:20]}...' if refresh_token else '  Refresh Token: NOT RETURNED')

    if refresh_token:
        # Save to .env FIRST
        with open('.env', 'r') as f:
            content = f.read()
        if 'GOOGLE_SHEETS_REFRESH_TOKEN=' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('GOOGLE_SHEETS_REFRESH_TOKEN='):
                    lines[i] = f'GOOGLE_SHEETS_REFRESH_TOKEN={refresh_token}'
            content = '\n'.join(lines)
        else:
            content = content.replace(
                f'GOOGLE_SHEETS_CLIENT_SECRET={CLIENT_SECRET}',
                f'GOOGLE_SHEETS_CLIENT_SECRET={CLIENT_SECRET}\nGOOGLE_SHEETS_REFRESH_TOKEN={refresh_token}'
            )
        with open('.env', 'w') as f:
            f.write(content)
        print()
        print(f'Refresh token saved to .env! (full token: {refresh_token})')
        print('RESULT: PASS')
    else:
        print('No refresh token. Revoke app at myaccount.google.com/permissions and retry.')
        print('RESULT: PARTIAL')

except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'FAILED (HTTP {e.code}): {body[:300]}')
except Exception as e:
    print(f'Error: {e}')
