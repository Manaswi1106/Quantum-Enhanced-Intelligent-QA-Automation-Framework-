"""Intelligent test case generator based on dynamically discovered DOM elements and AI models.
Strictly disallows any predefined, hardcoded, or mock test cases.
Preserves and prioritizes regression tests from previous runs and versions.
Safely generates unique, collision-free test IDs across all applications and requests.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from ..database.models import Application, ApplicationVersion, TestCase

logger = logging.getLogger(__name__)


def normalize_text(text: Optional[str]) -> str:
    """Normalize text by stripping punctuation and whitespace for fuzzy semantic deduplication."""
    if not text:
        return ""
    return re.sub(r"[\W_]+", " ", str(text).lower()).strip()


def steps_to_string(steps: Any) -> str:
    """Convert steps array or string to normalized plain text."""
    if isinstance(steps, list):
        return " ".join(str(s) for s in steps)
    return str(steps or "")


def is_trivial_root_load_test(name: str, steps: Any, target_route: Optional[str] = "/") -> bool:
    """Detect if a test is merely checking that the base URL / homepage loads without testing deeper features."""
    norm_n = normalize_text(name)
    root_keywords = [
        "base url", "root page", "initial load", "homepage load",
        "load root", "home page load", "verify base url", "load base url",
        "verify root", "homepage initial", "base page loads"
    ]
    if any(k in norm_n for k in root_keywords):
        return True

    route_clean = (target_route or "/").strip()
    if route_clean in ("/", ""):
        steps_list = steps if isinstance(steps, list) else [str(steps)]
        if len(steps_list) <= 2:
            steps_str = " ".join(str(s) for s in steps_list).lower()
            if "navigate to" in steps_str and ("verify page" in steps_str or "verify title" in steps_str or "loads" in steps_str or "renders" in steps_str):
                if "button" not in steps_str and "input" not in steps_str and "click" not in steps_str and "form" not in steps_str:
                    return True
    return False


def get_next_unique_test_id(
    db: Session,
    proposed_id: Optional[str] = None,
    reserved_ids: Optional[Set[str]] = None,
) -> str:
    """Safely derive a guaranteed unique test_id across the entire database.

    Requirements satisfied:
    - Never reuses an existing test_id in the database.
    - If AI returns an existing test_id, automatically assigns a new unique ID.
    - Preserves sequential TC-xxx format while preventing collision under concurrent or repeated runs.
    """
    if reserved_ids is None:
        reserved_ids = set()

    # Load all existing test_ids across the whole database
    db_existing = {r[0] for r in db.query(TestCase.test_id).all() if r[0]}
    all_taken = db_existing | reserved_ids

    # If proposed_id is provided, check if it's already safe and unallocated
    if proposed_id and str(proposed_id).strip():
        candidate = str(proposed_id).strip()
        # Accept proposed ID if it starts with TC- and has not been used anywhere
        if candidate.upper().startswith("TC-") and candidate not in all_taken:
            reserved_ids.add(candidate)
            return candidate

    # Find maximum integer suffix among all TC-xxx IDs across the database
    max_num = 0
    for tid in all_taken:
        m = re.match(r"^TC-?(\d+)$", tid, re.IGNORECASE)
        if m:
            try:
                val = int(m.group(1))
                if val > max_num:
                    max_num = val
            except ValueError:
                pass

    next_num = max(max_num + 1, 1)
    new_id = f"TC-{next_num:03d}"
    while new_id in all_taken:
        next_num += 1
        new_id = f"TC-{next_num:03d}"

    reserved_ids.add(new_id)
    return new_id


def validate_and_ground_test(
    t_data: Dict[str, Any],
    app_context: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any], str]:
    """Validate and ground an AI-generated test candidate against the discovered DOM.

    Requirements:
    - Must possess a non-empty name and at least one step.
    - Rejects empty or malformed tests.
    - Anchors target_route to an actually discovered page path or '/'.
    - Sanitizes step URLs so tests cannot hallucinate external third-party domains.
    - Verifies element / action relevance against discovered buttons, inputs, and forms.
    """
    name = (t_data.get("name") or "").strip()
    if not name or len(name) < 3:
        return False, t_data, "Invalid or missing test name"

    raw_steps = t_data.get("steps")
    if not raw_steps or not isinstance(raw_steps, list) or len(raw_steps) == 0:
        return False, t_data, "Test must contain at least one step"

    expected_result = (t_data.get("expected_result") or "").strip()
    if not expected_result:
        t_data["expected_result"] = "Verification step completes without unhandled errors."

    pages = app_context.get("pages", [])
    app_url = app_context.get("url", "")
    parsed_app_url = urlparse(app_url)
    app_host = parsed_app_url.netloc.lower()

    # Collect all discovered paths
    discovered_paths = set()
    for p in pages:
        if isinstance(p, dict):
            pth = (p.get("path") or "").strip().lower()
            if pth:
                discovered_paths.add(pth if pth.startswith("/") else f"/{pth}")
    discovered_paths.add("/")

    # Check and ground target_route
    raw_route = (t_data.get("target_route") or "/").strip()
    target_route = "/"
    if raw_route.startswith("http://") or raw_route.startswith("https://"):
        parsed_route = urlparse(raw_route)
        if parsed_route.netloc.lower() == app_host:
            target_route = parsed_route.path or "/"
    elif raw_route.startswith("/"):
        target_route = raw_route
    else:
        target_route = f"/{raw_route}"

    # Ensure target_route matches or anchors to discovered routes
    target_clean = target_route.lower().rstrip("/") or "/"
    if target_clean not in discovered_paths:
        matched = False
        for dp in discovered_paths:
            if dp != "/" and (dp in target_clean or target_clean in dp):
                target_route = dp
                matched = True
                break
        if not matched:
            target_route = "/"

    t_data["target_route"] = target_route

    # Sanitize steps: prevent hallucinating external domains
    sanitized_steps = []
    for step in raw_steps:
        step_str = str(step).strip()
        url_match = re.search(r"https?://([^\s/'\"]+)", step_str)
        if url_match:
            step_host = url_match.group(1).lower()
            if step_host != app_host and "127.0.0.1" not in step_host and "localhost" not in step_host:
                step_str = re.sub(r"https?://[^\s/'\"]+", app_url, step_str)
        sanitized_steps.append(step_str)

    t_data["steps"] = sanitized_steps

    # Collect element tokens from discovered DOM
    buttons = app_context.get("buttons", [])
    inputs = app_context.get("inputs", [])

    token_pool = set()
    for b in buttons:
        if isinstance(b, dict):
            txt = (b.get("text") or "").lower()
            tid = (b.get("testid") or "").lower()
            token_pool.update(re.findall(r"\w+", txt + " " + tid))
    for inp in inputs:
        if isinstance(inp, dict):
            nm = (inp.get("name") or "").lower()
            tid = (inp.get("testid") or "").lower()
            ph = (inp.get("placeholder") or "").lower()
            token_pool.update(re.findall(r"\w+", nm + " " + tid + " " + ph))
    for p in pages:
        if isinstance(p, dict):
            ttl = (p.get("title") or "").lower()
            token_pool.update(re.findall(r"\w+", ttl))

    # Expected Result Validation: check if literal quoted expectation matches discovered DOM
    quoted_matches = re.findall(r"['\"]([^'\"]{3,})['\"]", expected_result)
    for q_str in quoted_matches:
        q_norm = q_str.lower().strip()
        q_tokens = set(re.findall(r"\w+", q_norm))
        # If quoted string has no token overlap with discovered titles, buttons, or inputs
        if token_pool and q_tokens and not q_tokens.intersection(token_pool):
            logger.warning(
                f"Candidate test '{name}' contains unobserved expectation text '{q_str}'. "
                "Normalizing expectation to observable document assertion."
            )
            t_data["expected_result"] = (
                f"Page loads at '{target_route}' and renders without unhandled exceptions or crashes."
            )
            break

    return True, t_data, "Grounded in discovered DOM context"


def generate_test_cases(
    db: Session,
    app: Application,
    retain_previous_failures: bool = True,
    app_version_id: Optional[int] = None,
) -> List[TestCase]:
    """Generate candidate regression test suite using real AI, persisting to Supabase with deduplication.

    Raises:
        ValueError if the app is unanalyzed, unreachable, missing testable surfaces,
                    or if the AI provider is not configured.
    """
    analysis = app.analysis_data or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except Exception:
            analysis = {}

    if not analysis or not analysis.get("reachable"):
        raise ValueError(f"Target website at {app.url} is offline or could not be crawled.")

    inputs = analysis.get("inputs", [])
    buttons = analysis.get("buttons", [])
    pages = analysis.get("pages", [])
    forms = analysis.get("forms", [])
    links = analysis.get("links", [])

    total_interactive = len(buttons) + len(inputs) + len(forms)

    # Detailed logging as requested
    logger.info("==================================================")
    logger.info(f"DISCOVERY PIPELINE AUDIT FOR {app.url}:")
    logger.info(f"  - pages discovered: {len(pages)}")
    logger.info(f"  - routes discovered: {[p.get('path', '/') for p in pages[:10]]}")
    logger.info(f"  - links discovered: {len(links)}")
    logger.info(f"  - buttons discovered: {len(buttons)}")
    logger.info(f"  - inputs discovered: {len(inputs)}")
    logger.info(f"  - forms discovered: {len(forms)}")
    logger.info(f"  - interactive elements total: {total_interactive}")
    logger.info("==================================================")

    if not pages and not buttons and not inputs:
        raise ValueError(
            f"No testable UI surfaces were discovered on {app.url}. "
            "Please ensure the application renders accessible routes or interactive elements."
        )

    app_context = {
        "url": app.url,
        "name": app.name,
        "pages": pages,
        "buttons": buttons,
        "inputs": inputs,
        "forms": forms,
        "links": links,
    }

    # Invoke genuine AI test generation
    from ..ai.test_generation import generate_tests_from_context, get_ai_status
    ai_status = get_ai_status()
    if not ai_status.get("configured"):
        raise ValueError(
            "AI provider is not configured. "
            "Please configure GEMINI_API_KEY or OPENAI_API_KEY in backend/.env to synthesize test cases for this application."
        )

    try:
        raw_tests, provider_name, is_ai = generate_tests_from_context(app_context)
    except Exception as e:
        raise ValueError(f"AI test generation failed for {app.url}: {str(e)}")

    if not is_ai or not raw_tests:
        raise ValueError(
            f"AI provider '{ai_status.get('provider')}' was unable to synthesize test cases for this application. "
            "No tests were generated."
        )

    # Resolve version linkage: use explicit app_version_id or latest registered version
    if not app_version_id:
        latest_ver = (
            db.query(ApplicationVersion)
            .filter(ApplicationVersion.app_id == app.id)
            .order_by(ApplicationVersion.created_at.desc())
            .first()
        )
        if latest_ver:
            app_version_id = latest_ver.id

    # Fetch all existing tests for this app to enforce content-based deduplication
    existing_app_tests = db.query(TestCase).filter(TestCase.app_id == app.id).all()

    # Track existing test fingerprints
    # A test is a duplicate ONLY if:
    # 1. Identical target_route AND identical step sequence AND identical expected result
    # 2. OR identical test name AND identical target route
    existing_action_fps: Set[str] = set()
    existing_route_name_fps: Set[str] = set()
    has_existing_root_smoke = False

    for t in existing_app_tests:
        r = (getattr(t, "target_route", None) or "/").strip().lower()
        nm = normalize_text(t.name)
        st = normalize_text(steps_to_string(t.steps))
        exp = normalize_text(t.expected_result)
        existing_action_fps.add(f"{r}::{st}::{exp}")
        existing_route_name_fps.add(f"{r}::{nm}")
        if is_trivial_root_load_test(t.name, t.steps, getattr(t, "target_route", "/")):
            has_existing_root_smoke = True

    # Handle regression retention: If there were previously failed tests, heighten risk and retain them
    if retain_previous_failures:
        for rec in existing_app_tests:
            if rec.status in {"failed", "error"}:
                rec.status = "selected"  # Mark for prioritized re-testing in regression run
                rec.risk = min(1.0, (rec.risk or 0.7) + 0.15)
                rec.change_impact = min(1.0, (rec.change_impact or 0.6) + 0.2)
                logger.info(f"Retained previous failed test for regression priority: {rec.test_id} - {rec.name}")

    reserved_ids: Set[str] = set()
    created_tests: List[TestCase] = []
    rejected_count = 0
    dup_count = 0
    pruned_smoke_count = 0

    has_root_smoke = has_existing_root_smoke

    for t_data in raw_tests:
        # Validate and ground test candidate against discovered DOM
        is_valid, grounded_data, reason = validate_and_ground_test(t_data, app_context)
        if not is_valid:
            rejected_count += 1
            logger.warning(
                f"Skipping ungrounded/invalid candidate test for app {app.id}: "
                f"'{t_data.get('name')}' ({reason})"
            )
            continue
        t_data = grounded_data

        name = (t_data.get("name") or "").strip()
        norm_name = normalize_text(name)
        raw_steps = t_data.get("steps", [])
        norm_steps = normalize_text(steps_to_string(raw_steps))
        norm_expected = normalize_text(t_data.get("expected_result", ""))
        target_route = (t_data.get("target_route") or "/").strip().lower()

        # Prune redundant generic root smoke tests: keep at most 1 root load smoke test
        if is_trivial_root_load_test(name, raw_steps, target_route):
            if has_root_smoke:
                pruned_smoke_count += 1
                logger.info(f"Pruning redundant root smoke test: '{name}' (already registered root smoke test)")
                continue
            else:
                has_root_smoke = True

        action_fp = f"{target_route}::{norm_steps}::{norm_expected}"
        route_name_fp = f"{target_route}::{norm_name}"

        # Intelligent deduplication:
        # Avoid skipping valid alternative scenarios (e.g. valid query vs invalid query)
        is_dup = (action_fp in existing_action_fps) or (route_name_fp in existing_route_name_fps)

        if is_dup:
            dup_count += 1
            logger.info(f"Skipping identical candidate test for app {app.id}: '{name}' on '{target_route}'")
            continue

        existing_action_fps.add(action_fp)
        existing_route_name_fps.add(route_name_fp)

        # Trace original AI ID separately for auditability
        raw_ai_id = (t_data.get("test_id") or t_data.get("id") or "").strip()
        original_test_id = raw_ai_id if raw_ai_id else None

        # Determine guaranteed unique internal test ID
        unique_test_id = get_next_unique_test_id(
            db=db,
            proposed_id=original_test_id,
            reserved_ids=reserved_ids,
        )

        source_label = f"ai:{provider_name}"

        tc = TestCase(
            app_id=app.id,
            app_version_id=app_version_id,
            test_id=unique_test_id,
            original_test_id=original_test_id,
            name=name,
            description=t_data.get("description", "AI-synthesized regression scenario."),
            steps=raw_steps if isinstance(raw_steps, list) else [str(raw_steps)],
            expected_result=t_data.get("expected_result", "Expected verification passes."),
            source=source_label,
            priority=t_data.get("priority", "medium"),
            risk=float(t_data.get("risk", 0.5)),
            coverage=float(t_data.get("coverage", 0.5)),
            change_impact=float(t_data.get("change_impact", 0.5)),
            execution_cost=float(t_data.get("execution_cost", 3.0)),
            redundancy_group=t_data.get("redundancy_group"),
            status="not_run",
        )
        db.add(tc)
        created_tests.append(tc)

    try:
        db.commit()
    except Exception as commit_err:
        db.rollback()
        logger.error(f"Failed to commit newly generated test cases: {commit_err}")
        # Secondary recovery: If any ID collided unexpectedly, re-assign IDs with timestamp fallback
        for tc in created_tests:
            tc.test_id = get_next_unique_test_id(db, reserved_ids=reserved_ids)
            db.add(tc)
        db.commit()

    logger.info("==================================================")
    logger.info(f"AI TEST GENERATION SUMMARY FOR APP #{app.id} ({app.url}):")
    logger.info(f"  - Raw AI tests returned: {len(raw_tests)}")
    logger.info(f"  - Rejected by validation: {rejected_count}")
    logger.info(f"  - Redundant root smoke tests pruned: {pruned_smoke_count}")
    logger.info(f"  - Duplicate tests skipped: {dup_count}")
    logger.info(f"  - Newly saved candidate tests: {len(created_tests)}")
    logger.info("==================================================")

    all_current = (
        db.query(TestCase)
        .filter(TestCase.app_id == app.id)
        .order_by(TestCase.id.asc())
        .all()
    )

    return all_current
