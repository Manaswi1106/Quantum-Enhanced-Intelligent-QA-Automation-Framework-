import os
from playwright.sync_api import sync_playwright

output_dir = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(output_dir, exist_ok=True)

routes = [
    ("/", "overview"),
    ("/applications", "applications"),
    ("/test-cases", "test_cases"),
    ("/execution", "execution"),
    ("/optimization", "optimization"),
    ("/history", "history"),
    ("/results", "results"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    
    for path, name in routes:
        page = context.new_page()
        page_errors = []
        console_errors = []
        
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        url = f"http://localhost:5174{path}"
        print(f"\n==========================================")
        print(f"VERIFYING: {name.upper()} ({url})")
        print(f"==========================================")
        
        try:
            resp = page.goto(url, wait_until="networkidle", timeout=10000)
            page.wait_for_timeout(1000)
            status = resp.status if resp else "no-resp"
            print(f"HTTP Status: {status}")
        except Exception as e:
            print(f"Navigation error: {e}")
            
        # Check DOM structure
        h1 = page.evaluate('() => document.querySelector("h1")?.innerText')
        body_text = page.evaluate('() => document.body.innerText')
        card_count = page.evaluate("() => document.querySelectorAll('div').length")
        
        print(f"Header (H1): '{h1}'")
        print(f"Body text preview: {body_text[:120].strip()}...")
        print(f"Interactive UI containers count: {card_count}")
        
        screenshot_path = os.path.join(output_dir, f"{name}.png")
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved: {screenshot_path}")
        
        if page_errors:
            print("  [ERROR] Page Errors detected:")
            for e in page_errors:
                print(f"    - {e}")
        else:
            print("  [PASS] Zero Page Errors!")
            
        if console_errors:
            print("  [WARN] Console Errors:")
            for ce in console_errors:
                print(f"    - {ce}")
        else:
            print("  [PASS] Zero Console Errors!")
            
        page.close()
        
    browser.close()
print("\nAll route verifications complete.")
