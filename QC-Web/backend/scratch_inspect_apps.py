"""Inspect all current applications in the database and their analysis data."""
import requests, json

BASE = "http://127.0.0.1:8001/api"
r = requests.get(f"{BASE}/applications")
apps = r.json()
print(f"Total apps in database: {len(apps)}")
for a in apps:
    print("="*60)
    print(f"App #{a['id']}: name='{a['name']}' | status='{a['status']}'")
    print(f"  URL: {a['url']}")
    print(f"  Pages: {a.get('discovered_pages', 0)} | Elements: {a.get('discovered_elements', 0)}")
    ad = a.get('analysis_data') or {}
    print(f"  Reachable: {ad.get('reachable')} | Error: {ad.get('error')}")
    print(f"  Notes: {ad.get('discovery_notes')}")
