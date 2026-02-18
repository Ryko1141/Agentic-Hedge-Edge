"""Test Google Sheets OAuth2 credentials."""
import urllib.request, urllib.parse, json, ssl, os

ctx = ssl.create_default_context()
client_id = os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID')
client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')

print('=' * 50)
print('TEST: Google Sheets OAuth2 Credentials')
print('=' * 50)

data = urllib.parse.urlencode({
    'client_id': client_id,
    'client_secret': client_secret,
    'code': 'dummy_test_code',
    'grant_type': 'authorization_code',
    'redirect_uri': 'http://localhost:8080'
}).encode()

try:
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    resp = urllib.request.urlopen(req, context=ctx)
    print(f'  Unexpected success: {resp.read().decode()[:200]}')
except urllib.error.HTTPError as e:
    body = json.loads(e.read().decode())
    error = body.get('error', '')
    desc = body.get('error_description', '')
    if error == 'invalid_grant':
        print(f'  Client ID: VALID')
        print(f'  Client Secret: VALID')
        print(f'  (Dummy auth code rejected as expected)')
        print('  RESULT: PASS')
    elif error == 'invalid_client':
        print(f'  FAILED: {error} - {desc}')
        print('  RESULT: FAIL')
    elif error == 'redirect_uri_mismatch':
        print(f'  Client ID: VALID')
        print(f'  Client Secret: VALID')
        print(f'  (Redirect URI mismatch — add http://localhost:8080)')
        print('  RESULT: PASS')
    else:
        print(f'  Error: {error} - {desc}')

# Check if this is the same client as YouTube (same ID, different secret)
yt_secret = os.environ.get('YOUTUBE_CLIENT_SECRET', 'YOUR_YOUTUBE_CLIENT_SECRET')
if client_secret != yt_secret:
    print()
    print('  NOTE: Different secret from YouTube OAuth client.')
    print(f'  YouTube secret: {yt_secret[:15]}...')
    print(f'  Sheets secret:  {client_secret[:15]}...')
    print('  If this is the SAME OAuth client, the YouTube secret may have been')
    print('  regenerated. Check if YouTube refresh token still works.')
