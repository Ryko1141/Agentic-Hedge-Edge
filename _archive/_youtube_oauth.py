"""
YouTube OAuth2 Flow — Get refresh token for YouTube Data API.
Opens browser for Google login, captures auth code via local server.
"""
import http.server
import urllib.request
import urllib.parse
import json
import ssl
import webbrowser
import threading

# Load .env
env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

CLIENT_ID = env['YOUTUBE_CLIENT_ID']
CLIENT_SECRET = env['YOUTUBE_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8080'
SCOPES = ' '.join([
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
])

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
            self.wfile.write(b'<html><body><h1>Success!</h1><p>You can close this tab and return to VS Code.</p></body></html>')
        elif 'error' in params:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            error = params.get('error', ['unknown'])[0]
            self.wfile.write(f'<html><body><h1>Error: {error}</h1></body></html>'.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logs

# Build auth URL
auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id': CLIENT_ID,
    'redirect_uri': REDIRECT_URI,
    'response_type': 'code',
    'scope': SCOPES,
    'access_type': 'offline',
    'prompt': 'consent',
})

print('=' * 60)
print('YouTube OAuth2 Flow')
print('=' * 60)
print()
print('Opening browser for Google login...')
print(f'If browser does not open, visit:')
print(f'  {auth_url[:100]}...')
print()

# Start local server
server = http.server.HTTPServer(('localhost', 8080), OAuthHandler)
server.timeout = 120  # 2 minute timeout

# Open browser
webbrowser.open(auth_url)

print('Waiting for authorization (2 min timeout)...')
print()

# Wait for callback
while auth_code is None:
    server.handle_request()
    if auth_code is not None:
        break

server.server_close()

if not auth_code:
    print('ERROR: No auth code received. Timed out.')
    exit(1)

print(f'Auth code received: {auth_code[:20]}...')
print('Exchanging for refresh token...')
print()

# Exchange code for tokens
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
    
    print(f'Access Token: {access_token[:30]}...')
    print(f'Refresh Token: {refresh_token[:30]}...')
    print()
    
    if refresh_token:
        # Save to .env
        with open('.env', 'r') as f:
            content = f.read()
        
        if 'YOUTUBE_REFRESH_TOKEN' in content:
            # Replace existing
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith('YOUTUBE_REFRESH_TOKEN='):
                    new_lines.append(f'YOUTUBE_REFRESH_TOKEN={refresh_token}')
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        else:
            # Append after client secret
            content = content.replace(
                f'YOUTUBE_CLIENT_SECRET={CLIENT_SECRET}',
                f'YOUTUBE_CLIENT_SECRET={CLIENT_SECRET}\nYOUTUBE_REFRESH_TOKEN={refresh_token}'
            )
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print('Saved YOUTUBE_REFRESH_TOKEN to .env')
        print()
        
        # Quick test: get channel info
        print('Testing: Fetching YouTube channel info...')
        req2 = urllib.request.Request('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true')
        req2.add_header('Authorization', f'Bearer {access_token}')
        resp2 = urllib.request.urlopen(req2, context=ctx)
        ch_data = json.loads(resp2.read())
        items = ch_data.get('items', [])
        if items:
            ch = items[0]['snippet']
            print(f'  Channel: {ch.get("title", "N/A")}')
            print(f'  Description: {ch.get("description", "N/A")[:80]}')
            print(f'  Custom URL: {ch.get("customUrl", "N/A")}')
        else:
            print('  No channels found for this account')
        
        print()
        print('RESULT: PASS — YouTube fully connected!')
    else:
        print('WARNING: No refresh token returned.')
        print('This happens if you already authorized before.')
        print('Go to https://myaccount.google.com/permissions')
        print('Remove "Hedge Edge" app access, then run this again.')
        
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'FAILED (HTTP {e.code}): {body[:300]}')
except Exception as e:
    print(f'Error: {e}')
