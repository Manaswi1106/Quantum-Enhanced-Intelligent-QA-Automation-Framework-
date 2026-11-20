"""Check steps and definition of tests in execution #12."""
import requests

BASE = "http://127.0.0.1:8001/api"
r = requests.get(f"{BASE}/test-cases?app_id=8")
if r.status_code == 200:
    all_tests = r.json()
    test_map = {t["id"]: t for t in all_tests}
    target_ids = [78, 83, 95, 99]
    for tid in target_ids:
        tc = test_map.get(tid)
        if tc:
            print("="*60)
            print(f"ID: {tc.get('id')} | {tc.get('test_id')} | {tc.get('name')}")
            print(f"Target Route: {tc.get('target_route')}")
            print(f"Steps: {tc.get('steps')}")
            print(f"Expected: {tc.get('expected_result')}")
