# Hedge Edge Lead Drip - Scheduled Task Wrapper
# Runs every 2 days at 9:00 AM UTC
Continue = 'Continue'
 = 'C:\Users\sossi\Desktop\Orchestrator Hedge Edge'
 = "\.venv\Scripts\python.exe"
import sys, os, requests, json
from collections import Counter, defaultdict
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(os.path.join('.', '.env'))
KEY = os.getenv('RESEND_API_KEY')
headers = {'Authorization': f'Bearer {KEY}'}
all_emails = []
cursor = None
while True:
    params = {}
    if cursor:
        params['starting_after'] = cursor
    r = requests.get('https://api.resend.com/emails', headers=headers, params=params, timeout=10)
    data = r.json()
    batch = data.get('data', [])
    all_emails.extend(batch)
    if not data.get('has_more') or not batch:
        break
    cursor = batch[-1]['id']
drip = [e for e in all_emails if any(t.get('value') == 'lead-drip' for t in (e.get('tags') or []) if isinstance(t, dict))]
print(f'Total lead-drip emails in Resend: {len(drip)}')
recipient_nums = defaultdict(list)
for e in drip:
    to_list = e.get('to', [])
    email_num_tag = next((t.get('value') for t in (e.get('tags') or []) if isinstance(t, dict) and t.get('name') == 'email_num'), '?')
    created = e.get('created_at', '')[:19]
    for recip in (to_list if isinstance(to_list, list) else [to_list]):
        recipient_nums[recip].append({'num': email_num_tag, 'at': created})
print(f'Unique recipients: {len(recipient_nums)}')
print()
print('--- DUPLICATE CHECK ---')
dupe_count = 0
for recip, sends in sorted(recipient_nums.items()):
    nums = [s['num'] for s in sends]
    num_counts = Counter(nums)
    for num, cnt in num_counts.items():
        if cnt > 1:
            dupe_count += 1
            times = [s['at'] for s in sends if s['num'] == num]
            print(f'  DUPE: {recip} got Email #{num} x{cnt} at {times}')
if dupe_count == 0:
    print('  No duplicates found.')
print()
print('--- EMAILS PER RECIPIENT ---')
dist = Counter(len(v) for v in recipient_nums.values())
for cnt, num in sorted(dist.items()):
    print(f'  {cnt} email(s) received: {num} recipients') = "\scripts\lead_drip.py"
 = "\scripts\_lead_drip_cron.log"

# Log start
 = (Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")
Add-Content  "
===== LEAD DRIP CRON:  ====="

# Run the drip
&  import sys, os, requests, json
from collections import Counter, defaultdict
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(os.path.join('.', '.env'))
KEY = os.getenv('RESEND_API_KEY')
headers = {'Authorization': f'Bearer {KEY}'}
all_emails = []
cursor = None
while True:
    params = {}
    if cursor:
        params['starting_after'] = cursor
    r = requests.get('https://api.resend.com/emails', headers=headers, params=params, timeout=10)
    data = r.json()
    batch = data.get('data', [])
    all_emails.extend(batch)
    if not data.get('has_more') or not batch:
        break
    cursor = batch[-1]['id']
drip = [e for e in all_emails if any(t.get('value') == 'lead-drip' for t in (e.get('tags') or []) if isinstance(t, dict))]
print(f'Total lead-drip emails in Resend: {len(drip)}')
recipient_nums = defaultdict(list)
for e in drip:
    to_list = e.get('to', [])
    email_num_tag = next((t.get('value') for t in (e.get('tags') or []) if isinstance(t, dict) and t.get('name') == 'email_num'), '?')
    created = e.get('created_at', '')[:19]
    for recip in (to_list if isinstance(to_list, list) else [to_list]):
        recipient_nums[recip].append({'num': email_num_tag, 'at': created})
print(f'Unique recipients: {len(recipient_nums)}')
print()
print('--- DUPLICATE CHECK ---')
dupe_count = 0
for recip, sends in sorted(recipient_nums.items()):
    nums = [s['num'] for s in sends]
    num_counts = Counter(nums)
    for num, cnt in num_counts.items():
        if cnt > 1:
            dupe_count += 1
            times = [s['at'] for s in sends if s['num'] == num]
            print(f'  DUPE: {recip} got Email #{num} x{cnt} at {times}')
if dupe_count == 0:
    print('  No duplicates found.')
print()
print('--- EMAILS PER RECIPIENT ---')
dist = Counter(len(v) for v in recipient_nums.values())
for cnt, num in sorted(dist.items()):
    print(f'  {cnt} email(s) received: {num} recipients') --action run --batch-size 50 2>&1 | Tee-Object -Append 

# Sync waves
&  -c "import sys,os; sys.path.insert(0,''); exec(open('/scripts/lead_drip.py').read()); sync_all_waves()" 2>&1 | Tee-Object -Append 

Add-Content  "===== COMPLETE ====="
