"""Quick test for Cal.com API key — v2 API (v1 discontinued Feb 15 2026)."""
import urllib.request, json, ssl

env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

ctx = ssl.create_default_context()
key = env['CAL_API_KEY']

print('=' * 50)
print('TEST: Cal.com API Key (v2)')
print('=' * 50)
print(f"  Key prefix: {key[:12]}...")
print()

# --- Attempt 1: v2 /me with Bearer auth ---
# User is on cal.eu (EU instance), not cal.com
base_urls = [
    ('cal.eu (EU)', 'https://api.cal.eu'),
    ('cal.com (US)', 'https://api.cal.com'),
]

for label, base in base_urls:
    print(f"  [1] GET {base}/v2/me (Bearer auth) — {label}")
    try:
        req = urllib.request.Request(f'{base}/v2/me')
        req.add_header('Authorization', f'Bearer {key}')
        req.add_header('cal-api-version', '2024-08-13')
        req.add_header('User-Agent', 'HedgeEdge/1.0')
        req.add_header('Accept', 'application/json')
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read())
        u = data.get('data', data)
        print(f"      Status: OK (HTTP {resp.status})")
        print(f"      Name: {u.get('name', 'N/A')}")
        print(f"      Email: {u.get('email', 'N/A')}")
        print(f"      Username: {u.get('username', 'N/A')}")
        print(f"      Time Zone: {u.get('timeZone', 'N/A')}")
        print(f'      RESULT: PASS — use {base} as CAL_API_URL')
        # Save the working base URL
        with open('.env', 'r') as f:
            content = f.read()
        if 'CAL_API_URL' not in content:
            content = content.rstrip() + f'\nCAL_API_URL={base}\n'
            with open('.env', 'w') as f:
                f.write(content)
            print(f"      Added CAL_API_URL={base} to .env")
        break
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"      FAILED (HTTP {e.code}): {body}")
        print()
    except Exception as e:
        print(f"      Error: {e}")
        print()
else:
    print("  RESULT: FAIL (all endpoints failed)")
    print("  Check that the key is correct and active in cal.eu settings")