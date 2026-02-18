import requests, json

import os
token = os.environ.get('CLOUDFLARE_TOKEN', 'YOUR_CLOUDFLARE_TOKEN')
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
base = "https://api.cloudflare.com/client/v4"

# Zones
r1 = requests.get(f"{base}/zones", headers=h, timeout=10)
zones = r1.json().get("result", [])
print(f"=== ZONES ({len(zones)}) ===")
for z in zones:
    print(f"  {z['name']}  id={z['id']}  status={z['status']}  plan={z.get('plan',{}).get('name','?')}")

# Accounts
r2 = requests.get(f"{base}/accounts", headers=h, timeout=10)
accts = r2.json().get("result", [])
print(f"\n=== ACCOUNTS ({len(accts)}) ===")
for a in accts:
    print(f"  {a['name']}  id={a['id']}")

# DNS records for first zone
if zones:
    zid = zones[0]["id"]
    r3 = requests.get(f"{base}/zones/{zid}/dns_records", headers=h, timeout=10)
    records = r3.json().get("result", [])
    print(f"\n=== DNS RECORDS for {zones[0]['name']} ({len(records)}) ===")
    for rec in records[:20]:
        print(f"  {rec['type']:6s}  {rec['name']:40s}  {rec.get('content','')[:60]}")

# Token permissions check
r4 = requests.get(f"{base}/user", headers=h, timeout=10)
user = r4.json()
if user.get("success"):
    u = user["result"]
    print(f"\n=== USER ===")
    print(f"  email: {u.get('email','?')}  id: {u.get('id','?')}")
else:
    print(f"\n=== USER === (token may not have user:read)")
    print(json.dumps(user.get("errors", []), indent=2))
