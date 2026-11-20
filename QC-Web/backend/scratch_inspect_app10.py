"""Inspect App 10 full analysis_data."""
import requests, json

BASE = "http://127.0.0.1:8001/api"
r = requests.get(f"{BASE}/applications/10")
print(r.json())
