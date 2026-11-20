import asyncio
from playwright.async_api import async_playwright

PAGES = [
    ("overview", "http://localhost:5174/"),
    ("applications", "http://localhost:5174/applications"),
    ("test_cases", "http://localhost:5174/test-cases"),
    ("execution", "http://localhost:5174/execution"),
    ("optimization", "http://localhost:5174/qaoa"),
    ("history", "http://localhost:5174/history"),
    ("results", "http://localhost:5174/results"),
]

ARTIFACT_DIR = r"C:\Users\ganji\.gemini\antigravity\brain\34bb79c0-fec1-4c7d-a181-8723c6107987"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        
        errors = []
        page.on("console", lambda msg: print(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(str(err)))

        for name, url in PAGES:
            print(f"Navigating to {name}: {url}")
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(1000)
            screenshot_path = f"{ARTIFACT_DIR}\\{name}.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"Saved screenshot: {screenshot_path}")

        await browser.close()
        if errors:
            print(f"Page errors encountered: {errors}")
        else:
            print("All pages rendered cleanly with 0 runtime errors!")

if __name__ == "__main__":
    asyncio.run(main())
