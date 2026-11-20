"""Check /api/ai/status through the backend directly."""
import requests

r = requests.get("http://127.0.0.1:8001/api/ai/status")
print("Status code:", r.status_code)
print("Response JSON:", r.json())
