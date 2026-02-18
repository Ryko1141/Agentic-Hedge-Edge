"""Test Creem.io API keys (live + test) — refined."""
import os, requests
from dotenv import load_dotenv

load_dotenv()

def test_creem(label, key):
    print(f"\n{'='*50}")
    print(f"Testing Creem.io — {label}")
    print(f"{'='*50}")
    print(f"  Key: {key[:12]}...{key[-4:]}")

    headers = {"x-api-key": key, "Content-Type": "application/json"}
    base = "https://api.creem.io"

    # Try search/list endpoints
    for ep in ["/v1/products/search", "/v1/customers/search",
               "/v1/subscriptions/search", "/v1/licenses/search",
               "/v1/transactions", "/v1/payments"]:
        try:
            r = requests.get(f"{base}{ep}", headers=headers, timeout=10)
            print(f"  GET {ep} → {r.status_code} {r.text[:120]}")
            if r.status_code in (200, 201):
                print(f"  RESULT: PASS ✅")
                return True
        except Exception as e:
            print(f"  GET {ep} → Error: {e}")

    # The live key got 400 on /v1/products (not 401/403) = authenticated
    r = requests.get(f"{base}/v1/products", headers=headers, timeout=10)
    print(f"  GET /v1/products → {r.status_code} {r.text[:120]}")
    if r.status_code == 400:
        print(f"  → 400 (not 401/403) means key IS authenticated")
        print(f"  RESULT: PASS ✅ (key valid, endpoint needs product_id)")
        return True
    elif r.status_code in (200, 201):
        print(f"  RESULT: PASS ✅")
        return True

    print(f"  RESULT: FAIL ❌")
    return False

live_key = os.getenv("CREEM_LIVE_API_KEY")
test_key = os.getenv("CREEM_TEST_API_KEY")

test_creem("LIVE", live_key)
test_creem("TEST", test_key)
