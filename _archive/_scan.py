"""Quick scan of AGENTIC BUSINESS page structure."""
import os, json
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
TOKEN = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
if not TOKEN:
    mcp_path = os.path.join(os.path.dirname(__file__), ".vscode", "mcp.json")
    with open(mcp_path) as f:
        mcp = json.load(f)
    TOKEN = mcp["servers"]["makenotion/notion-mcp-server"]["env"]["NOTION_TOKEN"]

notion = Client(auth=TOKEN)
AGENTIC_PAGE = "2fb652ea-6c6d-80aa-b4fb-e40a1a8c5248"

def get_text(block):
    btype = block["type"]
    for key in ("heading_1","heading_2","heading_3","paragraph","toggle","callout","quote"):
        if btype == key:
            rich = block[key].get("rich_text", [])
            return " ".join(r["plain_text"] for r in rich)
    if btype == "child_page": return block["child_page"].get("title", "")
    if btype == "child_database": return block["child_database"].get("title", "")
    return ""

all_blocks = []
cursor = None
while True:
    kwargs = {"block_id": AGENTIC_PAGE, "page_size": 100}
    if cursor: kwargs["start_cursor"] = cursor
    resp = notion.blocks.children.list(**kwargs)
    all_blocks.extend(resp["results"])
    cursor = resp.get("next_cursor")
    if not cursor: break

print(f"Total blocks: {len(all_blocks)}\n")
for i, b in enumerate(all_blocks):
    text = get_text(b)
    btype = b["type"]
    color = ""
    if btype in ("heading_1","heading_2") and btype in b:
        color = b[btype].get("color","")
    prefix = ""
    if btype == "divider": prefix = "───"
    elif btype.startswith("heading"): prefix = f"H{btype[-1]}"
    elif btype == "child_page": prefix = "📁PG"
    elif btype == "child_database": prefix = "📊DB"
    elif btype == "toggle": prefix = "▶TG"
    else: prefix = btype[:4]
    print(f"  {i:3d} {prefix:6s} {text[:55]:55s} {b['id'][:15]}")
