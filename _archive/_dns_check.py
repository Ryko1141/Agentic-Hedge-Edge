"""Quick test: verify updated cloudflare_client.py works with account-scoped token."""
from shared.cloudflare_client import (
    verify_token, list_zones, get_default_zone_id,
    list_dns_records, get_status_summary,
)

t = verify_token()
print(f"Token: {t['status']}")

zs = list_zones()
print(f"Zones: {len(zs)}")
for z in zs:
    print(f"  {z['name']}  id={z['id']}  status={z['status']}")

zid = get_default_zone_id()
print(f"Default zone ID: {zid}")

recs = list_dns_records(zid, record_type="CNAME")
print(f"CNAME records ({len(recs)}):")
for r in recs:
    print(f"  {r['name']} -> {r['content']}  proxied={r['proxied']}")

# Test Short.io domain status
import requests, os
shortio_key = os.getenv("SHORTIO_API_KEY", "")
r3 = requests.get("https://api.short.io/api/domains",
                   headers={"Authorization": shortio_key}, timeout=10)
domains = r3.json()
print(f"\nShort.io domains:")
for d in domains:
    print(f"  {d['hostname']}  state={d.get('state')}  id={d.get('id')}")
