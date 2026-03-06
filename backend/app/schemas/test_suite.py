from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============ Test Suite Schemas ============

class TestSuiteTestCaseBase(BaseModel):
    test_case_id: int
    order: int = 0


class TestSuiteTestCaseCreate(TestSuiteTestCaseBase):
    pass


class TestSuiteTestCaseResponse(TestSuiteTestCaseBase):
    id: int
    suite_id: int
    added_at: datetime
    added_by_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class TestSuiteBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    module: Optional[str] = Field(None, max_length=100)
    parent_suite_id: Optional[int] = None
    execution_mode: str = "sequential"  # sequential or parallel
    status: str = "active"


class TestSuiteCreate(TestSuiteBase):
    project_id: int
    test_case_ids: Optional[List[int]] = []


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    module: Optional[str] = Field(None, max_length=100)
    parent_suite_id: Optional[int] = None
    execution_mode: Optional[str] = None
    status: Optional[str] = None


class TestSuiteAddTestCases(BaseModel):
    test_case_ids: List[int]
    starting_order: Optional[int] = None  # Where to insert in order


class TestSuiteReorderTestCases(BaseModel):
    test_case_orders: List[dict]  # [{"test_case_id": 1, "order": 0}, ...]


class TestSuiteResponse(TestSuiteBase):
    id: int
    suite_id: str
    project_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    estimated_duration: Optional[float] = None
    test_case_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class TestSuiteDetailResponse(TestSuiteResponse):
    """Detailed suite response with test cases"""
    test_cases: List[dict] = []  # Will include test case details with order
    child_suites: Optional[List[TestSuiteResponse]] = []


class TestSuiteCloneRequest(BaseModel):
    new_name: str = Field(..., max_length=200)
    include_child_suites: bool = False


# ============ Test Suite Execution Schemas ============

class TestSuiteExecutionCreate(BaseModel):
    suite_id: int
    execution_name: Optional[str] = None
    execution_mode: Optional[str] = None  # Override suite's default
    environment: Optional[str] = None
    notes: Optional[str] = None


class TestSuiteExecutionUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class TestSuiteExecutionResponse(BaseModel):
    id: int
    suite_id: int
    execution_name: Optional[str] = None
    executed_by_id: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_mode: str
    status: str
    total_test_cases: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    environment: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class TestSuiteExecutionDetailResponse(TestSuiteExecutionResponse):
    """Detailed execution response with individual test results"""
    test_results: Optional[List[dict]] = []  # Individual test case execution results
    suite_name: Optional[str] = None
    duration_minutes: Optional[float] = None


class TestSuiteStatsResponse(BaseModel):
    """Statistics for a test suite"""
    suite_id: int
    total_test_cases: int
    total_suites: int  # Including child suites
    estimated_duration: Optional[float] = None
    last_execution_date: Optional[datetime] = None
    last_execution_status: Optional[str] = None
    pass_rate: Optional[float] = None  # Based on last execution
