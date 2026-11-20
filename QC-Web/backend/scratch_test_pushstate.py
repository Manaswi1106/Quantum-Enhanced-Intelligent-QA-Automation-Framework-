from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://qc-e-com-1.vercel.app', wait_until='networkidle')
    print('Home URL:', page.url)

    # Test popstate pushState
    page.evaluate('''() => {
        window.history.pushState({}, '', '/products');
        window.dispatchEvent(new PopStateEvent('popstate'));
    }''')
    page.wait_for_timeout(800)
    print('After pushState /products, URL:', page.url)
    print('Inputs count:', len(page.query_selector_all('input')))
    print('Buttons count:', len(page.query_selector_all('button')))

    browser.close()
