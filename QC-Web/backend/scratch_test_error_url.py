"""Verify error recovery for an unreachable / invalid URL."""
import requests, time

BASE = "http://127.0.0.1:8001/api"
FAKE_URL = "https://this-domain-does-not-exist-at-all-xyz987123.com"

print("="*60)
print(f"Testing Unreachable URL Error Handling: {FAKE_URL}")
print("="*60)

t0 = time.time()
try:
    r = requests.post(f"{BASE}/applications/analyze", json={"url": FAKE_URL, "force": True}, timeout=30)
    elapsed = time.time() - t0
    print(f"Status Code: {r.status_code} in {elapsed:.1f}s")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"Request exception: {e}")
