import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def make_req(path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTP Error {e.code} on {path}: {err_msg}")
        return {"error": err_msg, "status_code": e.code}

print("=== 1. Checking Applications ===")
apps = make_req("/applications")
print(f"Applications found: {len(apps)}")
for a in apps:
    print(f"  - App #{a['id']}: {a['name']} ({a['url']}) | Pages: {a['discovered_pages']}, Elements: {a['discovered_elements']}")

print("\n=== 2. Checking Overview Metrics ===")
metrics = make_req("/overview/metrics")
print("Live Platform Metrics:", json.dumps(metrics, indent=2))

if apps:
    target_app = apps[0]
    app_id = target_app["id"]
    print(f"\n=== 3. Checking Candidate Tests for App #{app_id} ===")
    tcs = make_req(f"/test-cases?app_id={app_id}")
    print(f"Total candidate tests for App #{app_id}: {len(tcs)}")
    for tc in tcs[:5]:
        print(f"  [{tc['test_id']}] {tc['name']} (Priority: {tc['priority']}, Risk: {tc['risk']}, Route: {getattr(tc, 'target_route', '/')})")

    print(f"\n=== 4. Testing QAOA Optimization on Candidate Suite ===")
    qaoa_payload = {
        "app_id": app_id,
        "budget": min(len(tcs), 5) if len(tcs) > 0 else 3,
        "p": 1,
        "shots": 512,
    }
    qaoa_res = make_req("/optimization/qaoa", qaoa_payload)
    if "error" not in qaoa_res:
        selected_ids = qaoa_res.get("selected_ids", [])
        print(f"QAOA selected {len(selected_ids)} tests out of {qaoa_res.get('total_candidates')}: {selected_ids}")
        print(f"Objective value: {qaoa_res.get('objective_value')}")
        print(f"QAOA metadata: {json.dumps(qaoa_res.get('metadata', {}), indent=2)}")
    else:
        print("QAOA run result:", qaoa_res)

print("\n=== 5. Checking Results Analytics Endpoint ===")
results = make_req("/results")
print("Results Analytics:", json.dumps({
    "status": results.get("status"),
    "total_candidates": results.get("total_candidates"),
    "optimized_tests": results.get("optimized_tests"),
    "reduction_percent": results.get("reduction_percent"),
    "executed_tests": results.get("executed_tests"),
    "passed": results.get("passed"),
    "failed": results.get("failed"),
    "detected_defects": results.get("detected_defects"),
    "application_failures": results.get("application_failures"),
    "navigation_failures": results.get("navigation_failures"),
    "runtime_sec": results.get("runtime_sec"),
}, indent=2))
