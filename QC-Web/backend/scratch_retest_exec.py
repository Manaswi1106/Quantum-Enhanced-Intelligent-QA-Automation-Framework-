"""Re-execute tests 78, 83, 95, 99 and verify executor improvements."""
import requests, time

BASE = "http://127.0.0.1:8001/api"
r = requests.post(f"{BASE}/tests/execute", json={"app_id": 8, "test_case_ids": [78, 83, 95, 99]}, timeout=180)
print(f"Execution start status: {r.status_code}")
if r.status_code == 200:
    exec_id = r.json()["id"]
    print(f"Execution #{exec_id} running...")
    for i in range(60):
        time.sleep(3)
        res = requests.get(f"{BASE}/executions/{exec_id}").json()
        print(f"[{i*3}s] status={res['status']} passed={res.get('passed',0)} failed={res.get('failed',0)} progress={res.get('progress_percent',0)}%")
        if res["status"] in ("completed", "error"):
            break

    print("\nIndividual Test Results:")
    for tr in res.get("results", []):
        print("="*60)
        print(f"Test: {tr.get('test_id')} - {tr.get('test_name')}")
        print(f"Status: {tr.get('status')}")
        print(f"Category: {tr.get('failure_category')}")
        print(f"Duration: {tr.get('duration_ms')}ms")
        print(f"Error: {tr.get('error_message')}")
