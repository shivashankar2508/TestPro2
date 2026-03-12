from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============ Enums ============

class PriorityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SeverityEnum(str, Enum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    TRIVIAL = "trivial"

class TestTypeEnum(str, Enum):
    FUNCTIONAL = "functional"
    REGRESSION = "regression"
    SMOKE = "smoke"
    INTEGRATION = "integration"
    UAT = "uat"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"

class TestCaseStatusEnum(str, Enum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class StepStatusEnum(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    NOT_EXECUTED = "not_executed"

class AutomationStatusEnum(str, Enum):
    NOT_AUTOMATED = "not_automated"
    IN_PROGRESS = "in_progress"
    AUTOMATED = "automated"
    CANNOT_AUTOMATE = "cannot_automate"

# ============ Test Step Schemas ============

class TestStepBase(BaseModel):
    step_number: int = Field(..., ge=1, description="Step order number")
    action: str = Field(..., min_length=1, max_length=2000, description="Action to perform")
    test_data: Optional[str] = Field(None, max_length=2000, description="Test data for this step")
    expected_result: str = Field(..., min_length=1, max_length=2000, description="Expected outcome")

class TestStepCreate(TestStepBase):
    pass

class TestStepUpdate(BaseModel):
    action: Optional[str] = Field(None, min_length=1, max_length=2000)
    test_data: Optional[str] = Field(None, max_length=2000)
    expected_result: Optional[str] = Field(None, min_length=1, max_length=2000)
    actual_result: Optional[str] = Field(None, max_length=2000)
    status: Optional[StepStatusEnum] = None
    notes: Optional[str] = Field(None, max_length=1000)

class TestStepResponse(TestStepBase):
    id: int
    test_case_id: int
    actual_result: Optional[str]
    status: StepStatusEnum
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ============ Tag Schemas ============

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    color: Optional[str] = Field("#667eea", pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code")
    
    @validator('name')
    def validate_tag_name(cls, v):
        # Lowercase and remove extra spaces
        return v.lower().strip()

class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Test Case Schemas ============

class TestCaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Test case title")
    description: Optional[str] = Field(None, description="Detailed description")
    module: str = Field(..., min_length=1, max_length=100, description="Module/feature being tested")
    priority: PriorityEnum = Field(default=PriorityEnum.MEDIUM, description="Test priority")
    severity: SeverityEnum = Field(default=SeverityEnum.MINOR, description="Failure severity")
    type: TestTypeEnum = Field(default=TestTypeEnum.FUNCTIONAL, description="Test type")
    status: TestCaseStatusEnum = Field(default=TestCaseStatusEnum.DRAFT, description="Test case status")
    
    # Pre-conditions
    pre_conditions: Optional[str] = Field(None, description="Conditions before test execution")
    test_data_requirements: Optional[str] = Field(None, description="Required test data")
    environment_requirements: Optional[str] = Field(None, description="Environment setup requirements")
    
    # Post-conditions
    post_conditions: Optional[str] = Field(None, description="System state after test")
    cleanup_steps: Optional[str] = Field(None, description="Cleanup actions")
    
    # Metadata
    estimated_duration: Optional[float] = Field(None, ge=0, description="Estimated duration in minutes")
    automation_status: AutomationStatusEnum = Field(default=AutomationStatusEnum.NOT_AUTOMATED)
    automation_script_link: Optional[str] = Field(None, max_length=500, description="Link to automation script")

class TestCaseCreate(TestCaseBase):
    project_id: int = Field(..., description="Project ID")
    assigned_tester_id: Optional[int] = Field(None, description="Assigned tester user ID")
    steps: List[TestStepCreate] = Field(default=[], description="Test steps")
    tags: List[str] = Field(default=[], description="Tag names")
    
    @validator('steps')
    def validate_steps(cls, v):
        if len(v) > 100:
            raise ValueError('Cannot have more than 100 steps in a test case')
        return v

class TestCaseUpdate(BaseModel):
    change_summary: str = Field(..., min_length=5, max_length=500, description="Required summary of what changed")
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    module: Optional[str] = Field(None, min_length=1, max_length=100)
    priority: Optional[PriorityEnum] = None
    severity: Optional[SeverityEnum] = None
    type: Optional[TestTypeEnum] = None
    status: Optional[TestCaseStatusEnum] = None
    
    pre_conditions: Optional[str] = None
    test_data_requirements: Optional[str] = None
    environment_requirements: Optional[str] = None
    
    post_conditions: Optional[str] = None
    cleanup_steps: Optional[str] = None
    
    estimated_duration: Optional[float] = Field(None, ge=0)
    automation_status: Optional[AutomationStatusEnum] = None
    automation_script_link: Optional[str] = Field(None, max_length=500)
    assigned_tester_id: Optional[int] = None
    owner_id: Optional[int] = None
    
    tags: Optional[List[str]] = None

class TestCaseResponse(TestCaseBase):
    id: int
    test_case_id: str
    project_id: int
    created_by_id: int
    owner_id: Optional[int]
    assigned_tester_id: Optional[int]
    last_modified_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    version: int
    is_deleted: bool
    
    # Related data
    steps: List[TestStepResponse] = []
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True

class TestCaseListResponse(BaseModel):
    id: int
    test_case_id: str
    title: str
    module: str
    owner_id: Optional[int]
    assigned_tester_id: Optional[int]
    priority: PriorityEnum
    severity: SeverityEnum
    type: TestTypeEnum
    status: TestCaseStatusEnum
    automation_status: AutomationStatusEnum
    created_at: datetime
    updated_at: datetime
    version: int
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True

# ============ Test Execution Schemas ============

class TestExecutionCreate(BaseModel):
    test_case_id: int
    environment: Optional[str] = Field(None, max_length=100)
    browser: Optional[str] = Field(None, max_length=50)
    os: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    step_results: List[dict] = Field(default=[], description="List of {step_id, status, actual_result, notes}")

class TestExecutionResponse(BaseModel):
    id: int
    test_case_id: int
    executed_by_id: Optional[int]
    execution_date: datetime
    execution_duration: Optional[float]
    status: StepStatusEnum
    pass_count: int
    fail_count: int
    blocked_count: int
    skipped_count: int
    environment: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    notes: Optional[str]
    bug_ids: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExecutionStepResultResponse(BaseModel):
    id: int
    execution_id: int
    step_id: Optional[int]
    step_number: int
    action: str
    test_data: Optional[str]
    expected_result: str
    actual_result: Optional[str]
    status: StepStatusEnum
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============ Pagination Schema ============

class PaginatedTestCasesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    test_cases: List[TestCaseListResponse]

# ============ Statistics Schema ============

class TestCaseStatsResponse(BaseModel):
    total: int
    by_status: dict
    by_priority: dict
    by_type: dict
    by_automation_status: dict
    average_steps: float
    average_duration: Optional[float]


class TestCaseVersionHistoryResponse(BaseModel):
    id: int
    test_case_id: int
    version_number: int
    change_summary: str
    changed_fields: Optional[str]
    changed_by_id: Optional[int]
    changed_at: datetime

    class Config:
        from_attributes = True


class CloneTestCaseRequest(BaseModel):
    clone_attachments: bool = Field(default=False)


class DeleteTestCaseRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true to confirm delete")


class CreateTemplateRequest(BaseModel):
    test_case_id: int
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TestCaseTemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str]
    source_test_case_id: Optional[int]
    created_by_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateFromTemplateRequest(BaseModel):
    project_id: int
    module: Optional[str] = None
    assigned_tester_id: Optional[int] = None


class BulkUpdateRequest(BaseModel):
    test_case_ids: List[int]
    change_summary: str = Field(..., min_length=5, max_length=500)
    status: Optional[TestCaseStatusEnum] = None
    priority: Optional[PriorityEnum] = None
    severity: Optional[SeverityEnum] = None
    assigned_tester_id: Optional[int] = None
    module: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    test_case_ids: List[int]
    confirm: bool = Field(..., description="Must be true to confirm bulk delete")


class ImportPreviewRequest(BaseModel):
    format: str = Field(..., description="csv | excel | json")
    project_id: int
    field_mapping: dict = Field(default_factory=dict)
    records: List[dict] = Field(default_factory=list)


class ImportPreviewResponse(BaseModel):
    batch_id: int
    valid_records: int
    invalid_records: int
    errors: List[str]
    preview: List[dict]


class ImportConfirmRequest(BaseModel):
    batch_id: int
    confirm: bool = Field(..., description="Must be true to confirm import")


class StepExecutionUpdateRequest(BaseModel):
    status: StepStatusEnum
    actual_result: Optional[str] = None
    notes: Optional[str] = None


class FailAndCreateBugRequest(BaseModel):
    summary: str = Field(..., min_length=3, max_length=300)
    description: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    affected_version: Optional[str] = Field(None, max_length=100)
    assigned_to_id: Optional[int] = None


class ManualDurationRequest(BaseModel):
    duration_minutes: float = Field(..., ge=0)


class CreateTestRunRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    target_start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    test_case_ids: List[int] = Field(default_factory=list)
    tester_ids: List[int] = Field(default_factory=list)


class UpdateTestRunAssignmentsRequest(BaseModel):
    tester_ids: List[int] = Field(default_factory=list)


class CreateExecutionStartRequest(BaseModel):
    environment: Optional[str] = Field(None, max_length=100)
    browser: Optional[str] = Field(None, max_length=50)
    os: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
