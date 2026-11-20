"""Inspect execution #12 details and failure reasons."""
import requests, json

BASE = "http://127.0.0.1:8001/api"
r = requests.get(f"{BASE}/executions/12")
if r.status_code == 200:
    data = r.json()
    print("Execution #12 Details:")
    for res in data.get("results", []):
        print(f"\n  Test: {res.get('test_id')} - {res.get('test_name')}")
        print(f"  Status: {res.get('status')}")
        print(f"  Category: {res.get('failure_category')}")
        print(f"  Duration: {res.get('duration_ms')}ms")
        print(f"  Error: {res.get('error_message')}")
        print(f"  Screenshot: {res.get('screenshot_path')}")
else:
    print(f"Failed to fetch execution: {r.status_code}")
