"""QC Web API Routes."""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database.db import get_db
from ..database.models import (
    Application, ApplicationVersion, TestCase, TestExecution,
    TestResult, TestHistory, OptimizationRun, DiscoveredPage, InteractiveElement,
)
from ..schemas.schemas import (
    AnalyzeRequest, ApplicationResponse, TestCaseCreate, TestCaseGenerateRequest,
    TestCaseResponse, ExecuteRequest, ExecutionResponse, TestResultResponse,
    TestHistoryResponse, OptimizationRequest, OptimizationResponse,
    ResultsResponse,
)
from ..test_engine.discovery import analyze_website_sync
from ..test_engine.executor import execute_suite_sync
from ..services.test_generator import generate_test_cases, get_next_unique_test_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ---- Helper ----
def _serialize_dt(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


# ===================== Database Reset =====================

@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    """Reset all test data. Keeps source code, deletes generated data."""
    db.query(TestHistory).delete()
    db.query(TestResult).delete()
    db.query(OptimizationRun).delete()
    db.query(TestExecution).delete()
    db.query(TestCase).delete()
    db.query(InteractiveElement).delete()
    db.query(DiscoveredPage).delete()
    db.query(ApplicationVersion).delete()
    db.query(Application).delete()
    db.commit()
    return {"message": "Database reset complete", "status": "clean"}


# ===================== Applications =====================

@router.post("/applications/analyze")
def analyze_application(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """Analyze a deployed website URL with resilient discovery and explicit status tracking."""
    url = req.url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")

    from urllib.parse import urlparse
    parsed = urlparse(url)
    default_name = parsed.netloc.lower() or url.split("//")[-1].split("/")[0]

    # Check if already analyzed successfully with rich discovery
    existing = db.query(Application).filter(Application.url == url).first()
    force_reanalyze = getattr(req, "force", False)
    if not force_reanalyze and existing and existing.status in ("active", "limited_discovery") and existing.analysis_data and existing.discovered_pages > 1:
        return _app_to_dict(existing)

    # Use existing record or create new
    if existing:
        app = existing
        app.status = "analyzing"
        # Preserve user custom name if set, else ensure clean default domain name
        if not app.name or app.name.lower().startswith("loading ") or app.name.lower() == "loading":
            app.name = default_name
        db.commit()
    else:
        app = Application(name=default_name, url=url, status="analyzing")
        db.add(app)
        db.commit()
        db.refresh(app)

    # Run analysis (Playwright sync crawler in threadpool managed by FastAPI)
    try:
        analysis = analyze_website_sync(url)

        # Determine explicit application status based on actual evidence
        if not analysis.get("reachable"):
            app.status = "failed"
        elif analysis.get("context_status") == "insufficient" or analysis.get("interactive_elements", 0) == 0:
            app.status = "limited_discovery"
        else:
            app.status = "active"

        app.analysis_data = analysis
        app.discovered_pages = len(analysis.get("pages", []))
        app.discovered_elements = analysis.get("interactive_elements", 0)

        # Update name cleanly from observed page title (never use temporary loading labels)
        raw_title = analysis.get("title")
        if raw_title and not raw_title.lower().startswith("loading ") and raw_title.lower() != "loading":
            app.name = raw_title.strip()
        elif not app.name or app.name.lower().startswith("loading "):
            app.name = default_name

        # Create or update version
        existing_version = db.query(ApplicationVersion).filter(
            ApplicationVersion.app_id == app.id
        ).first()
        if existing_version:
            existing_version.analysis_data = analysis
        else:
            version = ApplicationVersion(
                app_id=app.id,
                version_label="v1",
                url=url,
                analysis_data=analysis,
            )
            db.add(version)

        # Persist discovered pages and interactive elements
        db.query(InteractiveElement).filter(InteractiveElement.app_id == app.id).delete()
        db.query(DiscoveredPage).filter(DiscoveredPage.app_id == app.id).delete()

        page_map = {}
        for p in analysis.get("pages", []):
            if isinstance(p, dict):
                path_val = p.get("path", "/")
                dp = DiscoveredPage(
                    app_id=app.id,
                    url=p.get("url", url),
                    path=path_val,
                    title=p.get("title", ""),
                )
                db.add(dp)
                db.flush()
                page_map[path_val] = dp.id

        for b in analysis.get("buttons", []):
            if isinstance(b, dict):
                page_path = b.get("page", "/")
                ie = InteractiveElement(
                    app_id=app.id,
                    page_id=page_map.get(page_path),
                    element_type="button",
                    testid=b.get("testid"),
                    text=b.get("text"),
                    page_path=page_path,
                )
                db.add(ie)

        for inp in analysis.get("inputs", []):
            if isinstance(inp, dict):
                page_path = inp.get("page", "/")
                ie = InteractiveElement(
                    app_id=app.id,
                    page_id=page_map.get(page_path),
                    element_type="input",
                    testid=inp.get("testid"),
                    name=inp.get("name"),
                    tag_name=inp.get("type"),
                    page_path=page_path,
                )
                db.add(ie)

        db.commit()
        db.refresh(app)

    except Exception as e:
        app.status = "failed"
        db.commit()
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")

    return _app_to_dict(app)


@router.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    apps = db.query(Application).order_by(Application.created_at.desc()).all()
    return [_app_to_dict(a) for a in apps]


@router.get("/applications/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    return _app_to_dict(app)


@router.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    """User-confirmed deletion of an application record."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    db.delete(app)
    db.commit()
    return {"message": f"Application #{app_id} deleted successfully", "id": app_id}


def _app_to_dict(app: Application) -> dict:
    return {
        "id": app.id,
        "name": app.name,
        "url": app.url,
        "status": app.status,
        "discovered_pages": app.discovered_pages,
        "discovered_elements": app.discovered_elements,
        "analysis_data": app.analysis_data,
        "created_at": _serialize_dt(app.created_at),
    }


# ===================== Test Cases =====================

@router.get("/test-cases")
def list_test_cases(app_id: int = None, db: Session = Depends(get_db)):
    query = db.query(TestCase)
    if app_id:
        query = query.filter(TestCase.app_id == app_id)
    tcs = query.order_by(TestCase.id).all()
    return [_tc_to_dict(tc, db) for tc in tcs]


@router.post("/test-cases")
def create_test_case(req: TestCaseCreate, db: Session = Depends(get_db)):
    unique_test_id = get_next_unique_test_id(db, proposed_id=getattr(req, "test_id", None))
    tc = TestCase(
        test_id=unique_test_id,
        original_test_id=getattr(req, "original_test_id", None) or unique_test_id,
        app_version_id=getattr(req, "app_version_id", None),
        name=req.name,
        description=req.description,
        steps=req.steps,
        expected_result=req.expected_result,
        source="manual",
        priority=req.priority,
        risk=req.risk,
        app_id=req.app_id,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return _tc_to_dict(tc, db)


@router.post("/test-cases/generate")
def generate_tests(req: TestCaseGenerateRequest, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == req.app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status == "failed":
        raise HTTPException(400, "Cannot generate tests for an application whose analysis failed. Complete successful discovery first.")
    if app.status == "analyzing":
        raise HTTPException(400, "Application analysis is currently in progress. Please wait for discovery to complete.")
    if not app.analysis_data:
        raise HTTPException(400, "Application has not been analyzed yet")

    try:
        generated = generate_test_cases(db, app)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Test generation error: {e}")
        raise HTTPException(500, f"Test generation failed: {str(e)}")

    return [_tc_to_dict(tc, db) for tc in generated]


def _tc_to_dict(tc: TestCase, db: Session) -> dict:
    # Calculate historical stats
    history = db.query(TestHistory).filter(TestHistory.test_case_id == tc.id).all()
    runs = len(history)
    failures = sum(1 for h in history if h.status == "failed")
    rate = failures / runs if runs > 0 else 0.0

    return {
        "id": tc.id,
        "test_id": tc.test_id,
        "original_test_id": getattr(tc, "original_test_id", None),
        "name": tc.name,
        "description": tc.description,
        "steps": tc.steps or [],
        "expected_result": tc.expected_result,
        "source": tc.source,
        "priority": tc.priority,
        "risk": tc.risk,
        "coverage": tc.coverage,
        "change_impact": tc.change_impact,
        "execution_cost": tc.execution_cost,
        "redundancy_group": tc.redundancy_group,
        "historical_runs": runs,
        "historical_failures": failures,
        "failure_rate": round(rate, 4),
        "status": tc.status,
        "app_id": tc.app_id,
        "app_version_id": getattr(tc, "app_version_id", None),
        "created_at": _serialize_dt(tc.created_at),
        "updated_at": _serialize_dt(tc.updated_at),
    }


# In-memory execution state for live UI tracking
LIVE_EXECUTION_STATE = {}


@router.get("/overview/metrics")
def get_overview_metrics(db: Session = Depends(get_db)):
    """Fetch live real-time platform metrics from Supabase database."""
    # Count applications: active and limited_discovery (exclude failed and analyzing from active application count)
    active_apps = db.query(Application).filter(Application.status.in_(["active", "limited_discovery"])).count()
    failed_apps = db.query(Application).filter(Application.status.in_(["failed", "error"])).count()
    total_apps = db.query(Application).count()

    total_tests = db.query(TestCase).count()
    total_executions = db.query(TestExecution).count()
    total_optimizations = db.query(OptimizationRun).count()

    total_results = db.query(TestResult).count()
    passed_results = db.query(TestResult).filter(TestResult.status == "passed").count()
    # Genuine application defects count towards detected_defects; infrastructure/network errors are excluded
    detected_defects = (
        db.query(TestResult)
        .filter(
            TestResult.status == "failed",
            (TestResult.failure_category.in_(["APPLICATION_FAILURE", "ASSERTION_FAILURE"])) | (TestResult.failure_category == None)
        )
        .count()
    )

    pass_rate = round((passed_results / total_results) * 100, 1) if total_results > 0 else 0.0

    return {
        "applications": active_apps,
        "total_applications": total_apps,
        "failed_applications": failed_apps,
        "generated_tests": total_tests,
        "executions": total_executions,
        "optimizations": total_optimizations,
        "detected_defects": detected_defects,
        "pass_rate": pass_rate,
    }


# ===================== Execution =====================

@router.post("/tests/execute")
async def execute_tests(req: ExecuteRequest, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == req.app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status == "failed":
        raise HTTPException(400, "Cannot execute tests for an application whose analysis failed. Complete website discovery and generate valid tests first.")
    if app.status == "analyzing":
        raise HTTPException(400, "Application analysis is currently in progress. Please wait for discovery to complete.")

    # Get test cases
    query = db.query(TestCase).filter(TestCase.app_id == req.app_id)
    if req.test_case_ids:
        query = query.filter(TestCase.id.in_(req.test_case_ids))
    test_cases = query.all()

    if not test_cases:
        raise HTTPException(400, "No test cases to execute. Complete website discovery and generate valid tests first.")

    # Pre-flight check: verify website availability
    from ..test_engine.executor import check_target_reachable
    if not check_target_reachable(app.url, timeout_sec=4):
        raise HTTPException(400, f"Website is offline or unreachable at {app.url}")

    # Create execution record
    execution = TestExecution(
        app_id=app.id,
        total=len(test_cases),
        status="running",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    exec_id = execution.id
    app_url = app.url
    tc_data = [(tc.id, tc.name, tc.steps, tc.test_id) for tc in test_cases]

    # Initialize live tracking
    LIVE_EXECUTION_STATE[exec_id] = {
        "current_test": tc_data[0][1] if tc_data else "Preparing suite...",
        "current_url": app_url,
        "stage": f"Starting 1 of {len(tc_data)}",
        "browser_status": "Launching Chromium...",
    }

    import threading

    def _run_in_background():
        _run_tests_with_progress(exec_id, app_url, tc_data)

    thread = threading.Thread(target=_run_in_background, daemon=True)
    thread.start()

    return _execution_to_dict(execution, db)


def _run_tests_with_progress(exec_id: int, app_url: str, tc_data: list):
    """Run tests one-by-one in background, updating DB after each."""
    from ..database.db import SessionLocal
    from ..test_engine.executor import execute_test_sync

    db = SessionLocal()
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == exec_id).first()
        if not execution:
            return

        passed = 0
        failed = 0
        skipped = 0
        total_tests = len(tc_data)

        for idx, (tc_id, tc_name, tc_steps, tc_test_id) in enumerate(tc_data):
            tc = db.query(TestCase).filter(TestCase.id == tc_id).first()
            if not tc:
                continue

            # Update live state
            LIVE_EXECUTION_STATE[exec_id] = {
                "current_test": tc_name,
                "current_url": app_url,
                "stage": f"Executing {idx + 1} of {total_tests}",
                "browser_status": f"Running Playwright Test [{tc_test_id}]",
            }

            execution.status = "running"
            db.commit()

            # Execute the test
            r = execute_test_sync(tc, app_url)

            # Save result
            tr = TestResult(
                execution_id=exec_id,
                test_case_id=tc_id,
                status=r["status"],
                failure_category=r.get("failure_category"),
                duration_ms=r["duration_ms"],
                error_message=r.get("error_message"),
                screenshot_path=r.get("screenshot_path"),
            )
            db.add(tr)

            # Update test case status
            tc.status = r["status"]

            # Record history
            th = TestHistory(
                test_case_id=tc_id,
                execution_id=exec_id,
                status=r["status"],
                failure_category=r.get("failure_category"),
                duration_ms=r["duration_ms"],
                failure_reason=r.get("error_message"),
            )
            db.add(th)

            if r["status"] == "passed":
                passed += 1
            elif r["status"] == "failed":
                failed += 1
            else:
                skipped += 1

            # Update execution progress in database
            execution.passed = passed
            execution.failed = failed
            execution.skipped = skipped
            db.commit()

        execution.status = "completed"
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()

        if exec_id in LIVE_EXECUTION_STATE:
            LIVE_EXECUTION_STATE[exec_id]["browser_status"] = "Completed"
            LIVE_EXECUTION_STATE[exec_id]["stage"] = f"Finished {total_tests}/{total_tests}"

    except Exception as e:
        logger.error(f"Background execution failed: {e}")
        try:
            execution = db.query(TestExecution).filter(TestExecution.id == exec_id).first()
            if execution:
                execution.status = "error"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/executions/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    ex = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    return _execution_to_dict(ex, db)


def _execution_to_dict(ex: TestExecution, db: Session) -> dict:
    results = db.query(TestResult).filter(TestResult.execution_id == ex.id).all()
    tc_ids = [r.test_case_id for r in results]
    tcs = db.query(TestCase).filter(TestCase.id.in_(tc_ids)).all() if tc_ids else []
    tc_map = {tc.id: tc for tc in tcs}

    result_list = []
    for r in results:
        tc = tc_map.get(r.test_case_id)
        result_list.append({
            "id": r.id,
            "execution_id": r.execution_id,
            "test_case_id": r.test_case_id,
            "test_id": tc.test_id if tc else "",
            "test_name": tc.name if tc else "",
            "status": r.status,
            "failure_category": getattr(r, "failure_category", None),
            "duration_ms": r.duration_ms,
            "error_message": r.error_message,
            "screenshot_path": r.screenshot_path,
            "created_at": _serialize_dt(r.created_at),
        })

    live_info = LIVE_EXECUTION_STATE.get(ex.id, {})
    completed_count = (ex.passed or 0) + (ex.failed or 0) + (ex.skipped or 0)
    progress_percent = int((completed_count / ex.total) * 100) if ex.total else 0
    if ex.status == "completed":
        progress_percent = 100

    return {
        "id": ex.id,
        "app_id": ex.app_id,
        "started_at": _serialize_dt(ex.started_at),
        "completed_at": _serialize_dt(ex.completed_at),
        "total": ex.total,
        "passed": ex.passed,
        "failed": ex.failed,
        "skipped": ex.skipped,
        "status": ex.status,
        "progress_percent": progress_percent,
        "current_test": live_info.get("current_test", ""),
        "current_url": live_info.get("current_url", ""),
        "browser_status": live_info.get("browser_status", "Completed" if ex.status == "completed" else "Idle"),
        "stage": live_info.get("stage", f"Completed {completed_count}/{ex.total}" if ex.status == "completed" else ""),
        "results": result_list,
    }


# ===================== History =====================

@router.get("/history")
def get_history(test_case_id: int = None, db: Session = Depends(get_db)):
    query = db.query(TestHistory)
    if test_case_id:
        query = query.filter(TestHistory.test_case_id == test_case_id)
    history = query.order_by(TestHistory.timestamp.desc()).all()

    tc_ids = [h.test_case_id for h in history]
    tcs = db.query(TestCase).filter(TestCase.id.in_(tc_ids)).all() if tc_ids else []
    tc_map = {tc.id: tc for tc in tcs}

    result = []
    for h in history:
        tc = tc_map.get(h.test_case_id)
        result.append({
            "id": h.id,
            "test_case_id": h.test_case_id,
            "test_id": tc.test_id if tc else "",
            "execution_id": h.execution_id,
            "status": h.status,
            "failure_category": getattr(h, "failure_category", None),
            "duration_ms": h.duration_ms,
            "failure_reason": h.failure_reason,
            "timestamp": _serialize_dt(h.timestamp),
        })
    return result


# ===================== Results =====================

@router.get("/results")
def get_results(app_id: int = None, db: Session = Depends(get_db)):
    query = db.query(TestExecution).filter(TestExecution.status == "completed")
    if app_id:
        query = query.filter(TestExecution.app_id == app_id)

    latest = query.order_by(TestExecution.completed_at.desc()).first()

    if not latest:
        return {
            "status": "not_evaluated",
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "execution_time_ms": 0,
            "blocking_failures": [],
            "recommendations": [],
            "evaluated_at": None,
        }

    # Get failed results
    failed_results = db.query(TestResult).filter(
        TestResult.execution_id == latest.id,
        TestResult.status.in_(["failed", "error"])
    ).all()

    tc_ids = [r.test_case_id for r in failed_results]
    tcs = db.query(TestCase).filter(TestCase.id.in_(tc_ids)).all() if tc_ids else []
    tc_map = {tc.id: tc for tc in tcs}

    blocking = []
    recommendations = []
    for r in failed_results:
        tc = tc_map.get(r.test_case_id)
        cat = getattr(r, "failure_category", None)
        blocking.append({
            "id": r.id,
            "execution_id": r.execution_id,
            "test_case_id": r.test_case_id,
            "test_id": tc.test_id if tc else "",
            "test_name": tc.name if tc else "",
            "status": r.status,
            "failure_category": cat,
            "duration_ms": r.duration_ms,
            "error_message": r.error_message,
            "screenshot_path": r.screenshot_path,
            "created_at": _serialize_dt(r.created_at),
        })
        if tc:
            cat_desc = f" [{cat}]" if cat else ""
            recommendations.append(f"Review {tc.name}{cat_desc}: {r.error_message or 'Unknown failure'}")

    # Calculate total execution time and breakdown
    all_results = db.query(TestResult).filter(TestResult.execution_id == latest.id).all()
    total_time = sum(r.duration_ms for r in all_results)

    cat_counts = {
        "APPLICATION_FAILURE": 0,
        "ASSERTION_FAILURE": 0,
        "NAVIGATION_FAILURE": 0,
        "ENVIRONMENT_FAILURE": 0,
        "TEST_EXECUTION_ERROR": 0,
    }
    for r in all_results:
        cat = getattr(r, "failure_category", None)
        if cat in cat_counts:
            cat_counts[cat] += 1

    # True defects: only APPLICATION_FAILURE or ASSERTION_FAILURE
    actual_bugs = [
        r for r in failed_results
        if getattr(r, "failure_category", None) in ("APPLICATION_FAILURE", "ASSERTION_FAILURE", None)
        and r.status == "failed"
    ]
    status = "ready" if len(actual_bugs) == 0 else "changes_required"

    # Contextual candidate and QAOA counts for research analytics
    target_app_id = latest.app_id
    total_candidates = db.query(TestCase).filter(TestCase.app_id == target_app_id).count()
    latest_opt = (
        db.query(OptimizationRun)
        .filter(OptimizationRun.app_id == target_app_id)
        .order_by(OptimizationRun.created_at.desc())
        .first()
    )
    optimized_count = len(latest_opt.selected_tests) if latest_opt and latest_opt.selected_tests else None
    reduction_pct = (
        round(((total_candidates - optimized_count) / total_candidates) * 100, 1)
        if (optimized_count and total_candidates and total_candidates > 0 and total_candidates >= optimized_count)
        else 0.0
    )

    return {
        "status": status,
        "execution_id": latest.id,
        "app_id": target_app_id,
        "total_candidates": total_candidates,
        "optimized_tests": optimized_count,
        "reduction_percent": reduction_pct,
        "total_tests": latest.total,
        "executed_tests": latest.total,
        "passed": latest.passed,
        "failed": latest.failed,
        "skipped": latest.skipped,
        "detected_defects": len(actual_bugs),
        "application_failures": cat_counts["APPLICATION_FAILURE"],
        "assertion_failures": cat_counts["ASSERTION_FAILURE"],
        "navigation_failures": cat_counts["NAVIGATION_FAILURE"],
        "environment_failures": cat_counts["ENVIRONMENT_FAILURE"],
        "execution_errors": cat_counts["TEST_EXECUTION_ERROR"],
        "execution_time_ms": total_time,
        "runtime_sec": round(total_time / 1000.0, 2),
        "blocking_failures": blocking,
        "recommendations": recommendations,
        "evaluated_at": _serialize_dt(latest.completed_at),
    }


# ===================== Optimization =====================

@router.post("/optimization/qubo")
def build_qubo_endpoint(req: OptimizationRequest, db: Session = Depends(get_db)):
    """Build QUBO matrix from test cases."""
    from ..optimizer.qubo_builder import build_qubo

    app = db.query(Application).filter(Application.id == req.app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status == "failed":
        raise HTTPException(400, "Cannot optimize tests for an application whose analysis failed. Complete website discovery and generate valid tests first.")
    if app.status == "analyzing":
        raise HTTPException(400, "Application analysis is currently in progress. Please wait for discovery to complete.")

    test_cases = db.query(TestCase).filter(TestCase.app_id == req.app_id).all()
    if not test_cases:
        raise HTTPException(400, "No test cases found for this application. Complete website discovery and generate valid tests first.")

    # Build test case data dicts with historical stats
    tc_data = []
    for tc in test_cases:
        history = db.query(TestHistory).filter(TestHistory.test_case_id == tc.id).all()
        runs = len(history)
        failures = sum(1 for h in history if h.status == "failed")
        rate = failures / runs if runs > 0 else 0.0

        tc_data.append({
            "id": tc.id,
            "name": tc.name,
            "change_impact": tc.change_impact,
            "failure_rate": rate,
            "coverage": tc.coverage,
            "risk": tc.risk,
            "execution_cost": tc.execution_cost,
            "redundancy_group": tc.redundancy_group,
        })

    result = build_qubo(tc_data, weights=req.weights, budget=req.budget)
    return result


@router.post("/optimization/qaoa")
def run_qaoa_endpoint(req: OptimizationRequest, db: Session = Depends(get_db)):
    """Run QAOA optimization on test cases."""
    from ..optimizer.qubo_builder import build_qubo
    from ..optimizer.qaoa_optimizer import run_qaoa

    app = db.query(Application).filter(Application.id == req.app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status == "failed":
        raise HTTPException(400, "Cannot run QAOA for an application whose analysis failed. Complete website discovery and generate valid tests first.")
    if app.status == "analyzing":
        raise HTTPException(400, "Application analysis is currently in progress. Please wait for discovery to complete.")

    test_cases = db.query(TestCase).filter(TestCase.app_id == req.app_id).all()
    if not test_cases:
        raise HTTPException(400, "No test cases found for this application. Complete website discovery and generate valid tests first.")

    # Build test case data
    tc_data = []
    for tc in test_cases:
        history = db.query(TestHistory).filter(TestHistory.test_case_id == tc.id).all()
        runs = len(history)
        failures = sum(1 for h in history if h.status == "failed")
        rate = failures / runs if runs > 0 else 0.0

        tc_data.append({
            "id": tc.id,
            "name": tc.name,
            "change_impact": tc.change_impact,
            "failure_rate": rate,
            "coverage": tc.coverage,
            "risk": tc.risk,
            "execution_cost": tc.execution_cost,
            "redundancy_group": tc.redundancy_group,
        })

    # Build QUBO
    qubo_result = build_qubo(tc_data, weights=req.weights, budget=req.budget)

    # Run QAOA
    qaoa_result = run_qaoa(
        qubo_matrix=qubo_result["qubo_matrix"],
        test_ids=qubo_result["test_ids"],
        budget=req.budget,
        p=req.p,
        shots=req.shots,
    )

    # Update test case statuses
    for tc in test_cases:
        if tc.id in qaoa_result["selected_tests"]:
            tc.status = "selected"
        else:
            tc.status = "excluded"

    # Store optimization run
    opt_run = OptimizationRun(
        app_id=req.app_id,
        qubo_size=qubo_result["num_variables"],
        qaoa_params={
            "p": req.p,
            "shots": req.shots,
            "weights": qubo_result["weights"],
            "budget": req.budget,
        },
        selected_tests=qaoa_result["selected_tests"],
        excluded_tests=qaoa_result["excluded_tests"],
        objective_value=qaoa_result["objective_value"],
    )
    db.add(opt_run)
    db.commit()
    db.refresh(opt_run)

    # Build response with test names
    selected_details = []
    excluded_details = []
    for tc in test_cases:
        entry = {"id": tc.id, "test_id": tc.test_id, "name": tc.name,
                 "risk": tc.risk, "coverage": tc.coverage}
        if tc.id in qaoa_result["selected_tests"]:
            selected_details.append(entry)
        else:
            excluded_details.append(entry)

    return {
        "id": opt_run.id,
        "app_id": req.app_id,
        "qubo_matrix": qubo_result.get("qubo_matrix", []),
        "qubo_size": qubo_result["num_variables"],
        "num_variables": qubo_result["num_variables"],
        "total_candidates": len(test_cases),
        "selected_count": len(qaoa_result["selected_tests"]),
        "excluded_count": len(qaoa_result["excluded_tests"]),
        "selected_tests": selected_details,
        "excluded_tests": excluded_details,
        "selected_ids": qaoa_result["selected_tests"],
        "excluded_ids": qaoa_result["excluded_tests"],
        "selected_details": selected_details,
        "excluded_details": excluded_details,
        "objective_value": qaoa_result["objective_value"],
        "qaoa_params": opt_run.qaoa_params,
        "metadata": qaoa_result.get("metadata", {}),
        "created_at": _serialize_dt(opt_run.created_at),
    }


# ===================== Version Compare =====================

@router.post("/versions/compare")
async def compare_versions(req: dict, db: Session = Depends(get_db)):
    """Compare two deployed website versions by observable structure."""
    baseline_url = req.get("baseline_url", "").strip().rstrip("/")
    new_url = req.get("new_url", "").strip().rstrip("/")

    if not baseline_url or not new_url:
        raise HTTPException(400, "Both baseline_url and new_url are required")

    # Analyze both (sync Playwright in thread)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        loop = asyncio.get_event_loop()
        baseline_analysis = await loop.run_in_executor(pool, analyze_website_sync, baseline_url)
        new_analysis = await loop.run_in_executor(pool, analyze_website_sync, new_url)

    if not baseline_analysis.get("reachable"):
        raise HTTPException(400, f"Cannot reach baseline URL: {baseline_url}")
    if not new_analysis.get("reachable"):
        raise HTTPException(400, f"Cannot reach new URL: {new_url}")

    # Compare pages
    baseline_paths = {p["path"] for p in baseline_analysis.get("pages", [])}
    new_paths = {p["path"] for p in new_analysis.get("pages", [])}
    new_pages = list(new_paths - baseline_paths)
    removed_pages = list(baseline_paths - new_paths)

    def _elem_str(elem):
        if isinstance(elem, dict):
            return elem.get("text") or elem.get("name") or elem.get("testid") or elem.get("placeholder") or str(elem)
        return str(elem)

    # Compare elements safely whether dicts or strings
    baseline_buttons = {_elem_str(b) for b in baseline_analysis.get("buttons", []) if _elem_str(b)}
    new_buttons = {_elem_str(b) for b in new_analysis.get("buttons", []) if _elem_str(b)}
    baseline_inputs = {_elem_str(i) for i in baseline_analysis.get("inputs", []) if _elem_str(i)}
    new_inputs = {_elem_str(i) for i in new_analysis.get("inputs", []) if _elem_str(i)}

    changed = []
    for b in list(new_buttons - baseline_buttons)[:10]:
        changed.append(f"New button: {b}")
    for b in list(baseline_buttons - new_buttons)[:10]:
        changed.append(f"Removed button: {b}")
    for i in list(new_inputs - baseline_inputs)[:10]:
        changed.append(f"New input: {i}")
    for i in list(baseline_inputs - new_inputs)[:10]:
        changed.append(f"Removed input: {i}")

    # Dynamically find affected regression tests
    affected_tests = []
    app_record = db.query(Application).filter(Application.url.ilike(f"%{baseline_url}%")).first()
    if not app_record:
        app_record = db.query(Application).filter(Application.url.ilike(f"%{new_url}%")).first()

    if app_record:
        tests = db.query(TestCase).filter(TestCase.app_id == app_record.id).all()
        for tc in tests:
            tc_route = (getattr(tc, "target_route", None) or "").strip()
            is_affected = False
            reasons = []
            if tc_route and (tc_route in removed_pages or tc_route in new_pages):
                is_affected = True
                reasons.append(f"Route '{tc_route}' modified")
            for rem in list(baseline_buttons - new_buttons)[:15]:
                if len(rem) > 3 and rem.lower() in tc.name.lower():
                    is_affected = True
                    reasons.append(f"Element '{rem}' changed")
                    break
            if is_affected:
                affected_tests.append({
                    "test_id": tc.test_id,
                    "name": tc.name,
                    "priority": tc.priority,
                    "reasons": reasons,
                })

    return {
        "baseline_version": baseline_url,
        "new_version": new_url,
        "new_pages": new_pages,
        "removed_pages": removed_pages,
        "changed_elements": changed,
        "affected_tests": affected_tests,
    }


# ===================== AI Status & Developer Report =====================

@router.get("/ai/status")
def get_ai_provider_status():
    """Return status of AI test generation provider."""
    from ..ai.test_generation import get_ai_status
    return get_ai_status()


@router.get("/reports/developer")
def get_developer_report(app_id: int = None, execution_id: int = None, db: Session = Depends(get_db)):
    """Generate a clean, structured developer regression report with actual Playwright findings."""
    query = db.query(TestExecution)
    if execution_id:
        exec_record = query.filter(TestExecution.id == execution_id).first()
    elif app_id:
        exec_record = query.filter(TestExecution.app_id == app_id).order_by(TestExecution.completed_at.desc()).first()
    else:
        exec_record = query.order_by(TestExecution.completed_at.desc()).first()

    if not exec_record:
        raise HTTPException(404, "No execution session found for report generation")

    app = db.query(Application).filter(Application.id == exec_record.app_id).first()
    results = db.query(TestResult).filter(TestResult.execution_id == exec_record.id).all()

    passed = [r for r in results if r.status == "passed"]
    failed = [r for r in results if r.status in ("failed", "error")]

    tc_ids = [r.test_case_id for r in results]
    tcs = db.query(TestCase).filter(TestCase.id.in_(tc_ids)).all() if tc_ids else []
    tc_map = {tc.id: tc for tc in tcs}

    # Build Markdown report
    lines = [
        "# QC-Web Regression Test Report",
        f"**Target Application:** {app.name if app else 'Unknown'}",
        f"**Target URL:** {app.url if app else 'Unknown'}",
        f"**Execution ID:** #{exec_record.id}",
        f"**Execution Date:** {_serialize_dt(exec_record.completed_at or exec_record.started_at)}",
        "",
        "## Summary",
        f"- **Total Tests Executed:** {exec_record.total}",
        f"- **Passed:** {len(passed)}",
        f"- **Failed:** {len(failed)}",
        f"- **Release Readiness:** {'READY FOR RELEASE' if len(failed) == 0 else 'CHANGES REQUIRED'}",
        "",
        "## Failed Tests (Action Required)" if failed else "## All Tests Passed Successfully",
    ]

    for f in failed:
        tc = tc_map.get(f.test_case_id)
        lines.append(f"### {tc.test_id if tc else 'TC'}: {tc.name if tc else 'Test'}")
        lines.append(f"- **Status:** {f.status.upper()}")
        if getattr(f, "failure_category", None):
            lines.append(f"- **Classification:** {f.failure_category}")
        lines.append(f"- **Execution Time:** {f.duration_ms}ms")
        lines.append(f"- **Reason:** {f.error_message or 'Assertion failed during Playwright step execution'}")
        if f.screenshot_path:
            lines.append(f"- **Evidence (DOM Snapshot):** Base64 Screenshot Captured ({len(f.screenshot_path)} bytes)")
        else:
            lines.append(f"- **Evidence:** Screenshot unavailable ({getattr(f, 'failure_category', 'Not captured')})")
        lines.append("")

    lines.append("## Passed Verifications")
    for p in passed:
        tc = tc_map.get(p.test_case_id)
        lines.append(f"- [x] **{tc.test_id if tc else 'TC'}:** {tc.name if tc else 'Test'} ({p.duration_ms}ms)")

    markdown_text = "\n".join(lines)

    return {
        "execution_id": exec_record.id,
        "app_id": exec_record.app_id,
        "app_name": app.name if app else "",
        "app_url": app.url if app else "",
        "total": exec_record.total,
        "passed": len(passed),
        "failed": len(failed),
        "status": "ready" if len(failed) == 0 else "changes_required",
        "markdown": markdown_text,
        "failed_tests": [
            {
                "test_id": tc_map.get(f.test_case_id).test_id if tc_map.get(f.test_case_id) else "",
                "name": tc_map.get(f.test_case_id).name if tc_map.get(f.test_case_id) else "",
                "status": f.status,
                "failure_category": getattr(f, "failure_category", None),
                "error": f.error_message,
                "duration_ms": f.duration_ms,
                "screenshot": f.screenshot_path,
            }
            for f in failed
        ]
    }


@router.post("/applications/version")
def create_application_version(req: dict, db: Session = Depends(get_db)):
    """Analyze a new version URL (e.g. V2), inherit previous failed tests, and synthesize regression suite."""
    baseline_app_id = req.get("baseline_app_id")
    new_url = req.get("new_url", "").strip().rstrip("/")
    version_label = req.get("version_label", "v2").strip()

    if not baseline_app_id or not new_url:
        raise HTTPException(400, "baseline_app_id and new_url are required")

    baseline_app = db.query(Application).filter(Application.id == baseline_app_id).first()
    if not baseline_app:
        raise HTTPException(404, "Baseline application not found")

    # Discover new version URL
    new_analysis = analyze_website_sync(new_url)

    # Create new application record or version
    app_v2 = Application(
        name=f"{baseline_app.name} ({version_label.upper()})",
        url=new_url,
        status="active" if new_analysis.get("reachable") else "error",
        discovered_pages=len(new_analysis.get("pages", [])),
        discovered_elements=new_analysis.get("interactive_elements", 0),
        analysis_data=new_analysis,
    )
    db.add(app_v2)
    db.commit()
    db.refresh(app_v2)

    # Version record
    v_record = ApplicationVersion(
        app_id=app_v2.id,
        version_label=version_label,
        url=new_url,
        analysis_data=new_analysis,
    )
    db.add(v_record)

    # Inherit and prioritize previous failed tests from baseline
    baseline_failed = db.query(TestCase).filter(
        TestCase.app_id == baseline_app_id,
        TestCase.status == "failed"
    ).all()

    inherited_count = 0
    reserved_v2_ids = set()
    for bf in baseline_failed:
        retained_id = get_next_unique_test_id(
            db, proposed_id=f"{bf.test_id}-R", reserved_ids=reserved_v2_ids
        )
        reserved_v2_ids.add(retained_id)
        retained_tc = TestCase(
            app_id=app_v2.id,
            app_version_id=v_record.id,
            test_id=retained_id,
            original_test_id=bf.test_id,
            name=f"[RETAINED REGRESSION] {bf.name}",
            description=f"Retained from {baseline_app.name}: previously failed. {bf.description}",
            steps=bf.steps,
            expected_result=bf.expected_result,
            source="retained_regression",
            priority="critical",
            risk=0.95,
            coverage=bf.coverage,
            change_impact=0.90,
            execution_cost=bf.execution_cost,
            redundancy_group=bf.redundancy_group,
            status="selected",
        )
        db.add(retained_tc)
        inherited_count += 1

    db.commit()

    # Generate candidate tests for the new version
    all_v2_tests = generate_test_cases(
        db, app_v2, retain_previous_failures=True, app_version_id=v_record.id
    )

    return {
        "new_app_id": app_v2.id,
        "name": app_v2.name,
        "url": app_v2.url,
        "version_label": version_label,
        "inherited_regression_tests": inherited_count,
        "total_test_cases": len(all_v2_tests),
        "status": "ready_for_optimization",
    }


