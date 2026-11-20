"""QC-Web Full E2E Verification — Clean database, real discovery, functional tests."""
import urllib.request
import json
import time

BASE = "http://localhost:8000/api"
RESULTS = {}

def api(method, path, data=None, timeout=300):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data is not None else (b"{}" if method == "POST" else None)
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())

def poll_execution(exec_id, timeout=600):
    """Poll execution until completed, return final result."""
    start = time.time()
    while time.time() - start < timeout:
        d = api("GET", f"/executions/{exec_id}")
        completed = d.get("passed", 0) + d.get("failed", 0) + d.get("skipped", 0)
        total = d.get("total", 0)
        pct = int(completed / total * 100) if total > 0 else 0
        print(f"    Progress: {completed}/{total} ({pct}%) - {d['status']}")
        if d["status"] in ("completed", "error"):
            return d
        time.sleep(3)
    raise Exception("Execution timeout")

def check(name, fn):
    try:
        fn()
        RESULTS[name] = "PASS"
        print(f"  [PASS] {name}")
    except Exception as e:
        RESULTS[name] = f"FAIL: {e}"
        print(f"  [FAIL] {name}: {e}")

# ===== 1. RESET =====
print("\n=== 1. RESET ===")
def test_reset():
    d = api("POST", "/reset")
    assert d["status"] == "clean"
    apps = api("GET", "/applications")
    assert len(apps) == 0, f"Expected 0 apps, got {len(apps)}"
check("RESET", test_reset)

# ===== 2. ANALYSIS =====
print("\n=== 2. APPLICATION ANALYSIS ===")
app_data = None
app_id = None
def test_analysis():
    global app_data, app_id
    print("    Analyzing http://localhost:5173 (takes ~15-30s)...")
    d = api("POST", "/applications/analyze", {"url": "http://localhost:5173"}, timeout=300)
    app_data = d
    app_id = d["id"]
    assert d["status"] == "active", f"Status: {d['status']}"
    assert d["discovered_pages"] > 0, f"Pages: {d['discovered_pages']}"
    assert d["discovered_elements"] > 0, f"Elements: {d['discovered_elements']}"
    print(f"    App ID: {app_id}")
    print(f"    Name: {d['name']}")
    print(f"    Pages: {d['discovered_pages']}")
    print(f"    Elements: {d['discovered_elements']}")
    ad = d.get("analysis_data", {})
    print(f"    Buttons: {len(ad.get('buttons', []))}")
    print(f"    Inputs: {len(ad.get('inputs', []))}")
    print(f"    Forms: {len(ad.get('forms', []))}")
check("APPLICATION_ANALYSIS", test_analysis)

# ===== 3. REAL DISCOVERY DATA =====
print("\n=== 3. REAL DISCOVERY DATA ===")
def test_discovery_data():
    ad = app_data.get("analysis_data", {})
    inputs = ad.get("inputs", [])
    buttons = ad.get("buttons", [])
    all_str = json.dumps(inputs + buttons).lower()
    found = {}
    found["login"] = "login" in all_str or "email" in all_str
    found["search"] = "search" in all_str
    found["cart"] = "cart" in all_str or "add" in all_str
    found["checkout"] = "checkout" in all_str or "phone" in all_str or "address" in all_str
    found["payment"] = "card" in all_str or "payment" in all_str or "cvv" in all_str
    for key, val in found.items():
        print(f"    {key}: {'YES' if val else 'NO'}")
    assert found["login"], "Login not discovered"
    assert found["search"], "Search not discovered"
check("REAL_DISCOVERY_DATA", test_discovery_data)

# ===== 4. TEST GENERATION =====
print("\n=== 4. FUNCTIONAL TEST GENERATION ===")
def test_generation():
    d = api("POST", "/test-cases/generate", {"app_id": app_id})
    print(f"    Generated {len(d)} test cases:")
    func = 0
    for t in d:
        kind = "FUNC" if "smoke" not in t["name"].lower() else "SMOKE"
        if kind == "FUNC": func += 1
        print(f"      [{kind}] {t['test_id']}: {t['name']} (p={t['priority']}, r={t['risk']})")
    assert func >= 5, f"Expected >= 5 functional, got {func}"
check("FUNCTIONAL_TEST_GENERATION", test_generation)

# ===== 5. DEDUPLICATION =====
print("\n=== 5. DUPLICATE PREVENTION ===")
def test_dedup():
    before = len(api("GET", f"/test-cases?app_id={app_id}"))
    api("POST", "/test-cases/generate", {"app_id": app_id})
    after = len(api("GET", f"/test-cases?app_id={app_id}"))
    print(f"    Before: {before}, After 2nd: {after}")
    assert after == before, f"Duplicates! {before} -> {after}"
check("DUPLICATE_PREVENTION", test_dedup)

# ===== 6. PLAYWRIGHT EXECUTION =====
print("\n=== 6. PLAYWRIGHT EXECUTION ===")
exec_data = None
def test_playwright():
    global exec_data
    print("    Starting Playwright (background, polling progress)...")
    d = api("POST", "/tests/execute", {"app_id": app_id}, timeout=30)
    exec_id = d["id"]
    print(f"    Execution #{exec_id} started (total={d['total']})")
    d = poll_execution(exec_id, timeout=600)
    exec_data = d
    print(f"    FINAL: Total={d['total']}, Passed={d['passed']}, Failed={d['failed']}")
    for r in d.get("results", []):
        icon = "PASS" if r["status"] == "passed" else "FAIL"
        print(f"      [{icon}] {r['test_id']}: {r['test_name']} ({r['duration_ms']}ms)")
        if r.get("error_message"):
            print(f"             {r['error_message'][:150]}")
    if d["failed"] > 0:
        print(f"    ** {d['failed']} E-Com 1 defects detected **")
check("PLAYWRIGHT", test_playwright)

# ===== 7. EXECUTION PROGRESS =====
print("\n=== 7. EXECUTION PROGRESS ===")
def test_progress():
    assert exec_data is not None
    total = exec_data["total"]
    completed = exec_data["passed"] + exec_data["failed"] + exec_data.get("skipped", 0)
    assert completed == total, f"Not all completed: {completed}/{total}"
    assert exec_data["status"] == "completed"
check("EXECUTION_PROGRESS", test_progress)

# ===== 8. QUBO =====
print("\n=== 8. QUBO ===")
def test_qubo():
    d = api("POST", "/optimization/qubo", {"app_id": app_id, "budget": 5})
    assert d["num_variables"] > 0
    print(f"    QUBO: {d['num_variables']}x{d['num_variables']}, Budget={d['budget']}")
check("QUBO", test_qubo)

# ===== 9. QAOA =====
print("\n=== 9. QAOA ===")
qaoa_selected = []
def test_qaoa():
    global qaoa_selected
    d = api("POST", "/optimization/qaoa", {"app_id": app_id, "budget": 5, "p": 1, "shots": 512}, timeout=300)
    assert len(d["selected_tests"]) > 0
    qaoa_selected = d["selected_tests"]
    meta = d.get("metadata", {})
    print(f"    Selected: {len(d['selected_tests'])}, Excluded: {len(d['excluded_tests'])}")
    print(f"    Objective: {d['objective_value']:.4f}")
    print(f"    Simulator: {meta.get('simulator')}, Method: {meta.get('method')}")
    if d.get("selected_details"):
        for t in d["selected_details"]:
            print(f"      -> {t['test_id']}: {t['name']}")
check("QAOA", test_qaoa)

# ===== 10. QAOA -> PLAYWRIGHT =====
print("\n=== 10. QAOA -> PLAYWRIGHT ===")
def test_qaoa_pw():
    tc_all = api("GET", f"/test-cases?app_id={app_id}")
    selected_ids = [t["id"] for t in tc_all if t["status"] == "selected"]
    assert len(selected_ids) > 0, "No QAOA-selected tests"
    print(f"    Executing {len(selected_ids)} QAOA-selected tests...")
    d = api("POST", "/tests/execute", {"app_id": app_id, "test_case_ids": selected_ids}, timeout=30)
    d = poll_execution(d["id"], timeout=600)
    assert d["total"] == len(selected_ids)
    print(f"    Result: {d['passed']} passed, {d['failed']} failed out of {d['total']}")
check("QAOA_PLAYWRIGHT", test_qaoa_pw)

# ===== 11. HISTORY =====
print("\n=== 11. HISTORY ===")
def test_history():
    d = api("GET", "/history")
    assert len(d) > 0
    dist = {}
    for h in d:
        s = h["status"]
        dist[s] = dist.get(s, 0) + 1
    print(f"    Entries: {len(d)}, Distribution: {dist}")
check("HISTORY", test_history)

# ===== 12. RESULTS =====
print("\n=== 12. RESULTS ===")
def test_results():
    d = api("GET", f"/results?app_id={app_id}")
    assert d["total_tests"] > 0
    print(f"    Status: {d['status']}, Total: {d['total_tests']}, P={d['passed']}, F={d['failed']}")
check("RESULTS", test_results)

# ===== 13. ADAPTIVE FEEDBACK =====
print("\n=== 13. ADAPTIVE FEEDBACK ===")
def test_adaptive():
    tc = api("GET", f"/test-cases?app_id={app_id}")
    with_hist = [t for t in tc if t["historical_runs"] > 0]
    print(f"    Tests with history: {len(with_hist)}")
    for t in with_hist[:5]:
        print(f"      {t['test_id']}: runs={t['historical_runs']}, fail_rate={t['failure_rate']:.2f}")
check("ADAPTIVE_FEEDBACK", test_adaptive)

# ===== SUMMARY =====
print("\n" + "=" * 60)
print("QC-WEB VERIFICATION REPORT")
print("=" * 60)
all_pass = True
for name, result in RESULTS.items():
    if result != "PASS":
        all_pass = False
    print(f"  {name}: {result}")
print("=" * 60)
print("ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED")
print("=" * 60)
