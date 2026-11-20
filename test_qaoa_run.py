import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.goto('http://localhost:5174/qaoa?app_id=3', wait_until='networkidle')
        await page.wait_for_timeout(1000)
        
        run_btn = page.locator('button:has-text("Run QAOA Optimization")')
        count = await run_btn.count()
        print(f"Buttons found: {count}")
        if count > 0:
            await run_btn.first.click()
            print("Clicked Run QAOA. Waiting for Qiskit Aer simulation...")
            await page.wait_for_timeout(8000)
            await page.screenshot(path=r'C:\Users\ganji\.gemini\antigravity\brain\34bb79c0-fec1-4c7d-a181-8723c6107987\optimization_app3_executed.png')
            print("Saved screenshot.")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
