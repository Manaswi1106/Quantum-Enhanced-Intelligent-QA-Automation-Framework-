import json
import logging
from app.test_engine.discovery import analyze_website_sync
from app.ai.test_generation import generate_tests_from_context, get_ai_status

logging.basicConfig(level=logging.INFO)

print("=== AI STATUS ===")
status = get_ai_status()
print(status)

print("\n=== RUNNING DISCOVERY ON SHOPSPHERE ===")
discovery_data = analyze_website_sync("https://qc-e-com-1.vercel.app")
print(f"Pages: {len(discovery_data['pages'])}, Buttons: {len(discovery_data['buttons'])}, Inputs: {len(discovery_data['inputs'])}, Forms: {len(discovery_data['forms'])}")

app_context = {
    "url": "https://qc-e-com-1.vercel.app",
    "name": discovery_data.get("title", "ShopSphere"),
    "pages": discovery_data["pages"],
    "buttons": discovery_data["buttons"],
    "inputs": discovery_data["inputs"],
    "forms": discovery_data["forms"],
    "links": discovery_data.get("links", []),
}

print("\n=== GENERATING TESTS VIA AI ===")
raw_tests, provider, is_ai = generate_tests_from_context(app_context)
print(f"Provider: {provider}, is_ai: {is_ai}, Total raw validated tests: {len(raw_tests)}")
for i, t in enumerate(raw_tests, 1):
    print(f" {i}. [{t.get('priority')}] {t.get('name')} -> Route: {t.get('target_route')}")
    print(f"    Steps: {t.get('steps')[:2]}...")
    print(f"    Expected: {t.get('expected_result')}")
