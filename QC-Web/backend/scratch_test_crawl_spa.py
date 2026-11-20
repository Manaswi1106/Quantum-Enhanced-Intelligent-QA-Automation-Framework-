from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urljoin
import time

url = 'https://qc-e-com-1.vercel.app'
base_domain = urlparse(url).netloc.lower()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded')
    page.wait_for_timeout(800)

    visited = set()
    queue = [url]
    discovered_pages = []
    all_buttons = []
    all_inputs = []
    all_forms = []

    while queue and len(visited) < 15:
        curr = queue.pop(0)
        norm = curr.rstrip('/')
        if norm in visited:
            continue
        visited.add(norm)
        path = urlparse(curr).path or '/'

        # Navigate
        if norm != url.rstrip('/'):
            # Try link click first if link exists
            clicked = False
            link_loc = page.locator(f"a[href='{path}'], a[href='{norm}'], a[href='{path}/']").first
            if link_loc.count() > 0:
                try:
                    link_loc.click(timeout=3000)
                    page.wait_for_timeout(600)
                    clicked = True
                except Exception:
                    clicked = False
            if not clicked:
                # Try direct goto
                try:
                    resp = page.goto(curr, wait_until='domcontentloaded', timeout=10000)
                    if resp and resp.status == 404:
                        # Fallback: go home and pushState
                        page.goto(url, wait_until='domcontentloaded')
                        page.wait_for_timeout(400)
                        page.evaluate(f'''() => {{
                            window.history.pushState({{}}, '', '{path}');
                            window.dispatchEvent(new PopStateEvent('popstate'));
                        }}''')
                        page.wait_for_timeout(600)
                except Exception:
                    continue

        title = page.title() or path
        print(f"Crawled: {path} | Title: {title} | Current page URL: {page.url}")

        # Extract elements
        buttons = page.evaluate('''(path) => {
            return Array.from(document.querySelectorAll('button, a.btn, [role="button"]')).map(b => ({
                text: (b.textContent || b.value || '').trim(),
                page: path
            })).filter(b => b.text && b.text.length < 50);
        }''', path)

        inputs = page.evaluate('''(path) => {
            return Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select')).map(i => ({
                name: i.name || null,
                placeholder: i.placeholder || null,
                type: i.type || i.tagName.toLowerCase(),
                page: path
            }));
        }''', path)

        forms = page.evaluate('''(path) => {
            return Array.from(document.querySelectorAll('form')).map(f => ({
                action: f.getAttribute('action') || path,
                fields: Array.from(f.querySelectorAll('input, select, textarea')).map(i => i.name || i.type)
            }));
        }''', path)

        print(f"  -> Buttons: {len(buttons)}, Inputs: {len(inputs)}, Forms: {len(forms)}")
        all_buttons.extend(buttons)
        all_inputs.extend(inputs)
        all_forms.extend(forms)

        discovered_pages.append({
            "url": curr,
            "path": path,
            "title": title,
            "buttons_count": len(buttons),
            "inputs_count": len(inputs),
            "forms_count": len(forms)
        })

        # Find more links
        hrefs = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(h => h && !h.startsWith('javascript:'));
        }''')
        for h in hrefs:
            p = urlparse(h)
            if p.netloc.lower() == base_domain:
                h_norm = h.split('#')[0].rstrip('/')
                if h_norm not in visited and h_norm not in queue:
                    queue.append(h_norm)

    print("\nTOTAL DISCOVERED:")
    print("Pages:", len(discovered_pages))
    print("Total Buttons:", len(all_buttons))
    print("Total Inputs:", len(all_inputs))
    print("Total Forms:", len(all_forms))
    browser.close()
