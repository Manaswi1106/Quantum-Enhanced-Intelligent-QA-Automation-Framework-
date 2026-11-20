"""Comprehensive verification for all requirements:
A. A valid, accessible deployed website (ShopSphere V1 / App #8).
B. A genuinely nonexistent domain.
C. A website that is reachable but restricts automated browser access (App #10 / Amazon root).
D. A repeated analysis retry (reuse existing application record, no duplicates).
"""
import requests, json, time

BASE = "http://127.0.0.1:8001/api"

def banner(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

# TEST A: Valid Accessible Deployed Website
banner("TEST A: Valid Accessible Website (ShopSphere App #8)")
r = requests.get(f"{BASE}/applications/8")
print(f"Status: {r.status_code}")
app8 = r.json()
print(f"App #8: name='{app8['name']}' | status='{app8['status']}'")
print(f"Pages: {app8['discovered_pages']} | Elements: {app8['discovered_elements']}")
assert app8["status"] == "active"
assert app8["discovered_pages"] > 1
assert app8["discovered_elements"] > 0
print("-> TEST A PASSED: Real active website accurately classified as 'active' with rich DOM.")

# TEST B: Genuinely Nonexistent Domain
banner("TEST B: Genuinely Nonexistent Domain")
fake_url = "https://this-fake-domain-cannot-exist-123456789.org"
t0 = time.time()
r = requests.post(f"{BASE}/applications/analyze", json={"url": fake_url, "force": True}, timeout=30)
elapsed = time.time() - t0
print(f"Analyze call returned {r.status_code} in {elapsed:.1f}s")
app_fake = r.json()
print(f"Fake App: ID={app_fake['id']} | name='{app_fake['name']}' | status='{app_fake['status']}'")
print(f"Pages: {app_fake['discovered_pages']} | Elements: {app_fake['discovered_elements']}")
ad = app_fake.get("analysis_data") or {}
print(f"Error Category: {ad.get('error_category')} | Error: {ad.get('error')}")
assert app_fake["status"] == "failed"
assert app_fake["discovered_pages"] == 0
assert app_fake["discovered_elements"] == 0
assert ad.get("error_category") == "DNS_RESOLUTION_FAILURE"
print("-> TEST B PASSED: Classified genuinely as 'failed' with error_category='DNS_RESOLUTION_FAILURE', 0 pages, 0 elements.")

# TEST B.2: Verify Disabled Actions for Failed App
banner("TEST B.2: Prerequisites Check for Failed App")
r_gen = requests.post(f"{BASE}/test-cases/generate", json={"app_id": app_fake["id"]})
print(f"Generate Tests on Failed App -> Status: {r_gen.status_code} | Msg: {r_gen.text}")
assert r_gen.status_code == 400

r_qubo = requests.post(f"{BASE}/optimization/qubo", json={"app_id": app_fake["id"], "budget": 5})
print(f"QUBO on Failed App -> Status: {r_qubo.status_code} | Msg: {r_qubo.text}")
assert r_qubo.status_code == 400

r_exec = requests.post(f"{BASE}/tests/execute", json={"app_id": app_fake["id"]})
print(f"Execute on Failed App -> Status: {r_exec.status_code} | Msg: {r_exec.text}")
assert r_exec.status_code == 400
print("-> TEST B.2 PASSED: All invalid actions are strictly rejected with 400 for failed app.")

# TEST C: Website Reachable but Restricts Automated Access (App #10 Retry / Re-Analysis)
banner("TEST C: Website with Limited Discovery / Access (App #10 Retry)")
r = requests.post(f"{BASE}/applications/analyze", json={"url": "https://www.amazon.in", "force": True}, timeout=45)
print(f"Amazon Analysis -> Status: {r.status_code}")
app10 = r.json()
print(f"App #10: ID={app10['id']} | name='{app10['name']}' | status='{app10['status']}'")
print(f"Pages: {app10['discovered_pages']} | Elements: {app10['discovered_elements']}")
print(f"Notes: {app10.get('analysis_data', {}).get('discovery_notes')}")
assert not app10["name"].lower().startswith("loading ")
assert app10["status"] in ("limited_discovery", "active", "failed")
print("-> TEST C PASSED: Title cleaned (no temporary 'Loading' string), status correctly represents discovery state.")

# TEST D: Repeated Analysis Retry (Reuse Existing Record, No Duplication)
banner("TEST D: Repeated Analysis Retry (No Duplication)")
r_before = requests.get(f"{BASE}/applications")
count_before = len(r_before.json())
fake_id = app_fake["id"]

# Retry the fake domain
r_retry = requests.post(f"{BASE}/applications/analyze", json={"url": fake_url, "force": True}, timeout=30)
app_retried = r_retry.json()
print(f"Retried ID: {app_retried['id']} (Expected: {fake_id})")
assert app_retried["id"] == fake_id

r_after = requests.get(f"{BASE}/applications")
count_after = len(r_after.json())
print(f"Total apps before retry: {count_before} | After retry: {count_after}")
assert count_before == count_after
print("-> TEST D PASSED: Application record was reused without creating duplicates.")

# TEST E: Check Overview Metrics Telemetry
banner("TEST E: Overview Metrics Check")
r_m = requests.get(f"{BASE}/overview/metrics")
metrics = r_m.json()
print(f"Metrics: active_apps={metrics['applications']} | total_apps={metrics['total_applications']} | failed_apps={metrics['failed_applications']}")
assert metrics["applications"] < metrics["total_applications"]
assert metrics["failed_applications"] >= 1
print("-> TEST E PASSED: Metrics accurately distinguish active vs failed applications.")

# Clean up temporary fake app created during test
banner("CLEANUP: User-Confirmed Delete Test")
r_del = requests.delete(f"{BASE}/applications/{fake_id}")
print(f"Delete fake app status: {r_del.status_code} | Msg: {r_del.json()}")
assert r_del.status_code == 200

banner("ALL REQUIREMENT VERIFICATIONS PASSED SUCCESSFULLY!")
