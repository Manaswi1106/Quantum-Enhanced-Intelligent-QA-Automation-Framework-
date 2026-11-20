from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://qc-e-com-1.vercel.app', wait_until='networkidle')
    print('Initial URL:', page.url)
    
    # Click Products link
    page.locator("a[href='/products']").first.click()
    page.wait_for_timeout(1000)
    print('After clicking Products, URL:', page.url)
    print('Inputs on Products page:', len(page.query_selector_all('input')))
    print('Buttons on Products page:', len(page.query_selector_all('button')))

    # Let's inspect all inputs and buttons on this page
    inputs = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('input, select, textarea')).map(i => ({
            name: i.name, placeholder: i.placeholder, type: i.type, id: i.id
        }));
    }''')
    print('Inputs:', inputs)

    buttons = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('button')).map(b => (b.textContent || '').trim()).filter(Boolean);
    }''')
    print('Buttons count:', len(buttons), 'Sample:', buttons[:10])

    browser.close()
