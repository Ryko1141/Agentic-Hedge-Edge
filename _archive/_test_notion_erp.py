from shared.notion_client import get_notion, query_db

rows = query_db("task_log")
notion = get_notion()
for r in rows:
    if not r.get("Task"):
        notion.pages.update(page_id=r["_id"], archived=True)
        pid = r["_id"]
        print(f"Archived blank row: {pid}")
print("Done")
