"""Quick schema check for all Notion databases."""
import json
from shared.notion_client import get_notion, DATABASES

n = get_notion()

# Check task_log schema first
print("=== task_log schema ===")
schema = n.databases.retrieve(database_id=DATABASES["task_log"])["properties"]
for k, v in schema.items():
    print(f"  {k}: {v['type']}")

# Check if databases.query exists
print("\n=== databases.query test ===")
try:
    r = n.databases.query(database_id=DATABASES["task_log"], page_size=1)
    print(f"query works! results: {len(r.get('results', []))}")
except AttributeError as e:
    print(f"query missing: {e}")
    # Try raw HTTP
    import requests, os
    token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    r = requests.post(
        f"https://api.notion.com/v1/databases/{DATABASES['task_log']}/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json={"page_size": 5},
        timeout=10,
    )
    print(f"raw HTTP query: {r.status_code}")
    data = r.json()
    results = data.get("results", [])
    print(f"results: {len(results)}")
    if results:
        print(f"first row props: {list(results[0].get('properties', {}).keys())}")

# Check 3 more DBs for schema consistency
for db_name in ["leads_crm", "kpi_snapshots", "competitors"]:
    print(f"\n=== {db_name} schema ===")
    schema = n.databases.retrieve(database_id=DATABASES[db_name])["properties"]
    for k, v in schema.items():
        print(f"  {k}: {v['type']}")
