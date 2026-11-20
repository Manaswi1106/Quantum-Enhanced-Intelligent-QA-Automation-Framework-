import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

def make_req(endpoint, data=None, method=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"ERROR {e.code} on {endpoint}: {err_body}")
        return {"error": err_body, "status_code": e.code}

print("==================================================")
print("STAGE 1: ANALYZE SHOPSPHERE DYNAMICALLY")
print("==================================================")
analyze_res = make_req("/applications/analyze", {"url": "https://qc-e-com-1.vercel.app", "force": True})
app_id = analyze_res.get("id")
print(f"App #{app_id}: {analyze_res.get('name')}")
print(f"Discovered Pages: {analyze_res.get('discovered_pages')}")
print(f"Discovered Elements: {analyze_res.get('discovered_elements')}")

print("\n==================================================")
print("STAGE 2: GENERATE REAL AI CANDIDATE TESTS")
print("==================================================")
gen_res = make_req("/test-cases/generate", {"app_id": app_id})
print(f"Total Candidate Tests in Suite for App #{app_id}: {len(gen_res)}")
for i, tc in enumerate(gen_res[:10], 1):
    print(f"  {i}. [{tc.get('test_id')}] ({tc.get('priority')}) {tc.get('name')}")
    print(f"     Steps: {tc.get('steps', [''])[:2]}")
    print(f"     Expected: {tc.get('expected_result')}")

print("\n==================================================")
print("STAGE 3: RUN QAOA OPTIMIZATION")
print("==================================================")
budget = min(len(gen_res), 5) if len(gen_res) > 0 else 3
qaoa_res = make_req("/optimization/qaoa", {
    "app_id": app_id,
    "budget": budget,
    "p": 1,
    "shots": 512
})
selected_ids = qaoa_res.get("selected_ids", [])
print(f"QAOA Candidates: {qaoa_res.get('total_candidates')}")
print(f"QAOA Selected ({len(selected_ids)} tests): {selected_ids}")
print(f"QAOA Objective Value: {qaoa_res.get('objective_value')}")

print("\n==================================================")
print("STAGE 4: EXECUTE QAOA-SELECTED TESTS")
print("==================================================")
exec_res = make_req("/tests/execute", {
    "app_id": app_id,
    "test_case_ids": selected_ids,
})
exec_id = exec_res.get("id")
print(f"Execution #{exec_id} started: Status = {exec_res.get('status')}, Total Tests = {exec_res.get('total')}")

# Poll execution until finished
while True:
    time.sleep(3)
    hist = make_req(f"/tests/executions/{exec_id}")
    st = hist.get("status")
    print(f"  -> Execution #{exec_id} status: {st} (Passed: {hist.get('passed')}, Failed: {hist.get('failed')})")
    if st in ("completed", "failed", "error", None) or "error" in hist:
        break

print("\n==================================================")
print("STAGE 5: VERIFY FINAL RESULTS & CLASSIFICATIONS")
print("==================================================")
results = make_req("/results")
print("Results Analytics Dashboard:", json.dumps({
    "total_candidates": results.get("total_candidates"),
    "optimized_tests": results.get("optimized_tests"),
    "reduction_percent": results.get("reduction_percent"),
    "executed_tests": results.get("executed_tests"),
    "passed": results.get("passed"),
    "failed": results.get("failed"),
    "detected_defects": results.get("detected_defects"),
    "application_failures": results.get("application_failures"),
    "navigation_failures": results.get("navigation_failures"),
    "runtime_sec": results.get("runtime_sec")
}, indent=2))
