"""Test Discord bot token and Resend API key."""
import urllib.request, json, ssl

env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

ctx = ssl.create_default_context()

# --- TEST 1: Discord Bot Token ---
print('=' * 50)
print('TEST 1: Discord Bot Token')
print('=' * 50)
try:
    req = urllib.request.Request('https://discord.com/api/v10/users/@me')
    req.add_header('Authorization', f"Bot {env['DISCORD_BOT_TOKEN']}")
    req.add_header('User-Agent', 'HedgeEdge/1.0')
    resp = urllib.request.urlopen(req, context=ctx)
    data = json.loads(resp.read())
    print(f"  Status: OK (HTTP {resp.status})")
    print(f"  Bot Name: {data.get('username', 'N/A')}#{data.get('discriminator', '0')}")
    print(f"  Bot ID: {data.get('id', 'N/A')}")
    print(f"  Verified: {data.get('verified', 'N/A')}")
    print('  RESULT: PASS')
except urllib.error.HTTPError as e:
    body = e.read().decode()[:300]
    print(f"  FAILED (HTTP {e.code}): {body}")
    print('  RESULT: FAIL')
except Exception as e:
    print(f"  Error: {e}")
    print('  RESULT: FAIL')

# --- TEST 2: Resend API Key ---
print()
print('=' * 50)
print('TEST 2: Resend API Key')
print('=' * 50)
try:
    req = urllib.request.Request('https://api.resend.com/domains')
    req.add_header('Authorization', f"Bearer {env['RESEND_API_KEY']}")
    req.add_header('User-Agent', 'HedgeEdge/1.0')
    resp = urllib.request.urlopen(req, context=ctx)
    data = json.loads(resp.read())
    print(f"  Status: OK (HTTP {resp.status})")
    domains = data.get('data', [])
    if domains:
        for d in domains:
            print(f"  Domain: {d.get('name', 'N/A')} (status: {d.get('status', 'N/A')})")
    else:
        print("  No domains configured yet (add one at resend.com/domains)")
    print('  RESULT: PASS')
except urllib.error.HTTPError as e:
    body = e.read().decode()[:300]
    print(f"  FAILED (HTTP {e.code}): {body}")
    print('  RESULT: FAIL')
except Exception as e:
    print(f"  Error: {e}")
    print('  RESULT: FAIL')

print()
print('=' * 50)
print('DONE')
print('=' * 50)
