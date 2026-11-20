"""Inspect screenshot for TC-073 in execution 12."""
import requests, base64

BASE = "http://127.0.0.1:8001/api"
r = requests.get(f"{BASE}/executions/12")
data = r.json()
for res in data.get("results", []):
    if res.get("test_id") == "TC-073":
        sc = res.get("screenshot_path")
        print("Test:", res.get("test_id"), "Error:", res.get("error_message"))
        print("Screenshot starts with:", sc[:50] if sc else None)
        if sc and sc.startswith("data:image/jpeg;base64,"):
            b64_data = sc.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_data)
            print("Decoded image bytes length:", len(raw_bytes))
            # Save to disk to inspect size and whether it's blank or not
            with open("D:/QC_Project/QC-Web/backend/scratch_tc073_shot.jpg", "wb") as f:
                f.write(raw_bytes)
            print("Saved to scratch_tc073_shot.jpg")
