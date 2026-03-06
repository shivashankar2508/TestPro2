from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, ForeignKey, Text, Float, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

# ============ Enums ============

class PriorityEnum(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SeverityEnum(str, enum.Enum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    TRIVIAL = "trivial"

class TestTypeEnum(str, enum.Enum):
    FUNCTIONAL = "functional"
    REGRESSION = "regression"
    SMOKE = "smoke"
    INTEGRATION = "integration"
    UAT = "uat"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"

class TestCaseStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class StepStatusEnum(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    NOT_EXECUTED = "not_executed"

class AutomationStatusEnum(str, enum.Enum):
    NOT_AUTOMATED = "not_automated"
    IN_PROGRESS = "in_progress"
    AUTOMATED = "automated"
    CANNOT_AUTOMATE = "cannot_automate"

class SuiteStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"

class SuiteExecutionModeEnum(str, enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

# ============ Association Tables ============

test_case_tags = Table(
    'test_case_tags',
    Base.metadata,
    Column('test_case_id', Integer, ForeignKey('test_cases.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)

# ============ Test Suite Models ============

class TestSuiteTestCase(Base):
    """Association table for test suites and test cases with ordering"""
    __tablename__ = "test_suite_test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey('test_suites.id', ondelete='CASCADE'), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False, index=True)
    order = Column(Integer, nullable=False, default=0)  # Order of execution within suite
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    suite = relationship("TestSuite", back_populates="suite_test_cases")
    test_case = relationship("TestCase")
    added_by = relationship("User")

# ============ Test Case Model ============

class TestCase(Base):
    __tablename__ = "test_cases"
    
    # Primary Fields
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String(50), unique=True, nullable=False, index=True)  # TC-2024-00142
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification
    module = Column(String(100), nullable=False)  # Authentication, User Management, etc.
    priority = Column(String(50), default=PriorityEnum.MEDIUM.value, nullable=False)
    severity = Column(String(50), default=SeverityEnum.MINOR.value, nullable=False)
    type = Column(String(50), default=TestTypeEnum.FUNCTIONAL.value, nullable=False)
    status = Column(String(50), default=TestCaseStatusEnum.DRAFT.value, nullable=False)
    
    # Pre-conditions
    pre_conditions = Column(Text, nullable=True)
    test_data_requirements = Column(Text, nullable=True)
    environment_requirements = Column(Text, nullable=True)
    
    # Post-conditions
    post_conditions = Column(Text, nullable=True)
    cleanup_steps = Column(Text, nullable=True)
    
    # Metadata
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_tester_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_modified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    version = Column(Integer, default=1, nullable=False)
    estimated_duration = Column(Float, nullable=True)  # in minutes
    
    # Automation
    automation_status = Column(String(50), default=AutomationStatusEnum.NOT_AUTOMATED.value)
    automation_script_link = Column(String(500), nullable=True)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="test_cases")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_test_cases")
    owner = relationship("User", foreign_keys=[owner_id])
    assigned_tester = relationship("User", foreign_keys=[assigned_tester_id])
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])
    
    steps = relationship("TestStep", back_populates="test_case", cascade="all, delete-orphan", order_by="TestStep.step_number")
    tags = relationship("Tag", secondary=test_case_tags, back_populates="test_cases")
    executions = relationship("TestExecution", back_populates="test_case", cascade="all, delete-orphan")
    attachments = relationship("TestCaseAttachment", back_populates="test_case", cascade="all, delete-orphan")
    version_history = relationship("TestCaseVersionHistory", back_populates="test_case", cascade="all, delete-orphan")

# ============ Test Step Model ============

class TestStep(Base):
    __tablename__ = "test_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    
    # Step Details
    action = Column(Text, nullable=False)
    test_data = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=False)
    
    # Execution Results (filled during test execution)
    actual_result = Column(Text, nullable=True)
    status = Column(String(50), default=StepStatusEnum.NOT_EXECUTED.value)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    test_case = relationship("TestCase", back_populates="steps")

# ============ Tag Model ============

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#667eea")  # Hex color code
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    test_cases = relationship("TestCase", secondary=test_case_tags, back_populates="tags")

# ============ Test Execution Model ============

class TestExecution(Base):
    __tablename__ = "test_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    executed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Execution Details
    execution_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    execution_duration = Column(Float, nullable=True)  # in minutes
    
    # Overall Result
    status = Column(String(50), nullable=False)  # Overall test status
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    blocked_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    
    # Environment
    environment = Column(String(100), nullable=True)  # Dev, QA, Staging, Production
    browser = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    bug_ids = Column(String(500), nullable=True)  # Comma-separated bug IDs
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    test_case = relationship("TestCase", back_populates="executions")
    executed_by = relationship("User")
    evidences = relationship("ExecutionEvidence", back_populates="execution", cascade="all, delete-orphan")
    timer_sessions = relationship("ExecutionTimerSession", back_populates="execution", cascade="all, delete-orphan")

# ============ Test Case Attachment Model ============

class TestCaseAttachment(Base):
    __tablename__ = "test_case_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    file_type = Column(String(50), nullable=True)  # MIME type
    
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    description = Column(Text, nullable=True)
    
    # Relationships
    test_case = relationship("TestCase", back_populates="attachments")
    uploaded_by = relationship("User")


class TestCaseVersionHistory(Base):
    __tablename__ = "test_case_version_history"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    change_summary = Column(String(500), nullable=False)
    changed_fields = Column(Text, nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    test_case = relationship("TestCase", back_populates="version_history")
    changed_by = relationship("User")


class TestCaseTemplate(Base):
    __tablename__ = "test_case_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    source_test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    payload = Column(Text, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    source_test_case = relationship("TestCase")
    created_by = relationship("User")


class TestCaseImportBatch(Base):
    __tablename__ = "test_case_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    format = Column(String(20), nullable=False)
    field_mapping = Column(Text, nullable=True)
    preview_payload = Column(Text, nullable=False)
    validation_errors = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    created_by = relationship("User")


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    target_start_date = Column(DateTime, nullable=True)
    target_end_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="planned", nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User")
    items = relationship("TestRunItem", back_populates="test_run", cascade="all, delete-orphan")


class TestRunItem(Base):
    __tablename__ = "test_run_items"

    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_tester_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default=StepStatusEnum.NOT_EXECUTED.value, nullable=False)
    latest_execution_id = Column(Integer, ForeignKey("test_executions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    test_run = relationship("TestRun", back_populates="items")
    test_case = relationship("TestCase")
    assigned_tester = relationship("User")
    latest_execution = relationship("TestExecution")


class ExecutionEvidence(Base):
    __tablename__ = "execution_evidences"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(Integer, ForeignKey("test_steps.id", ondelete="SET NULL"), nullable=True)
    evidence_type = Column(String(20), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution = relationship("TestExecution", back_populates="evidences")
    test_case = relationship("TestCase")
    step = relationship("TestStep")
    uploaded_by = relationship("User")


class ExecutionTimerSession(Base):
    __tablename__ = "execution_timer_sessions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    total_paused_seconds = Column(Integer, default=0, nullable=False)
    manual_duration_minutes = Column(Float, nullable=True)
    is_running = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    execution = relationship("TestExecution", back_populates="timer_sessions")


# ============ Test Suite Models ============

class TestSuite(Base):
    """Test Suite for grouping related test cases"""
    __tablename__ = "test_suites"
    
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(String(50), unique=True, nullable=False, index=True)  # TS-2024-00001
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    module = Column(String(100), nullable=True)  # Module/Feature area
    
    # Hierarchical structure
    parent_suite_id = Column(Integer, ForeignKey("test_suites.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Execution settings
    execution_mode = Column(String(20), default=SuiteExecutionModeEnum.SEQUENTIAL.value, nullable=False)
    estimated_duration = Column(Float, nullable=True)  # Total estimated duration in minutes
    
    # Status
    status = Column(String(20), default=SuiteStatusEnum.ACTIVE.value, nullable=False)
    
    # Metadata
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    project = relationship("Project")
    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])
    
    # Hierarchical relationships
    parent_suite = relationship("TestSuite", remote_side=[id], backref="child_suites")
    
    # Test cases in this suite
    suite_test_cases = relationship("TestSuiteTestCase", back_populates="suite", cascade="all, delete-orphan", order_by="TestSuiteTestCase.order")
    
    # Executions
    executions = relationship("TestSuiteExecution", back_populates="suite", cascade="all, delete-orphan")


class TestSuiteExecution(Base):
    """Execution record for a test suite"""
    __tablename__ = "test_suite_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Execution info
    execution_name = Column(String(200), nullable=True)
    executed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Execution mode used
    execution_mode = Column(String(20), nullable=False)  # sequential or parallel
    
    # Status
    status = Column(String(50), nullable=False)  # running, completed, failed, aborted
    
    # Results summary
    total_test_cases = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    blocked = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    
    # Environment
    environment = Column(String(100), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    suite = relationship("TestSuite", back_populates="executions")
    executed_by = relationship("User")


# ============ Update User Model Relationships ============
# Add these to the User model in user.py:
# created_test_cases = relationship("TestCase", foreign_keys="TestCase.created_by_id", back_populates="created_by")
