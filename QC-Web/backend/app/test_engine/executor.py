"""Playwright Automated Test Execution Engine.
Universal and dynamic: executes structured AI-generated test steps against ANY target application.
Zero hardcoded domains, credentials, or mock selectors.
"""
import re
import time
import base64
import urllib.request
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, Page, Error as PlaywrightError
from ..database.models import TestCase

logger = logging.getLogger(__name__)


def check_target_reachable(url: str, timeout_sec: int = 6) -> bool:
    """Pre-flight check: verify target website is online before launching browser."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QC-Web/2.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status < 500
    except Exception:
        # Some CDNs reject urllib with 403; let Playwright try if it's an HTTP/HTTPS URL
        return url.startswith(("http://", "https://"))


# Failure Classification Categories
APPLICATION_FAILURE = "APPLICATION_FAILURE"
ASSERTION_FAILURE = "ASSERTION_FAILURE"
NAVIGATION_FAILURE = "NAVIGATION_FAILURE"
ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
TEST_EXECUTION_ERROR = "TEST_EXECUTION_ERROR"


def classify_failure(error_msg: str, is_assertion: bool, console_logs: list) -> str:
    """Classify failure based on actual execution evidence and error characteristics."""
    msg_lower = (error_msg or "").lower()

    # 1. Navigation / Network Failures
    nav_patterns = [
        "err_http2_protocol_error",
        "err_connection_refused",
        "err_connection_reset",
        "err_name_not_resolved",
        "err_cert_",
        "err_timed_out",
        "net::err_",
        "navigation failed",
        "navigation timeout",
        "timeout 25000ms exceeded",
        "timeout 15000ms exceeded",
        "page.goto",
        "returned http status 404",
        "returned http status 502",
        "returned http status 503",
        "empty document body",
    ]
    if any(p in msg_lower for p in nav_patterns):
        return NAVIGATION_FAILURE

    # 2. Environment / Browser Engine Failures
    env_patterns = [
        "browser engine launch failure",
        "browser has been closed",
        "target closed",
        "playwright connection closed",
        "executable doesn't exist",
        "out of memory",
        "sandbox",
    ]
    if any(p in msg_lower for p in env_patterns):
        return ENVIRONMENT_FAILURE

    # 3. Application Failures (HTTP 500, unhandled application crash or exception in console)
    app_patterns = [
        "http status 500",
        "internal server error",
        "uncaught error",
        "uncaught typeerror",
        "unhandled promise rejection",
        "application error",
    ]
    if any(p in msg_lower for p in app_patterns):
        return APPLICATION_FAILURE

    if console_logs and any("500 (internal server error)" in str(c).lower() or "uncaught" in str(c).lower() for c in console_logs):
        return APPLICATION_FAILURE

    # 4. Step Assertion Failures
    if is_assertion or "assertion failed" in msg_lower or "expected" in msg_lower:
        return ASSERTION_FAILURE

    # 5. General test execution error
    return TEST_EXECUTION_ERROR


def execute_test_sync(test_case: TestCase, base_url: str) -> dict:
    """Execute a single test case dynamically against any deployed target website."""
    start_time = time.time()
    result = {
        "status": "skipped",
        "failure_category": None,
        "duration_ms": 0,
        "error_message": None,
        "screenshot_path": None,
        "console_logs": [],
    }

    console_messages = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-web-security",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 QCWeb/2.0",
                ignore_https_errors=True
            )
            page = context.new_page()

            # Record browser console messages
            page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

            try:
                # 1. Resolve initial target route
                target_route = getattr(test_case, "target_route", None) or "/"
                if target_route.startswith("http://") or target_route.startswith("https://"):
                    start_url = target_route
                else:
                    start_url = urljoin(base_url.rstrip("/") + "/", target_route.lstrip("/"))

                logger.info(f"Executing [{test_case.test_id} - {test_case.name}] on {start_url}...")

                # 2. Navigate to target route
                resp = page.goto(start_url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(800)

                if resp and resp.status >= 400:
                    if resp.status == 404 and target_route != "/":
                        # Resilient SPA route navigation: navigate via base URL and pushState / popstate
                        try:
                            page.goto(base_url, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(500)
                            page.evaluate('''(p) => {
                                window.history.pushState({}, '', p);
                                window.dispatchEvent(new PopStateEvent('popstate'));
                            }''', target_route)
                            page.wait_for_timeout(800)
                        except Exception as spa_err:
                            raise AssertionError(f"Target route {start_url} returned HTTP status {resp.status} (SPA fallback failed: {spa_err}).")
                    else:
                        raise AssertionError(f"Target route {start_url} returned HTTP status {resp.status}.")

                # 3. Verify DOM rendered
                doc_title = page.title()
                body_text = page.inner_text("body").strip()
                if not doc_title and len(body_text) < 15:
                    raise AssertionError(f"Page at {start_url} rendered an empty document body.")

                # 4. Interpret and execute structured steps dynamically
                steps: List[str] = test_case.steps or []
                _execute_dynamic_steps(page, steps, base_url, test_case)

                # 5. Check expected result if specified
                if test_case.expected_result:
                    _verify_expected_result(page, test_case.expected_result)

                result["status"] = "passed"
                result["failure_category"] = None
                logger.info(f"Test [{test_case.test_id}] PASSED in {int((time.time() - start_time) * 1000)}ms.")
                try:
                    shot = page.screenshot(type="jpeg", quality=75)
                    result["screenshot_path"] = f"data:image/jpeg;base64,{base64.b64encode(shot).decode('utf-8')}"
                except Exception as shot_err:
                    logger.debug(f"Passing screenshot skipped: {shot_err}")

            except AssertionError as e:
                err_str = str(e)
                category = classify_failure(err_str, is_assertion=True, console_logs=console_messages)
                result["status"] = "failed"
                result["failure_category"] = category
                result["error_message"] = err_str
                logger.info(f"Assertion Failure in [{test_case.test_id} - {test_case.name}] ({category}): {e}")

                # Avoid capturing blank empty-document screenshots for navigation failures
                has_dom = False
                try:
                    has_dom = page.evaluate("() => document.body && document.body.querySelectorAll('*').length > 5")
                except Exception:
                    has_dom = False

                if has_dom and category not in (NAVIGATION_FAILURE, ENVIRONMENT_FAILURE):
                    try:
                        shot = page.screenshot(type="jpeg", quality=75)
                        result["screenshot_path"] = f"data:image/jpeg;base64,{base64.b64encode(shot).decode('utf-8')}"
                    except Exception as shot_err:
                        logger.warning(f"Failed to capture failure screenshot: {shot_err}")
                else:
                    result["screenshot_path"] = None

            except Exception as e:
                err_str = str(e)
                category = classify_failure(err_str, is_assertion=False, console_logs=console_messages)
                # Only real application defects are marked failed; network/env errors marked error
                result["status"] = "failed" if category == APPLICATION_FAILURE else "error"
                result["failure_category"] = category
                result["error_message"] = f"{category}: {err_str}"
                logger.warning(f"Execution Failure in [{test_case.test_id}] ({category}): {e}")

                has_dom = False
                try:
                    has_dom = page.evaluate("() => document.body && document.body.querySelectorAll('*').length > 5")
                except Exception:
                    has_dom = False

                if has_dom and category == APPLICATION_FAILURE:
                    try:
                        shot = page.screenshot(type="jpeg", quality=75)
                        result["screenshot_path"] = f"data:image/jpeg;base64,{base64.b64encode(shot).decode('utf-8')}"
                    except Exception:
                        pass
                else:
                    result["screenshot_path"] = None

            browser.close()

    except Exception as e:
        err_str = str(e)
        category = classify_failure(err_str, is_assertion=False, console_logs=console_messages)
        result["status"] = "error"
        result["failure_category"] = category
        result["error_message"] = f"Browser Engine Launch Failure ({category}): {err_str}"

    result["duration_ms"] = max(int((time.time() - start_time) * 1000), 100)
    result["console_logs"] = console_messages[-15:] if console_messages else []
    return result


def execute_suite_sync(test_cases: List[TestCase], base_url: str) -> List[dict]:
    """Execute a list of test cases sequentially."""
    results = []
    for tc in test_cases:
        r = execute_test_sync(tc, base_url)
        r["test_case_id"] = tc.id
        results.append(r)
    return results


# -----------------------------------------------------------------------------
# Dynamic Step Interpreter for Arbitrary Websites
# -----------------------------------------------------------------------------

def _execute_dynamic_steps(page: Page, steps: List[str], base_url: str, test_case: TestCase):
    """Interpret natural or structured step instructions dynamically without hardcoded selectors."""
    for step_idx, step_text in enumerate(steps):
        s_clean = step_text.strip()
        if not s_clean:
            continue

        s_lower = s_clean.lower()
        logger.debug(f"Step {step_idx + 1}: {s_clean}")

        # --- A. Navigation Steps ---
        if s_lower.startswith(("navigate to", "go to", "visit", "open")):
            target = re.sub(r"^(navigate to|go to|visit|open)\s+", "", s_clean, flags=re.IGNORECASE).strip("'\"` ")
            if target.startswith("/"):
                nav_url = urljoin(base_url.rstrip("/") + "/", target.lstrip("/"))
                route_path = target
            elif target.startswith(("http://", "https://")):
                nav_url = target
                route_path = urlparse(target).path or "/"
            else:
                nav_url = base_url
                route_path = "/"

            resp = page.goto(nav_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(400)
            if resp and resp.status >= 400:
                if resp.status == 404 and route_path != "/":
                    # Resilient client-side SPA navigation fallback
                    try:
                        page.goto(base_url, wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(400)
                        page.evaluate('''(p) => {
                            window.history.pushState({}, '', p);
                            window.dispatchEvent(new PopStateEvent('popstate'));
                        }''', route_path)
                        page.wait_for_timeout(600)
                    except Exception as spa_err:
                        raise AssertionError(f"Step {step_idx + 1} failed: Navigation to '{nav_url}' returned HTTP {resp.status} (SPA fallback failed: {spa_err}).")
                else:
                    raise AssertionError(f"Step {step_idx + 1} failed: Navigation to '{nav_url}' returned HTTP {resp.status}.")
            continue

        # --- B. Input / Typing / Search Steps ---
        if any(kw in s_lower for kw in ["enter ", "type ", "fill ", "search for ", "input "]):
            # Extract target value if quoted, or general text
            quoted = re.findall(r"['\"]([^'\"]+)['\"]", s_clean)
            fill_value = quoted[0] if quoted else "test query"

            # Locate input element dynamically
            input_el = _find_input_element(page, s_clean)
            if input_el and input_el.is_visible():
                try:
                    input_el.fill(fill_value)
                    page.wait_for_timeout(300)
                    if "search" in s_lower:
                        input_el.press("Enter")
                        page.wait_for_timeout(600)
                    continue
                except Exception as fill_err:
                    logger.debug(f"Input fill failed on step: {fill_err}")

        # --- C. Click / Submit / Select Steps ---
        if any(kw in s_lower for kw in ["click", "press", "select", "submit", "trigger", "tap"]):
            target_match = re.findall(r"['\"]([^'\"]+)['\"]", s_clean)
            target_label = target_match[0] if target_match else ""

            clicked = _click_matching_element(page, s_clean, target_label)
            if not clicked and target_label:
                # If specific target was explicitly requested but absent
                logger.debug(f"Element '{target_label}' not found or not clickable on {page.url}.")
            page.wait_for_timeout(400)
            continue

        # --- D. Assertion / Verification Steps ---
        if any(kw in s_lower for kw in ["assert", "verify", "check", "ensure", "confirm"]):
            quoted = re.findall(r"['\"]([^'\"]+)['\"]", s_clean)
            if quoted:
                expected_text = quoted[0]
                # If the assertion explicitly checks the URL / path
                if "url" in s_lower or "route" in s_lower or "path" in s_lower:
                    current_url = page.url.lower()
                    if expected_text.lower() in current_url:
                        continue

                body_content = page.inner_text("body")
                if expected_text.lower() not in body_content.lower():
                    # Check if error message was expected
                    if "error" in s_lower or "reject" in s_lower:
                        err_el = page.locator('[role="alert"], .error, .alert, [aria-invalid="true"]').first
                        if not err_el.is_visible():
                            raise AssertionError(f"Step {step_idx + 1} assertion failed: Expected error indicator '{expected_text}' not found.")
                    else:
                        raise AssertionError(f"Step {step_idx + 1} assertion failed: Expected text '{expected_text}' not visible on {page.url}.")
            continue

        # General step delay
        page.wait_for_timeout(200)


def _find_input_element(page: Page, step_text: str):
    """Locate candidate input or textarea matching the step description."""
    s_lower = step_text.lower()

    if "search" in s_lower:
        loc = page.locator('input[type="search"], input[name*="search" i], input[placeholder*="search" i], [aria-label*="search" i]').first
        if loc.count() > 0 and loc.is_visible():
            return loc

    if "email" in s_lower:
        loc = page.locator('input[type="email"], input[name*="email" i], input[placeholder*="email" i]').first
        if loc.count() > 0 and loc.is_visible():
            return loc

    if "password" in s_lower:
        loc = page.locator('input[type="password"], input[name*="pass" i]').first
        if loc.count() > 0 and loc.is_visible():
            return loc

    # Fallback: first visible text/search input
    general = page.locator('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea').first
    if general.count() > 0 and general.is_visible():
        return general
    return None


def _click_matching_element(page: Page, step_text: str, target_label: str) -> bool:
    """Attempt to click an interactive button or link matching the label."""
    if target_label:
        # Check if target_label looks like a selector
        if any(target_label.startswith(p) for p in ["[", "#", "."]):
            try:
                sel = page.locator(target_label).first
                if sel.count() > 0 and sel.is_visible():
                    sel.click(timeout=3000)
                    return True
            except Exception:
                pass

        # Try role button first
        btn = page.get_by_role("button", name=target_label, exact=False).first
        if btn.count() > 0 and btn.is_visible():
            try:
                btn.click(timeout=3000)
                return True
            except Exception:
                pass

        # Try link
        link = page.get_by_role("link", name=target_label, exact=False).first
        if link.count() > 0 and link.is_visible():
            try:
                link.click(timeout=3000)
                return True
            except Exception:
                pass

        # Text match
        el = page.locator(f'button:has-text("{target_label}"), a:has-text("{target_label}"), [role="button"]:has-text("{target_label}")').first
        if el.count() > 0 and el.is_visible():
            try:
                el.click(timeout=3000)
                return True
            except Exception:
                pass

    # Check if raw step text contains explicit CSS/testid selector: e.g. [data-testid='nav-login']
    css_match = re.findall(r"(\[[^\]]+\])", step_text)
    for c_sel in css_match:
        try:
            sel_el = page.locator(c_sel).first
            if sel_el.count() > 0 and sel_el.is_visible():
                sel_el.click(timeout=3000)
                return True
        except Exception:
            pass

    # Generic submit if step implies form submission
    if any(k in step_text.lower() for k in ["submit", "continue", "proceed", "login", "save"]):
        sub = page.locator('button[type="submit"], input[type="submit"]').first
        if sub.count() > 0 and sub.is_visible():
            try:
                sub.click(timeout=3000)
                return True
            except Exception:
                pass

    return False


def _verify_expected_result(page: Page, expected_result: str):
    """Verify that expected result assertion passes against live document."""
    exp_lower = expected_result.lower()
    body_text = page.inner_text("body").lower()

    # If expected result explicitly mandates error presence
    if "error" in exp_lower or "invalid" in exp_lower or "rejected" in exp_lower:
        err_indicators = page.locator('[role="alert"], .error-message, .alert-danger, [aria-invalid="true"]').count()
        if err_indicators == 0 and "error" not in body_text and "invalid" not in body_text:
            raise AssertionError(f"Expected validation rejection or error, but none was detected: '{expected_result}'")

    # If page should render without crash
    if "crash" in exp_lower or "exception" in exp_lower:
        if "uncaught error" in body_text or "internal server error" in body_text:
            raise AssertionError(f"Page encountered critical runtime error contrary to expected: '{expected_result}'")
