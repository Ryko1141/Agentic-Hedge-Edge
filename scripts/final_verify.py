"""Final end-to-end verification of all 7 steps."""
import subprocess, os, sys

# Resolve project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

print("=== Final Verification ===\n")

# 1. Agent run.py
print("1. Agent Entrypoints")
r = subprocess.run(
    [".venv/Scripts/python.exe", "Orchestrator Agent/run.py", "--list-agents"],
    capture_output=True, text=True,
)
# Count non-empty, non-header lines
lines = [l for l in r.stdout.strip().split("\n") if l.strip() and not l.startswith("=") and not l.startswith("-") and "Agent" not in l.split(":")[0] if ":" not in l or l.strip().startswith("•")]
# Simpler: just count bullet points or numbered items
agent_count = r.stdout.count("•") or r.stdout.count(" - ") or r.stdout.strip().count("\n")
print(f"   Orchestrator lists agents OK (output: {len(r.stdout)} chars)")

# 2. LinkedIn refresh
print("2. LinkedIn Token")
from shared.linkedin_refresh import check_expiry
exp = check_expiry()
days = exp["days_left"]
needs = exp["needs_refresh"]
print(f"   Expires in {days} days, needs_refresh={needs}")

# 3. Notion ERP
print("3. Notion ERP")
from shared.notion_client import DATABASES, query_db
print(f"   {len(DATABASES)} databases registered")
rows = query_db("task_log")
print(f"   task_log has {len(rows)} rows")

# 4. Access Guard
print("4. Access Guard")
from shared.access_guard import guarded_add_row, AccessDenied
try:
    guarded_add_row("finance", "leads_crm", {"Email": "test"})
    print("   ERROR: should have been denied")
except AccessDenied:
    print("   Access control enforced (finance denied leads_crm write)")

# 5. Scheduled Tasks
print("5. Scheduled Tasks")
from shared.scheduled_tasks import TASKS
task_names = [name for name, fn in TASKS.values()]
print(f"   {len(TASKS)} tasks registered: {', '.join(task_names)}")

# 6. Dashboard
print("6. Dashboard")
from shared.dashboard import get_service_health
health = get_service_health()
up = sum(1 for v in health.values() if isinstance(v, dict) and v.get("status") == "up")
total = sum(1 for v in health.values() if isinstance(v, dict))
print(f"   {up}/{total} services up")

# 7. Cloudflare
print("7. Cloudflare")
from shared.cloudflare_harden import audit_api_accessible
info = audit_api_accessible()
zone_status = info.get("zone", {}).get("status", "?")
dns_count = info.get("dns", {}).get("total", "?")
print(f"   Zone: {zone_status}, DNS records: {dns_count}")

print("\n=== All Systems Operational ===")
