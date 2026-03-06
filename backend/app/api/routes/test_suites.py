from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.test_case import TestSuite, TestSuiteTestCase, TestSuiteExecution, TestCase, TestExecution
from app.models.user import User
from app.schemas.test_suite import (
    TestSuiteCreate, TestSuiteUpdate, TestSuiteResponse, TestSuiteDetailResponse,
    TestSuiteAddTestCases, TestSuiteReorderTestCases, TestSuiteCloneRequest,
    TestSuiteExecutionCreate, TestSuiteExecutionResponse, TestSuiteExecutionDetailResponse,
    TestSuiteStatsResponse
)
from app.utils.auth_middleware import get_current_user

router = APIRouter(prefix="/api/test-suites", tags=["test-suites"])


def generate_suite_id(db: Session) -> str:
    """Generate unique suite ID like TS-2024-00001"""
    from datetime import datetime
    year = datetime.now().year
    
    # Get the last suite ID for this year
    last_suite = db.query(TestSuite).filter(
        TestSuite.suite_id.like(f"TS-{year}-%")
    ).order_by(TestSuite.id.desc()).first()
    
    if last_suite:
        last_number = int(last_suite.suite_id.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    
    return f"TS-{year}-{new_number:05d}"


# ============ FR-TS-001: Create Test Suite ============

@router.post("/", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
def create_test_suite(
    suite_data: TestSuiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new test suite with optional test cases.
    Supports hierarchical suites (parent/child).
    """
    # Generate unique suite ID
    suite_id = generate_suite_id(db)
    
    # Validate parent suite if provided
    if suite_data.parent_suite_id:
        parent_suite = db.query(TestSuite).filter(
            TestSuite.id == suite_data.parent_suite_id,
            TestSuite.is_deleted == False
        ).first()
        if not parent_suite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent suite not found"
            )
    
    # Create suite
    new_suite = TestSuite(
        suite_id=suite_id,
        name=suite_data.name,
        description=suite_data.description,
        module=suite_data.module,
        parent_suite_id=suite_data.parent_suite_id,
        execution_mode=suite_data.execution_mode,
        status=suite_data.status,
        project_id=suite_data.project_id,
        created_by_id=current_user.id
    )
    
    db.add(new_suite)
    db.flush()  # Get the ID
    
    # Add test cases if provided
    if suite_data.test_case_ids:
        for idx, test_case_id in enumerate(suite_data.test_case_ids):
            # Validate test case exists
            test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
            if not test_case:
                continue
            
            suite_tc = TestSuiteTestCase(
                suite_id=new_suite.id,
                test_case_id=test_case_id,
                order=idx,
                added_by_id=current_user.id
            )
            db.add(suite_tc)
    
    db.commit()
    db.refresh(new_suite)
    
    # Add test case count
    response = TestSuiteResponse.from_orm(new_suite)
    response.test_case_count = len(suite_data.test_case_ids) if suite_data.test_case_ids else 0
    
    return response


@router.get("/", response_model=List[TestSuiteResponse])
def get_test_suites(
    project_id: Optional[int] = None,
    parent_suite_id: Optional[int] = None,
    status: Optional[str] = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all test suites with optional filters.
    Can filter by project, parent suite, and status.
    """
    query = db.query(TestSuite).filter(TestSuite.is_deleted == False)
    
    if project_id:
        query = query.filter(TestSuite.project_id == project_id)
    
    if parent_suite_id is not None:
        if parent_suite_id == 0:
            # Root level suites only
            query = query.filter(TestSuite.parent_suite_id == None)
        else:
            query = query.filter(TestSuite.parent_suite_id == parent_suite_id)
    
    if status:
        query = query.filter(TestSuite.status == status)
    elif not include_archived:
        query = query.filter(TestSuite.status != "archived")
    
    suites = query.order_by(TestSuite.created_at.desc()).all()
    
    # Add test case counts
    result = []
    for suite in suites:
        suite_response = TestSuiteResponse.from_orm(suite)
        suite_response.test_case_count = db.query(TestSuiteTestCase).filter(
            TestSuiteTestCase.suite_id == suite.id
        ).count()
        result.append(suite_response)
    
    return result


@router.get("/{suite_id}", response_model=TestSuiteDetailResponse)
def get_test_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific test suite.
    Includes test cases and child suites.
    """
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Get test cases with order
    suite_test_cases = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == suite_id
    ).order_by(TestSuiteTestCase.order).all()
    
    test_cases = []
    for stc in suite_test_cases:
        tc = db.query(TestCase).filter(TestCase.id == stc.test_case_id).first()
        if tc:
            test_cases.append({
                "id": tc.id,
                "test_case_id": tc.test_case_id,
                "title": tc.title,
                "priority": tc.priority,
                "status": tc.status,
                "order": stc.order,
                "module": tc.module
            })
    
    # Get child suites
    child_suites = db.query(TestSuite).filter(
        TestSuite.parent_suite_id == suite_id,
        TestSuite.is_deleted == False
    ).all()
    
    response = TestSuiteDetailResponse.from_orm(suite)
    response.test_cases = test_cases
    response.test_case_count = len(test_cases)
    response.child_suites = [TestSuiteResponse.from_orm(cs) for cs in child_suites]
    
    return response


# ============ FR-TS-003: Suite Management ============

@router.put("/{suite_id}", response_model=TestSuiteResponse)
def update_test_suite(
    suite_id: int,
    suite_data: TestSuiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update test suite metadata"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Update fields
    update_data = suite_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(suite, field, value)
    
    suite.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(suite)
    
    response = TestSuiteResponse.from_orm(suite)
    response.test_case_count = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == suite_id
    ).count()
    
    return response


@router.post("/{suite_id}/test-cases", response_model=dict)
def add_test_cases_to_suite(
    suite_id: int,
    data: TestSuiteAddTestCases,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add test cases to a suite"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Get current max order
    max_order_result = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == suite_id
    ).order_by(TestSuiteTestCase.order.desc()).first()
    
    starting_order = data.starting_order if data.starting_order is not None else (max_order_result.order + 1 if max_order_result else 0)
    
    added_count = 0
    for idx, test_case_id in enumerate(data.test_case_ids):
        # Check if already exists
        exists = db.query(TestSuiteTestCase).filter(
            TestSuiteTestCase.suite_id == suite_id,
            TestSuiteTestCase.test_case_id == test_case_id
        ).first()
        
        if exists:
            continue
        
        # Validate test case exists
        test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
        if not test_case:
            continue
        
        suite_tc = TestSuiteTestCase(
            suite_id=suite_id,
            test_case_id=test_case_id,
            order=starting_order + idx,
            added_by_id=current_user.id
        )
        db.add(suite_tc)
        added_count += 1
    
    db.commit()
    
    return {
        "message": f"Added {added_count} test cases to suite",
        "added_count": added_count
    }


@router.delete("/{suite_id}/test-cases/{test_case_id}")
def remove_test_case_from_suite(
    suite_id: int,
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a test case from a suite"""
    suite_tc = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == suite_id,
        TestSuiteTestCase.test_case_id == test_case_id
    ).first()
    
    if not suite_tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found in this suite"
        )
    
    db.delete(suite_tc)
    db.commit()
    
    return {"message": "Test case removed from suite"}


@router.put("/{suite_id}/reorder", response_model=dict)
def reorder_test_cases(
    suite_id: int,
    data: TestSuiteReorderTestCases,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reorder test cases within a suite"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Update orders
    for item in data.test_case_orders:
        suite_tc = db.query(TestSuiteTestCase).filter(
            TestSuiteTestCase.suite_id == suite_id,
            TestSuiteTestCase.test_case_id == item["test_case_id"]
        ).first()
        
        if suite_tc:
            suite_tc.order = item["order"]
    
    db.commit()
    
    return {"message": "Test cases reordered successfully"}


@router.post("/{suite_id}/clone", response_model=TestSuiteResponse)
def clone_test_suite(
    suite_id: int,
    clone_data: TestSuiteCloneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone an entire test suite with optional child suites"""
    original_suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not original_suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Create new suite
    new_suite_id = generate_suite_id(db)
    new_suite = TestSuite(
        suite_id=new_suite_id,
        name=clone_data.new_name,
        description=original_suite.description,
        module=original_suite.module,
        parent_suite_id=original_suite.parent_suite_id,
        execution_mode=original_suite.execution_mode,
        status="draft",
        project_id=original_suite.project_id,
        created_by_id=current_user.id
    )
    
    db.add(new_suite)
    db.flush()
    
    # Clone test cases
    original_test_cases = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == suite_id
    ).order_by(TestSuiteTestCase.order).all()
    
    for stc in original_test_cases:
        new_stc = TestSuiteTestCase(
            suite_id=new_suite.id,
            test_case_id=stc.test_case_id,
            order=stc.order,
            added_by_id=current_user.id
        )
        db.add(new_stc)
    
    db.commit()
    db.refresh(new_suite)
    
    response = TestSuiteResponse.from_orm(new_suite)
    response.test_case_count = len(original_test_cases)
    
    return response


@router.put("/{suite_id}/archive")
def archive_test_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a test suite"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    suite.status = "archived"
    suite.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Test suite archived successfully"}


@router.put("/{suite_id}/restore")
def restore_test_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore an archived test suite"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    suite.status = "active"
    suite.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Test suite restored successfully"}


@router.delete("/{suite_id}")
def delete_test_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a test suite"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    suite.is_deleted = True
    suite.deleted_at = datetime.utcnow()
    suite.deleted_by_id = current_user.id
    
    db.commit()
    
    return {"message": "Test suite deleted successfully"}


# ============ FR-TS-002: Suite Execution ============

@router.post("/execute", response_model=TestSuiteExecutionResponse)
def execute_test_suite(
    execution_data: TestSuiteExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute all test cases in a suite.
    Creates an execution record and returns it for tracking.
    """
    suite = db.query(TestSuite).filter(
        TestSuite.id == execution_data.suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Get test cases in suite
    test_cases = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == execution_data.suite_id
    ).count()
    
    # Create execution record
    execution_mode = execution_data.execution_mode or suite.execution_mode
    
    execution = TestSuiteExecution(
        suite_id=execution_data.suite_id,
        execution_name=execution_data.execution_name,
        executed_by_id=current_user.id,
        execution_mode=execution_mode,
        status="running",
        total_test_cases=test_cases,
        environment=execution_data.environment,
        notes=execution_data.notes
    )
    
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    return TestSuiteExecutionResponse.from_orm(execution)


@router.get("/{suite_id}/executions", response_model=List[TestSuiteExecutionResponse])
def get_suite_executions(
    suite_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get execution history for a test suite"""
    executions = db.query(TestSuiteExecution).filter(
        TestSuiteExecution.suite_id == suite_id
    ).order_by(TestSuiteExecution.started_at.desc()).limit(limit).all()
    
    return [TestSuiteExecutionResponse.from_orm(ex) for ex in executions]


@router.get("/executions/{execution_id}", response_model=TestSuiteExecutionDetailResponse)
def get_suite_execution_detail(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a suite execution"""
    execution = db.query(TestSuiteExecution).filter(
        TestSuiteExecution.id == execution_id
    ).first()
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    # Get suite info
    suite = db.query(TestSuite).filter(TestSuite.id == execution.suite_id).first()
    
    response = TestSuiteExecutionDetailResponse.from_orm(execution)
    response.suite_name = suite.name if suite else "Unknown"
    
    # Calculate duration
    if execution.completed_at and execution.started_at:
        duration = (execution.completed_at - execution.started_at).total_seconds() / 60
        response.duration_minutes = round(duration, 2)
    
    return response


@router.put("/executions/{execution_id}", response_model=TestSuiteExecutionResponse)
def update_suite_execution(
    execution_id: int,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update execution status and results"""
    execution = db.query(TestSuiteExecution).filter(
        TestSuiteExecution.id == execution_id
    ).first()
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    # Update fields
    for field, value in update_data.items():
        if hasattr(execution, field):
            setattr(execution, field, value)
    
    db.commit()
    db.refresh(execution)
    
    return TestSuiteExecutionResponse.from_orm(execution)


@router.get("/{suite_id}/stats", response_model=TestSuiteStatsResponse)
def get_suite_statistics(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get statistics for a test suite"""
    suite = db.query(TestSuite).filter(
        TestSuite.id == suite_id,
        TestSuite.is_deleted == False
    ).first()
    
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found"
        )
    
    # Get test case count
    test_case_count = db.query(TestSuiteTestCase).filter(
        TestSuiteTestCase.suite_id == suite_id
    ).count()
    
    # Get child suite count
    child_suite_count = db.query(TestSuite).filter(
        TestSuite.parent_suite_id == suite_id,
        TestSuite.is_deleted == False
    ).count()
    
    # Get last execution
    last_execution = db.query(TestSuiteExecution).filter(
        TestSuiteExecution.suite_id == suite_id
    ).order_by(TestSuiteExecution.started_at.desc()).first()
    
    pass_rate = None
    if last_execution and last_execution.total_test_cases > 0:
        pass_rate = (last_execution.passed / last_execution.total_test_cases) * 100
    
    return TestSuiteStatsResponse(
        suite_id=suite_id,
        total_test_cases=test_case_count,
        total_suites=child_suite_count,
        estimated_duration=suite.estimated_duration,
        last_execution_date=last_execution.started_at if last_execution else None,
        last_execution_status=last_execution.status if last_execution else None,
        pass_rate=round(pass_rate, 2) if pass_rate else None
    )
