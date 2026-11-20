"""Quick end-to-end pipeline verification script."""
import requests, time, json, sys

BASE = "http://127.0.0.1:8001/api"
TARGET_URL = "https://qc-e-com-1.vercel.app"

def step(label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

# 1. Check AI status
step("1. AI STATUS CHECK")
r = requests.get(f"{BASE}/ai/status")
print(f"  Status: {r.status_code}")
ai = r.json()
print(f"  Configured: {ai.get('configured')}, Provider: {ai.get('provider')}")

# 2. Check existing apps
step("2. EXISTING APPLICATIONS")
r = requests.get(f"{BASE}/applications")
apps = r.json()
print(f"  Total apps: {len(apps)}")
for a in apps:
    print(f"    App #{a['id']}: {a['name']} | {a['url']} | pages={a.get('discovered_pages',0)} | elements={a.get('discovered_elements',0)} | status={a['status']}")

# Find our target app
target_app = None
for a in apps:
    if TARGET_URL in a.get("url", ""):
        target_app = a
        break

# 3. If no existing app or insufficient discovery, analyze
if not target_app or target_app.get("discovered_pages", 0) <= 1:
    step("3. ANALYZING WEBSITE (may take 30-60s)")
    t0 = time.time()
    r = requests.post(f"{BASE}/applications/analyze", json={"url": TARGET_URL, "force": True}, timeout=120)
    elapsed = time.time() - t0
    print(f"  Status: {r.status_code} Time: {elapsed:.1f}s")
    if r.status_code == 200:
        target_app = r.json()
        print(f"  App #{target_app['id']}: pages={target_app.get('discovered_pages',0)} elements={target_app.get('discovered_elements',0)}")
    else:
        print(f"  FAILED: {r.text[:500]}")
        sys.exit(1)
else:
    step("3. USING EXISTING APP (already analyzed)")
    print(f"  App #{target_app['id']}: pages={target_app.get('discovered_pages',0)} elements={target_app.get('discovered_elements',0)}")

app_id = target_app["id"]

# 4. Check existing test cases for this app
step("4. EXISTING TEST CASES")
r = requests.get(f"{BASE}/test-cases?app_id={app_id}")
existing_tests = r.json()
print(f"  Existing tests for app #{app_id}: {len(existing_tests)}")
for tc in existing_tests[:5]:
    print(f"    {tc['test_id']}: {tc['name'][:60]} (source={tc['source']}, priority={tc['priority']})")
if len(existing_tests) > 5:
    print(f"    ... and {len(existing_tests) - 5} more")

# 5. Generate new test cases
step("5. AI TEST GENERATION")
t0 = time.time()
r = requests.post(f"{BASE}/test-cases/generate", json={"app_id": app_id}, timeout=180)
elapsed = time.time() - t0
print(f"  Status: {r.status_code} Time: {elapsed:.1f}s")
if r.status_code == 200:
    tests = r.json()
    print(f"  Total tests after generation: {len(tests)}")
    new_tests = [t for t in tests if t not in existing_tests]
    print(f"  New tests added: {len(tests) - len(existing_tests)}")
    for tc in tests[-10:]:
        print(f"    {tc['test_id']}: {tc['name'][:60]} (source={tc['source']}, priority={tc['priority']})")
else:
    print(f"  FAILED: {r.text[:500]}")

# 6. Build QUBO
step("6. QUBO FORMULATION")
r = requests.post(f"{BASE}/optimization/qubo", json={"app_id": app_id, "budget": 5}, timeout=30)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    qubo = r.json()
    print(f"  QUBO matrix size: {qubo.get('matrix_size')}")
    print(f"  Candidates: {qubo.get('n_candidates')}")
else:
    print(f"  FAILED: {r.text[:300]}")

# 7. Run QAOA
step("7. QAOA OPTIMIZATION")
r = requests.post(f"{BASE}/optimization/qaoa", json={"app_id": app_id, "budget": 5, "p": 1, "shots": 512}, timeout=120)
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    qaoa = r.json()
    print(f"  Selected: {len(qaoa.get('selected_tests', []))} out of {qaoa.get('qubo_size')}")
    selected = qaoa.get("selected_tests", [])
    print(f"  Selected test IDs: {selected}")
else:
    print(f"  FAILED: {r.text[:300]}")

# 8. Execute tests
step("8. PLAYWRIGHT EXECUTION")
# Get QAOA-selected test IDs
test_ids_to_run = []
if r.status_code == 200 and qaoa.get("selected_tests"):
    raw_sel = qaoa["selected_tests"]
    for s in raw_sel:
        if isinstance(s, int):
            test_ids_to_run.append(s)
        elif isinstance(s, dict) and "id" in s:
            test_ids_to_run.append(s["id"])

if test_ids_to_run:
    print(f"  Executing {len(test_ids_to_run)} QAOA-selected tests...")
    r = requests.post(f"{BASE}/tests/execute", json={"app_id": app_id, "test_case_ids": test_ids_to_run}, timeout=300)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        exec_data = r.json()
        exec_id = exec_data["id"]
        print(f"  Execution #{exec_id} started. Polling for completion...")
        
        for attempt in range(60):
            time.sleep(5)
            r2 = requests.get(f"{BASE}/executions/{exec_id}")
            if r2.status_code == 200:
                ed = r2.json()
                print(f"    [{attempt*5}s] status={ed['status']} passed={ed.get('passed',0)} failed={ed.get('failed',0)} progress={ed.get('progress_percent',0)}%")
                if ed["status"] in ("completed", "error"):
                    break
        
        # Final results
        r3 = requests.get(f"{BASE}/results?app_id={app_id}")
        if r3.status_code == 200:
            results = r3.json()
            print(f"\n  FINAL RESULTS:")
            print(f"    Status: {results.get('status')}")
            print(f"    Total: {results.get('total_tests')}")
            print(f"    Passed: {results.get('passed')}")
            print(f"    Failed: {results.get('failed')}")
    else:
        print(f"  FAILED: {r.text[:300]}")
else:
    print(f"  No QAOA-selected tests to execute")

step("PIPELINE TEST COMPLETE")
