"""Fetch the LinkedIn verification email from Resend API."""
import urllib.request
import json

import os
API_KEY = os.environ.get('RESEND_API_KEY', 'YOUR_RESEND_API_KEY')
EMAIL_ID = "ead93c3a-f4a4-4369-81ef-11fe9950b13e"

endpoints = [
    f"https://api.resend.com/emails/{EMAIL_ID}",
    f"https://api.resend.com/received-emails/{EMAIL_ID}",
    f"https://api.resend.com/received-emails/{EMAIL_ID}/content",
]

for url in endpoints:
    print(f"\n--- {url} ---")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(json.dumps(data, indent=2)[:3000])
    except Exception as e:
        print(f"Error: {e}")
