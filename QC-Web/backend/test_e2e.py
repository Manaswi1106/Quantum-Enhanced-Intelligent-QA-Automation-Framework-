import urllib.request
import json

def api_call(method, path, data=None):
    url = f"http://localhost:8000/api{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    if method == "GET" and body:
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=120)
    return json.loads(r.read())

# Test 1: Generate test cases
print("=== TEST GENERATION ===")
tests = api_call("POST", "/test-cases/generate", {"app_id": 1})
print(f"Generated {len(tests)} test cases")
for t in tests:
    print(f"  {t['test_id']}: {t['name']} [{t['priority']}]")

# Test 2: List test cases
print("\n=== LIST TEST CASES ===")
all_tests = api_call("GET", "/test-cases?app_id=1")
print(f"Total test cases: {len(all_tests)}")

# Test 3: Execute all tests
print("\n=== EXECUTING TESTS ===")
print("Running Playwright against E-Com 1...")
result = api_call("POST", "/tests/execute", {"app_id": 1})
print(f"Status: {result['status']}")
print(f"Total: {result['total']}, Passed: {result['passed']}, Failed: {result['failed']}")
print("\nResults:")
for r in result.get("results", []):
    status_icon = "✅" if r["status"] == "passed" else "❌" if r["status"] == "failed" else "⚠️"
    print(f"  {status_icon} {r['test_id']}: {r['test_name']} - {r['status']} ({r['duration_ms']}ms)")
    if r.get("error_message"):
        print(f"     Error: {r['error_message'][:120]}")

# Test 4: Get results
print("\n=== RESULTS ===")
results = api_call("GET", "/results?app_id=1")
print(f"Status: {results['status']}")
print(f"Total: {results['total_tests']}, Passed: {results['passed']}, Failed: {results['failed']}")
if results.get("recommendations"):
    print("Recommendations:")
    for rec in results["recommendations"]:
        print(f"  - {rec[:120]}")

# Test 5: Get history
print("\n=== HISTORY ===")
history = api_call("GET", "/history")
print(f"History entries: {len(history)}")

print("\n=== ALL E2E TESTS COMPLETE ===")
