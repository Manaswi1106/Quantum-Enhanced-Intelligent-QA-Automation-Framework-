from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://qc-e-com-1.vercel.app', wait_until='networkidle')
    
    links = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('a')).map(a => ({
            href: a.href,
            raw_href: a.getAttribute('href'),
            text: (a.textContent || '').trim()
        }));
    }''')
    print("ALL A LINKS:", len(links))
    for l in links:
        print("  Link:", l)

    buttons = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('button')).map(b => ({
            text: (b.textContent || '').trim(),
            onclick: b.getAttribute('onclick'),
            className: b.className
        }));
    }''')
    print("\nALL BUTTONS:", len(buttons))
    for b in buttons:
        print("  Button:", b)
        
    inputs = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('input, textarea, select')).map(i => ({
            tag: i.tagName,
            type: i.type,
            name: i.name,
            placeholder: i.placeholder,
            id: i.id
        }));
    }''')
    print("\nALL INPUTS:", len(inputs))
    for i in inputs:
        print("  Input:", i)

    # Check products or cards rendered
    cards = page.evaluate('''() => {
        return document.querySelectorAll('.product-card, [data-testid*="product"], .card, article').length;
    }''')
    print("\nProduct cards count:", cards)
    
    body_html_len = len(page.content())
    print("\nPage HTML length:", body_html_len)
    
    browser.close()
