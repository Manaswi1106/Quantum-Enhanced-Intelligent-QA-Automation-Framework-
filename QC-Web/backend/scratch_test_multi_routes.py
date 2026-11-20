from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://qc-e-com-1.vercel.app', wait_until='networkidle')

    routes_to_test = ['/products', '/cart', '/login', '/orders', '/products/1']
    for r in routes_to_test:
        loc = page.locator(f"a[href='{r}']").first
        if loc.count() > 0:
            loc.click()
            page.wait_for_timeout(800)
            print(f"Navigated to {r} -> Current URL: {page.url}, Inputs: {len(page.query_selector_all('input'))}, Buttons: {len(page.query_selector_all('button'))}")
            # print forms
            forms = page.query_selector_all('form')
            print(f"  Forms on {r}: {len(forms)}")
        else:
            print(f"Link {r} not found on current page")
    browser.close()
