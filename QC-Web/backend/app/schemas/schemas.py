from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


# --- Application schemas ---

class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="URL of the deployed website to analyze")
    force: Optional[bool] = Field(default=False, description="Force re-discovery even if already analyzed")


class ApplicationResponse(BaseModel):
    id: int
    name: str
    url: str
    status: str
    discovered_pages: int
    discovered_elements: int
    analysis_data: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


# --- Test Case schemas ---

class TestCaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: list[str] = []
    expected_result: Optional[str] = None
    priority: str = "medium"
    risk: float = 0.5
    app_id: int = 1
    original_test_id: Optional[str] = None
    app_version_id: Optional[int] = None


class TestCaseGenerateRequest(BaseModel):
    app_id: int


class TestCaseResponse(BaseModel):
    id: int
    test_id: str
    original_test_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    steps: list[str] = []
    expected_result: Optional[str] = None
    source: str
    priority: str
    risk: float
    coverage: float
    change_impact: float
    execution_cost: float
    redundancy_group: Optional[str] = None
    historical_runs: int = 0
    historical_failures: int = 0
    failure_rate: float = 0.0
    status: str
    app_id: int
    app_version_id: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# --- Execution schemas ---

class ExecuteRequest(BaseModel):
    app_id: int
    test_case_ids: Optional[list[int]] = None


class ExecutionResponse(BaseModel):
    id: int
    app_id: int
    started_at: str
    completed_at: Optional[str] = None
    total: int
    passed: int
    failed: int
    skipped: int
    status: str

    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    id: int
    execution_id: int
    test_case_id: int
    test_id: str = ""
    test_name: str = ""
    status: str
    duration_ms: int
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


# --- History schemas ---

class TestHistoryResponse(BaseModel):
    id: int
    test_case_id: int
    test_id: str = ""
    execution_id: int
    status: str
    duration_ms: int
    failure_reason: Optional[str] = None
    timestamp: str

    class Config:
        from_attributes = True


# --- Optimization schemas ---

class OptimizationRequest(BaseModel):
    app_id: int
    weights: Optional[dict] = None
    budget: int = 10
    p: int = 1
    shots: int = 1024


class OptimizationResponse(BaseModel):
    id: int
    app_id: int
    qubo_size: int
    selected_tests: list[int]
    excluded_tests: list[int]
    objective_value: float
    qaoa_params: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


# --- Results schemas ---

class ResultsResponse(BaseModel):
    status: str  # ready, changes_required, not_evaluated
    total_tests: int
    passed: int
    failed: int
    skipped: int
    execution_time_ms: int = 0
    blocking_failures: list[TestResultResponse] = []
    recommendations: list[str] = []
    evaluated_at: Optional[str] = None


# --- Version comparison ---

class VersionCompareRequest(BaseModel):
    baseline_url: str
    new_url: str


class VersionCompareResponse(BaseModel):
    baseline_version: str
    new_version: str
    new_pages: list[str] = []
    removed_pages: list[str] = []
    changed_elements: list[str] = []
    affected_tests: list[int] = []
