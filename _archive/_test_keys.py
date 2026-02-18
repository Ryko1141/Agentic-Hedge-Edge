"""Quick test for Notion + Supabase API keys."""
import os, urllib.request, json, ssl

# Load .env manually
env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

ctx = ssl.create_default_context()

# --- TEST 1: Notion API ---
print('=' * 50)
print('TEST 1: Notion API Key')
print('=' * 50)
try:
    req = urllib.request.Request(
        'https://api.notion.com/v1/users/me',
        headers={
            'Authorization': f"Bearer {env['NOTION_API_KEY']}",
            'Notion-Version': '2022-06-28'
        }
    )
    resp = urllib.request.urlopen(req, context=ctx)
    data = json.loads(resp.read())
    print(f"  Status: OK (HTTP {resp.status})")
    print(f"  Bot Name: {data.get('name', 'N/A')}")
    print(f"  Bot ID: {data.get('id', 'N/A')}")
    print(f"  Type: {data.get('type', 'N/A')}")
    if data.get('bot'):
        owner = data['bot'].get('owner', {})
        print(f"  Owner Type: {owner.get('type', 'N/A')}")
    print('  RESULT: PASS ✓')
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  Status: FAILED (HTTP {e.code})")
    print(f"  Error: {body[:200]}")
    print('  RESULT: FAIL ✗')
except Exception as e:
    print(f"  Error: {e}")
    print('  RESULT: FAIL ✗')

# --- TEST 2: Supabase ---
print()
print('=' * 50)
print('TEST 2: Supabase Service Role Key')
print('=' * 50)

supa_key = env.get('SUPABASE_SERVICE_ROLE_KEY', '')
supa_url = env.get('SUPABASE_URL', '')

if not supa_url:
    # Try to decode project ref from the JWT (service_role key is a JWT)
    # The key format is: header.payload.signature — payload has project info
    import base64
    parts = supa_key.split('.')
    if len(parts) == 3:
        # Decode the payload
        payload = parts[1]
        # Add padding
        payload += '=' * (4 - len(payload) % 4)
        try:
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            print(f"  JWT Payload: role={decoded.get('role')}, iss={decoded.get('iss', 'N/A')}")
            iss = decoded.get('iss', '')
            if 'supabase' in iss:
                supa_url = iss.replace('/auth/v1', '')
                print(f"  Detected URL: {supa_url}")
        except Exception as e:
            print(f"  Could not decode JWT: {e}")
    
    if not supa_url:
        print("  No SUPABASE_URL in .env and could not auto-detect it.")
        print("  Trying the key as-is against Supabase Management API...")
        # Try Supabase Management API (if it's an access token, not service_role)
        try:
            req = urllib.request.Request(
                'https://api.supabase.com/v1/projects',
                headers={
                    'Authorization': f"Bearer {supa_key}",
                }
            )
            resp = urllib.request.urlopen(req, context=ctx)
            data = json.loads(resp.read())
            if isinstance(data, list):
                print(f"  Found {len(data)} project(s):")
                for proj in data[:5]:
                    name = proj.get('name', 'N/A')
                    ref = proj.get('id', 'N/A')
                    region = proj.get('region', 'N/A')
                    status = proj.get('status', 'N/A')
                    print(f"    - {name} (ref: {ref}, region: {region}, status: {status})")
                    org_id = proj.get('organization_id', '')
                print('  RESULT: PASS ✓ (Management API access token)')
            else:
                print(f"  Response: {json.dumps(data)[:200]}")
                print('  RESULT: PASS ✓')
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  Management API: FAILED (HTTP {e.code})")
            print(f"  Error: {body[:300]}")
            print('  RESULT: FAIL ✗')
            print()
            print("  NOTE: If this is a service_role key (starts with 'eyJ...'),")
            print("  you also need SUPABASE_URL in .env to test it against your project.")
        except Exception as e:
            print(f"  Error: {e}")
            print('  RESULT: FAIL ✗')
else:
    # We have both URL and key — test against the project
    try:
        req = urllib.request.Request(
            f"{supa_url}/rest/v1/",
            headers={
                'apikey': supa_key,
                'Authorization': f"Bearer {supa_key}",
            }
        )
        resp = urllib.request.urlopen(req, context=ctx)
        print(f"  Status: OK (HTTP {resp.status})")
        print(f"  URL: {supa_url}")
        print('  RESULT: PASS ✓')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Status: FAILED (HTTP {e.code})")
        print(f"  Error: {body[:200]}")
        print('  RESULT: FAIL ✗')
    except Exception as e:
        print(f"  Error: {e}")
        print('  RESULT: FAIL ✗')

print()
print('=' * 50)
print('DONE')
print('=' * 50)
