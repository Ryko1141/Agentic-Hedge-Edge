"""
Notion Database Connectivity Check
───────────────────────────────────
Loops through every entry in shared.notion_client.DATABASES,
tests each with a query (page_size=1), and prints a status table.

Note: notion-client 2.7.0 uses API version 2025-09-03 which broke
databases.query(). We use httpx directly with the stable 2022-06-28 version.
"""
import sys, os

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import httpx
from shared.notion_client import DATABASES, get_notion

notion = get_notion()
token = notion.options.auth
HEADERS = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

ok_count = 0
err_count = 0

print(f"{'DB Name':<25} {'DB ID':<38} {'Status':<12} {'Rows':>5}")
print("─" * 85)

with httpx.Client(timeout=30) as http:
    for db_name, db_id in DATABASES.items():
        try:
            r = http.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers=HEADERS,
                json={"page_size": 1},
            )
            r.raise_for_status()
            data = r.json()
            row_count = len(data.get("results", []))
            status = "OK"
            ok_count += 1
            print(f"{db_name:<25} {db_id:<38} {status:<12} {row_count:>5}")
        except Exception as e:
            err_str = str(e)
            short_err = f"ERROR: {err_str[:48]}…" if len(err_str) > 48 else f"ERROR: {err_str}"
            err_count += 1
            print(f"{db_name:<25} {db_id:<38} {short_err}")

print("─" * 85)
print(f"\nTotal: {len(DATABASES)} databases  |  Accessible: {ok_count}  |  Inaccessible: {err_count}")
