"""Verify that calling test generation on an unreachable app cleanly rejects with 400."""
import requests

BASE = "http://127.0.0.1:8001/api"
r = requests.post(f"{BASE}/test-cases/generate", json={"app_id": 11})
print(f"Status Code: {r.status_code}")
print(f"Response: {r.text}")
