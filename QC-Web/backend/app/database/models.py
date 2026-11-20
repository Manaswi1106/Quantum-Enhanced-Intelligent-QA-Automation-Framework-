from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.db import Base
import enum


class AppStatus(str, enum.Enum):
    ANALYZING = "analyzing"
    ACTIVE = "active"
    LIMITED_DISCOVERY = "limited_discovery"
    FAILED = "failed"
    ERROR = "failed"  # Alias for backward compatibility


class TestSource(str, enum.Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class TestPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TestStatus(str, enum.Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    SELECTED = "selected"
    EXCLUDED = "excluded"


class ExecutionStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class ResultStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    status = Column(String, default=AppStatus.ANALYZING.value)
    discovered_pages = Column(Integer, default=0)
    discovered_elements = Column(Integer, default=0)
    analysis_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    versions = relationship("ApplicationVersion", back_populates="application", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="application", cascade="all, delete-orphan")
    executions = relationship("TestExecution", back_populates="application", cascade="all, delete-orphan")
    pages = relationship("DiscoveredPage", back_populates="application", cascade="all, delete-orphan")
    elements = relationship("InteractiveElement", back_populates="application", cascade="all, delete-orphan")
    optimization_runs = relationship("OptimizationRun", back_populates="application", cascade="all, delete-orphan")


class DiscoveredPage(Base):
    __tablename__ = "discovered_pages"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    path = Column(String, nullable=False)
    title = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="pages")
    elements = relationship("InteractiveElement", back_populates="page", cascade="all, delete-orphan")


class InteractiveElement(Base):
    __tablename__ = "interactive_elements"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id = Column(Integer, ForeignKey("discovered_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    element_type = Column(String, nullable=False)  # button, input, form, link
    tag_name = Column(String, nullable=True)
    selector = Column(String, nullable=True)
    testid = Column(String, nullable=True)
    name = Column(String, nullable=True)
    text = Column(String, nullable=True)
    page_path = Column(String, nullable=True)
    attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="elements")
    page = relationship("DiscoveredPage", back_populates="elements")


class ApplicationVersion(Base):
    __tablename__ = "application_versions"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label = Column(String, nullable=False)
    url = Column(String, nullable=False)
    analysis_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="versions")
    executions = relationship("TestExecution", back_populates="app_version")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String, nullable=False, index=True)
    original_test_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(JSON, default=list)
    expected_result = Column(Text, nullable=True)
    source = Column(String, default=TestSource.MANUAL.value)
    priority = Column(String, default=TestPriority.MEDIUM.value)
    risk = Column(Float, default=0.5)
    coverage = Column(Float, default=0.5)
    change_impact = Column(Float, default=0.5)
    execution_cost = Column(Float, default=1.0)
    redundancy_group = Column(String, nullable=True)
    status = Column(String, default=TestStatus.NOT_RUN.value)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    app_version_id = Column(Integer, ForeignKey("application_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="test_cases")
    app_version = relationship("ApplicationVersion", backref="test_cases")
    results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")
    history = relationship("TestHistory", back_populates="test_case", cascade="all, delete-orphan")


class TestExecution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    app_version_id = Column(Integer, ForeignKey("application_versions.id", ondelete="SET NULL"), nullable=True)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    total = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    status = Column(String, default=ExecutionStatus.RUNNING.value)

    application = relationship("Application", back_populates="executions")
    app_version = relationship("ApplicationVersion", back_populates="executions")
    results = relationship("TestResult", back_populates="execution", cascade="all, delete-orphan")
    history_entries = relationship("TestHistory", back_populates="execution", cascade="all, delete-orphan")
    optimization_runs = relationship("OptimizationRun", back_populates="execution")


class TestResult(Base):
    __tablename__ = "execution_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default=ResultStatus.SKIPPED.value)
    failure_category = Column(String, nullable=True)
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    execution = relationship("TestExecution", back_populates="results")
    test_case = relationship("TestCase", back_populates="results")


class OptimizationRun(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id", ondelete="SET NULL"), nullable=True)
    qubo_matrix = Column(JSON, nullable=True)
    qubo_size = Column(Integer, default=0)
    qaoa_params = Column(JSON, nullable=True)
    selected_tests = Column(JSON, default=list)
    excluded_tests = Column(JSON, default=list)
    objective_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="optimization_runs")
    execution = relationship("TestExecution", back_populates="optimization_runs")


class TestHistory(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False)
    failure_category = Column(String, nullable=True)
    duration_ms = Column(Integer, default=0)
    failure_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    test_case = relationship("TestCase", back_populates="history")
    execution = relationship("TestExecution", back_populates="history_entries")


# Model aliases for domain and schema naming consistency
Execution = TestExecution
ExecutionResult = TestResult
History = TestHistory
OptimizationResult = OptimizationRun
