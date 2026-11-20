"""AI-driven website discovery engine using Playwright.
Crawls dynamic web applications (both MPA and client-side SPAs), detects routes, forms,
buttons, inputs, and interactive elements.
Zero application-specific hardcoding: dynamically discovers structure from ANY target website.
"""
import logging
import time
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def classify_discovery_error(err_str: str) -> str:
    """Classify network/discovery errors based on actual evidence."""
    err_lower = (err_str or "").lower()
    if any(k in err_lower for k in ["getaddrinfo", "err_name_not_resolved", "nodename nor servname", "dns"]):
        return "DNS_RESOLUTION_FAILURE"
    if any(k in err_lower for k in ["timeout", "timed out", "navigation timeout"]):
        return "TIMEOUT"
    if any(k in err_lower for k in ["cert", "ssl", "tls", "err_cert"]):
        return "TLS_SSL_FAILURE"
    if any(k in err_lower for k in ["err_connection_refused", "connection refused"]):
        return "CONNECTION_REFUSED"
    if any(k in err_lower for k in ["403", "401", "forbidden", "unauthorized", "err_http2_protocol_error", "blocked", "captcha", "access denied"]):
        return "ACCESS_RESTRICTED"
    if any(k in err_lower for k in ["404", "not found"]):
        return "HTTP_404_NOT_FOUND"
    if any(k in err_lower for k in ["500", "502", "503", "504", "server error"]):
        return "HTTP_SERVER_ERROR"
    return "NETWORK_FAILURE"


def clean_discovered_title(title: str, fallback_domain: str) -> str:
    """Derive clean, readable display title removing loading artifacts."""
    if not title:
        return fallback_domain
    t = title.strip()
    # If the title is literally "Loading ..." or contains temporary loading indicator
    if t.lower().startswith("loading ") or t.lower() == "loading..." or t.lower() == "loading":
        return fallback_domain
    if len(t) < 2:
        return fallback_domain
    return t


def analyze_website_sync(url: str, max_pages: int = 20, max_depth: int = 2) -> dict:
    """Intelligently crawl and analyze any web application using Playwright.

    Discovers pages, forms, inputs, buttons, navigation, and interactive elements
    without assuming any hardcoded knowledge of the target site.
    Supports SPAs, dynamic hydration, same-origin filtering, and bounded execution.
    """
    start_time = time.time()
    max_crawl_duration_sec = 60.0

    base_url_parsed = urlparse(url)
    base_domain = base_url_parsed.netloc.lower() or url
    base_scheme = base_url_parsed.scheme or "https"

    result = {
        "title": base_domain,
        "favicon": "",
        "reachable": False,
        "base_url": url,
        "final_url": url,
        "pages": [],
        "forms": [],
        "links": [],
        "buttons": [],
        "inputs": [],
        "interactive_elements": 0,
        "context_status": "insufficient",
        "discovery_notes": "",
        "crawl_duration_ms": 0,
        "error": None,
        "error_category": None,
    }

    visited_paths = set()
    paths_to_visit = [("/", 0)]
    all_links = set()

    all_buttons = []
    all_inputs = []
    all_forms = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = context.new_page()
            # Remove automated browser fingerprints to prevent false anti-bot blocks
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            # 1. First load: Base URL / Homepage
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Bounded wait for dynamic client-side rendering / hydration
                page.wait_for_timeout(800)

                # Check if DOM body has rendered content
                element_count = page.evaluate("() => document.body ? document.body.querySelectorAll('*').length : 0")
                if element_count < 5:
                    try:
                        page.wait_for_load_state("load", timeout=3000)
                    except Exception:
                        pass

                result["final_url"] = page.url
                raw_title = page.title() or ""
                result["title"] = clean_discovered_title(raw_title, base_domain)

                if response:
                    result["reachable"] = response.status < 500
                else:
                    result["reachable"] = True
                logger.info(f"Connected to {url} via Playwright. Final URL: {result['final_url']} (Title: {result['title']})")
            except Exception as e:
                logger.warning(f"Direct Playwright navigation encountered {e}; trying HTTP fallback...")
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        }
                    )
                    with urllib.request.urlopen(req, timeout=12) as r:
                        html = r.read().decode("utf-8", errors="ignore")
                    page.set_content(html, wait_until="domcontentloaded")
                    page.wait_for_timeout(800)
                    result["reachable"] = True
                    raw_title = page.title() or ""
                    result["title"] = clean_discovered_title(raw_title, base_domain)
                    logger.info(f"Connected to {url} via resilient HTTP fallback. Title: {result['title']}")
                except Exception as fallback_err:
                    err_msg = str(fallback_err)
                    cat = classify_discovery_error(err_msg)
                    logger.error(f"Failed to reach URL {url} via both Chromium and fallback ({cat}): {err_msg}")
                    result["error"] = err_msg
                    result["error_category"] = cat
                    result["reachable"] = False
                    result["title"] = base_domain
                    result["discovery_notes"] = f"Target website is unreachable or offline [{cat}]: {err_msg}"
                    result["crawl_duration_ms"] = int((time.time() - start_time) * 1000)
                    return result

            # Detect favicon
            try:
                favicon = page.evaluate('''() => {
                    const icon = document.querySelector('link[rel~="icon"], link[rel="shortcut icon"]');
                    return icon ? icon.href : null;
                }''')
                result["favicon"] = favicon or f"{base_scheme}://{base_domain}/favicon.ico"
            except Exception:
                result["favicon"] = ""

            # Check if homepage body is completely empty (e.g. anti-bot 202 or empty document)
            body_text_len = page.evaluate("() => document.body ? document.body.innerText.trim().length : 0")
            initial_elem_count = page.evaluate("() => document.body ? document.body.querySelectorAll('*').length : 0")
            if initial_elem_count == 0 or body_text_len == 0:
                logger.warning(f"Target at {url} rendered an empty document body ({initial_elem_count} elements, {body_text_len} text chars).")
                result["discovery_notes"] = "Page rendered an empty document body or access was restricted."

            # Discover internal links from homepage
            def extract_page_links():
                try:
                    return page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.href)
                            .filter(href => href && !href.startsWith('javascript:') && !href.startsWith('mailto:') && !href.startsWith('tel:'));
                    }''')
                except Exception:
                    return []

            for href in extract_page_links():
                try:
                    p_href = urlparse(href)
                    if p_href.netloc.lower() == base_domain or not p_href.netloc:
                        p_path = (p_href.path or "/").rstrip("/") or "/"
                        all_links.add(p_path)
                        if p_path not in visited_paths and p_path not in [p for p, _ in paths_to_visit]:
                            paths_to_visit.append((p_path, 1))
                except Exception:
                    continue

            # 2. Controlled crawl across discovered internal routes
            while paths_to_visit and len(visited_paths) < max_pages:
                if (time.time() - start_time) > max_crawl_duration_sec:
                    logger.info("Reached maximum crawl duration bound; wrapping up discovery.")
                    break

                current_path, current_depth = paths_to_visit.pop(0)
                if current_path in visited_paths:
                    continue

                visited_paths.add(current_path)
                full_page_url = urljoin(url.rstrip("/") + "/", current_path.lstrip("/"))

                # Route navigation: SPA-first + direct fallback
                if current_path != "/":
                    nav_ok = False
                    # A. Try clicking visible in-page anchor (smooth SPA navigation)
                    try:
                        link_locator = page.locator(
                            f"a[href='{current_path}'], a[href='{current_path}/'], a[href='{full_page_url}']"
                        ).first
                        if link_locator.count() > 0:
                            link_locator.click(timeout=2500)
                            page.wait_for_timeout(600)
                            nav_ok = True
                    except Exception:
                        nav_ok = False

                    # B. If link click did not work, try direct page.goto
                    if not nav_ok:
                        try:
                            resp = page.goto(full_page_url, wait_until="domcontentloaded", timeout=10000)
                            if resp and resp.status < 400:
                                page.wait_for_timeout(400)
                                nav_ok = True
                            elif resp and resp.status == 404:
                                # Client-side SPA route without server rewrites: load base and pushState
                                page.goto(url, wait_until="domcontentloaded", timeout=10000)
                                page.wait_for_timeout(300)
                                page.evaluate(f'''(p) => {{
                                    window.history.pushState({{}}, '', p);
                                    window.dispatchEvent(new PopStateEvent('popstate'));
                                }}''', current_path)
                                page.wait_for_timeout(600)
                                nav_ok = True
                        except Exception as nav_e:
                            logger.debug(f"Direct route navigation for {current_path} failed: {nav_e}")

                    if not nav_ok:
                        continue

                page_title = page.title() or current_path

                # Extract headings / key visible text for contextual grounding
                page_meta = page.evaluate('''() => {
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
                        .map(h => (h.textContent || '').trim())
                        .filter(t => t.length > 0 && t.length < 80)
                        .slice(0, 5);
                    const snippet = document.body ? (document.body.innerText || '').slice(0, 300).replace(/\\s+/g, ' ').trim() : '';
                    return { headings, snippet };
                }''')

                # A. Extract Interactive Buttons, Links & Navigation CTA
                buttons_data = page.evaluate('''(path) => {
                    const elements = Array.from(document.querySelectorAll(
                        'button, input[type="button"], input[type="submit"], [role="button"], a.btn, a.button, nav a, header a, [role="tab"], [role="menuitem"]'
                    ));
                    return elements.slice(0, 50).map(b => ({
                        testid: b.getAttribute('data-testid') || null,
                        text: (b.textContent || b.value || b.getAttribute('aria-label') || '').trim(),
                        id: b.id || null,
                        aria_label: b.getAttribute('aria-label') || null,
                        type: b.getAttribute('type') || (b.tagName === 'A' ? 'link' : 'button'),
                        page: path
                    })).filter(b => (b.text && b.text.length < 50) || b.testid || b.id || b.aria_label);
                }''', current_path)

                # B. Extract Inputs, Textareas, Selects & Labels
                inputs_data = page.evaluate('''(path) => {
                    const fields = Array.from(document.querySelectorAll(
                        'input:not([type="hidden"]):not([type="button"]):not([type="submit"]), textarea, select'
                    ));
                    return fields.slice(0, 30).map(i => {
                        let labelText = null;
                        if (i.id) {
                            const lbl = document.querySelector(`label[for="${i.id}"]`);
                            if (lbl) labelText = (lbl.textContent || '').trim();
                        }
                        if (!labelText && i.closest('label')) {
                            labelText = (i.closest('label').textContent || '').trim();
                        }
                        return {
                            testid: i.getAttribute('data-testid') || null,
                            name: i.name || null,
                            type: i.type || i.tagName.toLowerCase(),
                            placeholder: i.placeholder || null,
                            aria_label: i.getAttribute('aria-label') || null,
                            label: labelText,
                            id: i.id || null,
                            required: i.required || false,
                            page: path
                        };
                    });
                }''', current_path)

                # C. Extract Forms
                forms_data = page.evaluate('''(path) => {
                    return Array.from(document.querySelectorAll('form')).map(f => {
                        const formInputs = Array.from(f.querySelectorAll('input:not([type="hidden"]), textarea, select'))
                            .map(i => i.getAttribute('data-testid') || i.name || i.id || i.type || 'input');
                        return {
                            action: f.getAttribute('action') || path,
                            method: (f.getAttribute('method') || 'POST').toUpperCase(),
                            fields: formInputs,
                            page: path
                        };
                    });
                }''', current_path)

                result["pages"].append({
                    "url": full_page_url,
                    "title": page_title,
                    "path": current_path,
                    "headings": page_meta.get("headings", []),
                    "snippet": page_meta.get("snippet", "")[:150],
                    "buttons_count": len(buttons_data),
                    "inputs_count": len(inputs_data),
                    "forms_count": len(forms_data),
                })

                all_buttons.extend(buttons_data)
                all_inputs.extend(inputs_data)
                all_forms.extend(forms_data)

                # Expand queue from newly discovered links
                if current_depth < max_depth and len(visited_paths) < max_pages:
                    for h in extract_page_links():
                        try:
                            p_href = urlparse(h)
                            if p_href.netloc.lower() == base_domain or not p_href.netloc:
                                p_path = (p_href.path or "/").rstrip("/") or "/"
                                all_links.add(p_path)
                                if p_path not in visited_paths and p_path not in [p for p, _ in paths_to_visit]:
                                    paths_to_visit.append((p_path, current_depth + 1))
                        except Exception:
                            pass

        # Browser is safely closed by sync_playwright context manager when exiting with block
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Playwright discovery exception: {err_msg}")
        result["error"] = err_msg
        result["error_category"] = classify_discovery_error(err_msg)
        if not result["discovery_notes"]:
            result["discovery_notes"] = f"Discovery encountered browser exception [{result['error_category']}]: {err_msg}"

    # Deduplicate buttons and inputs
    unique_buttons = []
    seen_b = set()
    for b in all_buttons:
        sig = (b.get("testid"), b.get("text"), b.get("page"))
        if sig not in seen_b:
            seen_b.add(sig)
            unique_buttons.append(b)

    unique_inputs = []
    seen_i = set()
    for i in all_inputs:
        sig = (i.get("testid"), i.get("name"), i.get("placeholder"), i.get("page"))
        if sig not in seen_i:
            seen_i.add(sig)
            unique_inputs.append(i)

    result["buttons"] = unique_buttons
    result["inputs"] = unique_inputs
    result["forms"] = all_forms
    result["links"] = list(all_links)[:50]
    result["interactive_elements"] = len(unique_buttons) + len(unique_inputs) + len(all_forms)
    result["crawl_duration_ms"] = int((time.time() - start_time) * 1000)

    # Determine context sufficiency honestly based on actual findings
    if result["interactive_elements"] == 0 and len(result["pages"]) <= 1:
        result["context_status"] = "insufficient"
        if not result["discovery_notes"]:
            result["discovery_notes"] = (
                "The current discovery extracted insufficient usable website context "
                "(empty document body or restricted access), so only verified sanity "
                "or connectivity testing can be safely executed."
            )
    else:
        result["context_status"] = "sufficient"
        if not result["discovery_notes"]:
            result["discovery_notes"] = (
                f"Discovered {len(result['pages'])} routes and {result['interactive_elements']} "
                "interactive UI surfaces."
            )

    logger.info(
        f"Discovery finished for {url}: {len(result['pages'])} pages, "
        f"{len(result['buttons'])} buttons, {len(result['inputs'])} inputs, "
        f"{len(all_forms)} forms ({result['interactive_elements']} total interactive elements, "
        f"Status: {result['context_status']})."
    )

    return result
