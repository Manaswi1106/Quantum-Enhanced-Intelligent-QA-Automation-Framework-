"""Print full error messages from execution #12 without printing binary."""
import requests

BASE = "http://127.0.0.1:8001/api"
r = requests.get(f"{BASE}/executions/12")
if r.status_code == 200:
    data = r.json()
    print("Execution #12 Results:")
    for res in data.get("results", []):
        print("="*60)
        print(f"Test: {res.get('test_id')} - {res.get('test_name')}")
        print(f"Status: {res.get('status')}")
        print(f"Category: {res.get('failure_category')}")
        print(f"Duration: {res.get('duration_ms')}ms")
        print(f"Error: {res.get('error_message')}")
        sc = res.get('screenshot_path')
        if sc and sc.startswith('data:image'):
            print(f"Screenshot: [Base64 image present, length: {len(sc)}]")
        else:
            print(f"Screenshot: {sc}")
