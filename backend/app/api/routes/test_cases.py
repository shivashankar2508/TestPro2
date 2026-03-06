from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime
import json
import io
import csv
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User, RoleEnum
from app.models.test_case import (
    TestCase, TestStep, Tag, TestExecution, TestCaseAttachment,
    TestCaseVersionHistory, TestCaseTemplate, TestCaseImportBatch,
    TestRun, TestRunItem, ExecutionEvidence, ExecutionTimerSession,
    TestCaseStatusEnum, PriorityEnum, SeverityEnum, TestTypeEnum,
    AutomationStatusEnum, StepStatusEnum
)
from app.schemas.test_case import (
    TestCaseCreate, TestCaseUpdate, TestCaseResponse, TestCaseListResponse,
    PaginatedTestCasesResponse, TestCaseStatsResponse,
    TestStepCreate, TestStepUpdate, TestStepResponse,
    TagCreate, TagResponse,
    TestExecutionCreate, TestExecutionResponse,
    TestCaseVersionHistoryResponse, CloneTestCaseRequest, DeleteTestCaseRequest,
    CreateTemplateRequest, TestCaseTemplateResponse, CreateFromTemplateRequest,
    BulkUpdateRequest, BulkDeleteRequest,
    ImportPreviewRequest, ImportPreviewResponse, ImportConfirmRequest,
    StepExecutionUpdateRequest, FailAndCreateBugRequest, ManualDurationRequest,
    CreateTestRunRequest, UpdateTestRunAssignmentsRequest, CreateExecutionStartRequest
)
from app.utils.auth_middleware import get_current_user, require_admin, require_tester
from app.exceptions import (
    ResourceNotFoundError, PermissionDeniedError, ValidationError,
    InvalidOperationError
)

router = APIRouter(prefix="/api/test-cases", tags=["Test Cases"])

# ============ Helper Functions ============

def generate_test_case_id(db: Session, project_id: int) -> str:
    """Generate unique test case ID: TC-YYYY-NNNNN"""
    year = datetime.utcnow().year
    
    # Get the count of test cases for this year
    count = db.query(TestCase).filter(
        TestCase.test_case_id.like(f"TC-{year}-%")
    ).count()
    
    # Generate ID with zero-padding
    tc_id = f"TC-{year}-{str(count + 1).zfill(5)}"
    return tc_id

def get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """Get existing tags or create new ones"""
    tags = []
    for tag_name in tag_names:
        tag_name = tag_name.lower().strip()
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
        tags.append(tag)
    db.flush()
    return tags


def ensure_edit_access(test_case: TestCase, current_user: User) -> None:
    if current_user.role == RoleEnum.ADMIN:
        return
    if test_case.owner_id == current_user.id:
        return
    if test_case.assigned_tester_id == current_user.id:
        return
    raise PermissionDeniedError("You do not have edit access to this test case")


def create_version_log(
    db: Session,
    test_case: TestCase,
    changed_by_id: Optional[int],
    change_summary: str,
    changed_fields: Optional[List[str]] = None
) -> None:
    history = TestCaseVersionHistory(
        test_case_id=test_case.id,
        version_number=test_case.version,
        change_summary=change_summary,
        changed_fields=", ".join(changed_fields) if changed_fields else None,
        changed_by_id=changed_by_id
    )
    db.add(history)


EVIDENCE_LIMITS = {
    "image": 10 * 1024 * 1024,
    "video": 100 * 1024 * 1024,
    "log": 50 * 1024 * 1024,
    "har": 50 * 1024 * 1024,
}


def calculate_execution_duration_minutes(timer: ExecutionTimerSession) -> float:
    end_time = timer.ended_at or datetime.utcnow()
    total_seconds = max(0, int((end_time - timer.started_at).total_seconds()) - timer.total_paused_seconds)
    calculated_minutes = total_seconds / 60.0
    if timer.manual_duration_minutes is not None:
        return float(timer.manual_duration_minutes)
    return round(calculated_minutes, 2)


def get_evidence_type(filename: str, content_type: Optional[str]) -> str:
    ext = Path(filename).suffix.lower()
    ctype = (content_type or "").lower()
    if ctype.startswith("image/") or ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
        return "image"
    if ctype.startswith("video/") or ext in [".mp4", ".webm", ".mov", ".avi", ".mkv"]:
        return "video"
    if ext == ".har":
        return "har"
    if ext in [".log", ".txt", ".json", ".xml", ".csv"] or ctype.startswith("text/"):
        return "log"
    raise HTTPException(status_code=400, detail="Unsupported evidence file type")


def compute_run_progress(items: List[TestRunItem]) -> dict:
    total = len(items)
    completed = len([i for i in items if i.status in ["pass", "fail", "blocked", "skipped"]])
    pass_count = len([i for i in items if i.status == "pass"])
    fail_count = len([i for i in items if i.status == "fail"])
    blocked_count = len([i for i in items if i.status == "blocked"])
    skipped_count = len([i for i in items if i.status == "skipped"])
    not_executed_count = len([i for i in items if i.status == "not_executed"])
    progress_percent = round((completed / total) * 100, 2) if total > 0 else 0.0
    return {
        "total": total,
        "completed": completed,
        "pass": pass_count,
        "fail": fail_count,
        "blocked": blocked_count,
        "skipped": skipped_count,
        "not_executed": not_executed_count,
        "progress_percent": progress_percent,
    }


# ============ Test Case CRUD ============

@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    test_case_data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Create a new test case"""
    
    try:
        # Generate unique test case ID
        test_case_id = generate_test_case_id(db, test_case_data.project_id)
        
        # Create test case
        test_case = TestCase(
            test_case_id=test_case_id,
            title=test_case_data.title,
            description=test_case_data.description,
            module=test_case_data.module,
            priority=test_case_data.priority.value if hasattr(test_case_data.priority, 'value') else test_case_data.priority,
            severity=test_case_data.severity.value if hasattr(test_case_data.severity, 'value') else test_case_data.severity,
            type=test_case_data.type.value if hasattr(test_case_data.type, 'value') else test_case_data.type,
            status=test_case_data.status.value if hasattr(test_case_data.status, 'value') else test_case_data.status,
            pre_conditions=test_case_data.pre_conditions,
            test_data_requirements=test_case_data.test_data_requirements,
            environment_requirements=test_case_data.environment_requirements,
            post_conditions=test_case_data.post_conditions,
            cleanup_steps=test_case_data.cleanup_steps,
            estimated_duration=test_case_data.estimated_duration,
            automation_status=test_case_data.automation_status.value if hasattr(test_case_data.automation_status, 'value') else test_case_data.automation_status,
            automation_script_link=test_case_data.automation_script_link,
            project_id=test_case_data.project_id,
            created_by_id=current_user.id,
            owner_id=current_user.id,
            assigned_tester_id=test_case_data.assigned_tester_id,
            last_modified_by_id=current_user.id
        )
        
        db.add(test_case)
        db.flush()  # Get the ID
        
        # Add test steps
        for step_data in test_case_data.steps:
            step = TestStep(
                test_case_id=test_case.id,
                step_number=step_data.step_number,
                action=step_data.action,
                test_data=step_data.test_data,
                expected_result=step_data.expected_result
            )
            db.add(step)
        
        # Add tags
        if test_case_data.tags:
            test_case.tags = get_or_create_tags(db, test_case_data.tags)

        create_version_log(
            db=db,
            test_case=test_case,
            changed_by_id=current_user.id,
            change_summary="Initial test case creation",
            changed_fields=["initial_create"]
        )

        db.commit()
        db.refresh(test_case)
        
        return test_case
    
    except Exception as e:
        print(f"ERROR creating test case: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test case: {str(e)}"
        )

@router.get("", response_model=PaginatedTestCasesResponse)
async def list_test_cases(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    project_id: Optional[int] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    type: Optional[str] = Query(None, description="Filter by type"),
    automation_status: Optional[str] = Query(None, description="Filter by automation status"),
    search: Optional[str] = Query(None, max_length=200, description="Search in title or test_case_id"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List test cases with pagination and filters"""
    
    try:
        # Base query (exclude deleted)
        query = db.query(TestCase).filter(TestCase.is_deleted == False)
        
        # Apply filters (compare against string values since columns are String type)
        if project_id:
            query = query.filter(TestCase.project_id == project_id)
        if status:
            query = query.filter(TestCase.status == status.lower())
        if priority:
            query = query.filter(TestCase.priority == priority.lower())
        if type:
            query = query.filter(TestCase.type == type.lower())
        if automation_status:
            query = query.filter(TestCase.automation_status == automation_status.lower())
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TestCase.title.ilike(search_pattern),
                    TestCase.test_case_id.ilike(search_pattern)
                )
            )
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(",")]
            query = query.join(TestCase.tags).filter(Tag.name.in_(tag_list))
        
        # Get total count
        total = query.count()
        
        # Paginate
        offset = (page - 1) * page_size
        test_cases = query.options(joinedload(TestCase.tags)).offset(offset).limit(page_size).all()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "test_cases": test_cases
        }
    
    except Exception as e:
        print(f"ERROR listing test cases: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list test cases: {str(e)}"
        )

@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get test case details"""
    
    test_case = db.query(TestCase).options(
        joinedload(TestCase.steps),
        joinedload(TestCase.tags)
    ).filter(
        TestCase.id == test_case_id,
        TestCase.is_deleted == False
    ).first()
    
    if not test_case:
        raise ResourceNotFoundError("Test case")
    
    return test_case

@router.put("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: int,
    update_data: TestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Update test case. Change summary is required for version history."""

    test_case = db.query(TestCase).filter(
        TestCase.id == test_case_id,
        TestCase.is_deleted == False
    ).first()

    if not test_case:
        raise ResourceNotFoundError("Test case")

    ensure_edit_access(test_case, current_user)

    update_dict = update_data.dict(exclude_unset=True, exclude={"tags", "change_summary"})
    changed_fields = []
    for field, value in update_dict.items():
        if getattr(test_case, field) != value:
            setattr(test_case, field, value)
            changed_fields.append(field)

    if update_data.tags is not None:
        test_case.tags = get_or_create_tags(db, update_data.tags)
        changed_fields.append("tags")

    if not changed_fields:
        raise ValidationError("No changes detected")

    test_case.last_modified_by_id = current_user.id
    test_case.version += 1
    test_case.updated_at = datetime.utcnow()

    create_version_log(
        db=db,
        test_case=test_case,
        changed_by_id=current_user.id,
        change_summary=update_data.change_summary,
        changed_fields=changed_fields
    )

    db.commit()
    db.refresh(test_case)

    return test_case

@router.delete("/{test_case_id}", status_code=status.HTTP_200_OK)
async def delete_test_case(
    test_case_id: int,
    delete_data: DeleteTestCaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Soft delete test case (confirmation required)."""

    if not delete_data.confirm:
        raise ValidationError("Deletion confirmation is required")

    test_case = db.query(TestCase).filter(
        TestCase.id == test_case_id,
        TestCase.is_deleted == False
    ).first()

    if not test_case:
        raise ResourceNotFoundError("Test case")

    ensure_edit_access(test_case, current_user)

    test_case.is_deleted = True
    test_case.deleted_at = datetime.utcnow()
    test_case.deleted_by_id = current_user.id

    create_version_log(
        db=db,
        test_case=test_case,
        changed_by_id=current_user.id,
        change_summary="Soft deleted test case",
        changed_fields=["is_deleted", "deleted_at", "deleted_by_id"]
    )

    db.commit()

    return {"message": f"Test case {test_case.test_case_id} deleted successfully"}

# ============ Test Steps ============

@router.post("/{test_case_id}/steps", response_model=TestStepResponse, status_code=status.HTTP_201_CREATED)
async def add_test_step(
    test_case_id: int,
    step_data: TestStepCreate,
    change_summary: str = Query(..., min_length=5, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Add a step to test case"""
    
    test_case = db.query(TestCase).filter(
        TestCase.id == test_case_id,
        TestCase.is_deleted == False
    ).first()
    
    if not test_case:
        raise ResourceNotFoundError("Test case")

    ensure_edit_access(test_case, current_user)

    step = TestStep(
        test_case_id=test_case_id,
        step_number=step_data.step_number,
        action=step_data.action,
        test_data=step_data.test_data,
        expected_result=step_data.expected_result
    )
    
    db.add(step)
    
    # Update test case metadata
    test_case.last_modified_by_id = current_user.id
    test_case.version += 1
    test_case.updated_at = datetime.utcnow()

    create_version_log(
        db=db,
        test_case=test_case,
        changed_by_id=current_user.id,
        change_summary=change_summary,
        changed_fields=["steps"]
    )

    db.commit()
    db.refresh(step)

    return step

@router.put("/steps/{step_id}", response_model=TestStepResponse)
async def update_test_step(
    step_id: int,
    step_data: TestStepUpdate,
    change_summary: str = Query(..., min_length=5, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Update test step"""
    
    step = db.query(TestStep).filter(TestStep.id == step_id).first()
    
    if not step:
        raise ResourceNotFoundError("Test step")

    ensure_edit_access(step.test_case, current_user)

    # Update fields
    update_dict = step_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(step, field, value)
    
    step.updated_at = datetime.utcnow()
    
    # Update test case metadata
    test_case = step.test_case
    test_case.last_modified_by_id = current_user.id
    test_case.version += 1
    test_case.updated_at = datetime.utcnow()

    create_version_log(
        db=db,
        test_case=test_case,
        changed_by_id=current_user.id,
        change_summary=change_summary,
        changed_fields=["steps"]
    )

    db.commit()
    db.refresh(step)

    return step

@router.delete("/steps/{step_id}", status_code=status.HTTP_200_OK)
async def delete_test_step(
    step_id: int,
    change_summary: str = Query(..., min_length=5, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Delete test step"""
    
    step = db.query(TestStep).filter(TestStep.id == step_id).first()
    
    if not step:
        raise ResourceNotFoundError("Test step")

    ensure_edit_access(step.test_case, current_user)

    test_case_id = step.test_case_id

    db.delete(step)
    
    # Update test case metadata
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if test_case:
        test_case.last_modified_by_id = current_user.id
        test_case.version += 1
        test_case.updated_at = datetime.utcnow()
        create_version_log(
            db=db,
            test_case=test_case,
            changed_by_id=current_user.id,
            change_summary=change_summary,
            changed_fields=["steps"]
        )

    db.commit()
    
    return {"message": "Test step deleted successfully"}

# ============ Tags ============

@router.get("/tags/list", response_model=List[TagResponse])
async def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available tags"""
    
    tags = db.query(Tag).order_by(Tag.name).all()
    return tags

@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    """Create a new tag"""
    
    # Check if tag already exists
    existing = db.query(Tag).filter(Tag.name == tag_data.name.lower()).first()
    if existing:
        return existing
    
    tag = Tag(name=tag_data.name.lower(), color=tag_data.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return tag

# ============ Statistics ============

@router.get("/stats/overview", response_model=TestCaseStatsResponse)
async def get_test_case_stats(
    project_id: Optional[int] = Query(None, description="Filter by project"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get test case statistics"""
    
    # Base query
    query = db.query(TestCase).filter(TestCase.is_deleted == False)
    
    if project_id:
        query = query.filter(TestCase.project_id == project_id)
    
    total = query.count()
    
    # Count by status
    by_status = {}
    for status_enum in TestCaseStatusEnum:
        count = query.filter(TestCase.status == status_enum.value).count()
        by_status[status_enum.value] = count
    
    # Count by priority
    by_priority = {}
    for priority_enum in PriorityEnum:
        count = query.filter(TestCase.priority == priority_enum.value).count()
        by_priority[priority_enum.value] = count
    
    # Count by type
    by_type = {}
    for type_enum in TestTypeEnum:
        count = query.filter(TestCase.type == type_enum.value).count()
        by_type[type_enum.value] = count
    
    # Count by automation status
    by_automation = {}
    for auto_enum in AutomationStatusEnum:
        count = query.filter(TestCase.automation_status == auto_enum.value).count()
        by_automation[auto_enum.value] = count
    
    # Average steps per test case
    avg_steps = db.query(func.avg(func.count(TestStep.id))).join(TestCase).filter(
        TestCase.is_deleted == False
    ).group_by(TestCase.id).scalar() or 0
    
    # Average duration
    avg_duration = db.query(func.avg(TestCase.estimated_duration)).filter(
        TestCase.is_deleted == False,
        TestCase.estimated_duration.isnot(None)
    ).scalar()
    
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_type": by_type,
        "by_automation_status": by_automation,
        "average_steps": float(avg_steps),
        "average_duration": float(avg_duration) if avg_duration else None
    }


# ============ Execution Module ============

@router.post("/{test_case_id}/executions/start", status_code=status.HTTP_201_CREATED)
async def start_test_execution(
    test_case_id: int,
    payload: CreateExecutionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id, TestCase.is_deleted == False).first()
    if not test_case:
        raise ResourceNotFoundError("Test case")

    execution = TestExecution(
        test_case_id=test_case.id,
        executed_by_id=current_user.id,
        status=StepStatusEnum.NOT_EXECUTED.value,
        environment=payload.environment,
        browser=payload.browser,
        os=payload.os,
        notes=payload.notes
    )
    db.add(execution)
    db.flush()

    timer = ExecutionTimerSession(
        execution_id=execution.id,
        started_at=datetime.utcnow(),
        is_running=True
    )
    db.add(timer)
    db.commit()
    db.refresh(execution)

    return {
        "execution_id": execution.id,
        "test_case_id": test_case.id,
        "started_at": timer.started_at,
        "status": execution.status,
        "message": "Execution started"
    }


@router.post("/executions/{execution_id}/steps/{step_id}/autosave", status_code=status.HTTP_200_OK)
async def autosave_execution_step(
    execution_id: int,
    step_id: int,
    payload: StepExecutionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise ResourceNotFoundError("Execution")

    step = db.query(TestStep).filter(TestStep.id == step_id, TestStep.test_case_id == execution.test_case_id).first()
    if not step:
        raise ResourceNotFoundError("Step")

    step.status = payload.status.value if hasattr(payload.status, "value") else payload.status
    step.actual_result = payload.actual_result
    step.notes = payload.notes
    step.updated_at = datetime.utcnow()

    steps = db.query(TestStep).filter(TestStep.test_case_id == execution.test_case_id).all()
    statuses = [s.status for s in steps]
    execution.pass_count = len([s for s in statuses if s == StepStatusEnum.PASS.value])
    execution.fail_count = len([s for s in statuses if s == StepStatusEnum.FAIL.value])
    execution.blocked_count = len([s for s in statuses if s == StepStatusEnum.BLOCKED.value])
    execution.skipped_count = len([s for s in statuses if s == StepStatusEnum.SKIPPED.value])
    if execution.fail_count > 0:
        execution.status = StepStatusEnum.FAIL.value
    elif execution.blocked_count > 0:
        execution.status = StepStatusEnum.BLOCKED.value
    elif any(s == StepStatusEnum.NOT_EXECUTED.value for s in statuses):
        execution.status = StepStatusEnum.NOT_EXECUTED.value
    elif execution.pass_count > 0 and execution.pass_count == len(statuses):
        execution.status = StepStatusEnum.PASS.value
    else:
        execution.status = StepStatusEnum.SKIPPED.value

    db.commit()

    return {
        "execution_id": execution.id,
        "step_id": step.id,
        "saved": True,
        "overall_status": execution.status,
        "pass_count": execution.pass_count,
        "fail_count": execution.fail_count,
        "blocked_count": execution.blocked_count,
        "skipped_count": execution.skipped_count
    }


@router.post("/executions/{execution_id}/complete", status_code=status.HTTP_200_OK)
async def complete_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise ResourceNotFoundError("Execution")

    timer = db.query(ExecutionTimerSession).filter(
        ExecutionTimerSession.execution_id == execution.id
    ).order_by(ExecutionTimerSession.created_at.desc()).first()

    if timer and timer.is_running:
        if timer.paused_at:
            timer.total_paused_seconds += max(0, int((datetime.utcnow() - timer.paused_at).total_seconds()))
            timer.paused_at = None
        timer.ended_at = datetime.utcnow()
        timer.is_running = False
        execution.execution_duration = calculate_execution_duration_minutes(timer)

    execution.execution_date = datetime.utcnow()
    db.commit()
    db.refresh(execution)

    return {
        "execution_id": execution.id,
        "status": execution.status,
        "execution_duration_minutes": execution.execution_duration,
        "pass_count": execution.pass_count,
        "fail_count": execution.fail_count,
        "blocked_count": execution.blocked_count,
        "skipped_count": execution.skipped_count
    }


@router.get("/{test_case_id}/executions/history", status_code=status.HTTP_200_OK)
async def execution_history(
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = db.query(TestExecution).filter(
        TestExecution.test_case_id == test_case_id
    ).order_by(TestExecution.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "test_case_id": e.test_case_id,
            "status": e.status,
            "execution_date": e.execution_date,
            "execution_duration": e.execution_duration,
            "pass_count": e.pass_count,
            "fail_count": e.fail_count,
            "blocked_count": e.blocked_count,
            "skipped_count": e.skipped_count,
            "notes": e.notes,
            "bug_ids": e.bug_ids,
        }
        for e in rows
    ]


@router.post("/{test_case_id}/executions/reexecute", status_code=status.HTTP_201_CREATED)
async def reexecute_test_case(
    test_case_id: int,
    payload: CreateExecutionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id, TestCase.is_deleted == False).first()
    if not test_case:
        raise ResourceNotFoundError("Test case")

    previous = db.query(TestExecution).filter(
        TestExecution.test_case_id == test_case_id
    ).order_by(TestExecution.created_at.desc()).first()

    execution = TestExecution(
        test_case_id=test_case.id,
        executed_by_id=current_user.id,
        status=StepStatusEnum.NOT_EXECUTED.value,
        environment=payload.environment,
        browser=payload.browser,
        os=payload.os,
        notes=payload.notes
    )
    db.add(execution)
    db.flush()

    timer = ExecutionTimerSession(
        execution_id=execution.id,
        started_at=datetime.utcnow(),
        is_running=True
    )
    db.add(timer)
    db.commit()

    return {
        "execution_id": execution.id,
        "previous_execution": {
            "id": previous.id,
            "status": previous.status,
            "execution_date": previous.execution_date,
            "execution_duration": previous.execution_duration,
            "pass_count": previous.pass_count,
            "fail_count": previous.fail_count,
            "blocked_count": previous.blocked_count,
            "skipped_count": previous.skipped_count,
        } if previous else None,
        "message": "Re-execution started"
    }


@router.post("/executions/{execution_id}/steps/{step_id}/fail-and-create-bug", status_code=status.HTTP_201_CREATED)
async def fail_and_create_bug(
    execution_id: int,
    step_id: int,
    payload: FailAndCreateBugRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise ResourceNotFoundError("Execution")

    step = db.query(TestStep).filter(TestStep.id == step_id, TestStep.test_case_id == execution.test_case_id).first()
    if not step:
        raise ResourceNotFoundError("Step")

    step.status = StepStatusEnum.FAIL.value
    step.actual_result = payload.description or payload.summary
    step.notes = payload.description

    bug_id = f"BUG-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    existing_bug_ids = [b.strip() for b in (execution.bug_ids or "").split(",") if b.strip()]
    existing_bug_ids.append(bug_id)
    execution.bug_ids = ", ".join(existing_bug_ids)
    execution.status = StepStatusEnum.FAIL.value

    db.commit()

    return {
        "execution_id": execution.id,
        "step_id": step.id,
        "bug": {
            "id": bug_id,
            "summary": payload.summary,
            "description": payload.description,
            "linked_test_case_id": execution.test_case_id,
            "linked_step_id": step.id,
            "created_by_id": current_user.id,
        },
        "message": "Step failed and bug report created"
    }


@router.post("/executions/{execution_id}/timer/pause", status_code=status.HTTP_200_OK)
async def pause_execution_timer(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    timer = db.query(ExecutionTimerSession).filter(
        ExecutionTimerSession.execution_id == execution_id,
        ExecutionTimerSession.is_running == True
    ).order_by(ExecutionTimerSession.created_at.desc()).first()
    if not timer:
        raise HTTPException(status_code=400, detail="No running timer found")
    if timer.paused_at:
        raise HTTPException(status_code=400, detail="Timer is already paused")

    timer.paused_at = datetime.utcnow()
    db.commit()
    return {"execution_id": execution_id, "paused": True, "paused_at": timer.paused_at}


@router.post("/executions/{execution_id}/timer/resume", status_code=status.HTTP_200_OK)
async def resume_execution_timer(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    timer = db.query(ExecutionTimerSession).filter(
        ExecutionTimerSession.execution_id == execution_id,
        ExecutionTimerSession.is_running == True
    ).order_by(ExecutionTimerSession.created_at.desc()).first()
    if not timer:
        raise HTTPException(status_code=400, detail="No running timer found")
    if not timer.paused_at:
        raise HTTPException(status_code=400, detail="Timer is not paused")

    timer.total_paused_seconds += max(0, int((datetime.utcnow() - timer.paused_at).total_seconds()))
    timer.paused_at = None
    db.commit()
    return {"execution_id": execution_id, "resumed": True}


@router.post("/executions/{execution_id}/timer/manual", status_code=status.HTTP_200_OK)
async def set_manual_duration(
    execution_id: int,
    payload: ManualDurationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    timer = db.query(ExecutionTimerSession).filter(
        ExecutionTimerSession.execution_id == execution_id
    ).order_by(ExecutionTimerSession.created_at.desc()).first()
    if not timer:
        raise ResourceNotFoundError("Execution timer")

    timer.manual_duration_minutes = payload.duration_minutes
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if execution:
        execution.execution_duration = payload.duration_minutes
    db.commit()
    return {"execution_id": execution_id, "manual_duration_minutes": payload.duration_minutes}


@router.post("/executions/{execution_id}/evidence", status_code=status.HTTP_201_CREATED)
async def upload_execution_evidence(
    execution_id: int,
    step_id: Optional[int] = Query(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise ResourceNotFoundError("Execution")

    if step_id is not None:
        step = db.query(TestStep).filter(TestStep.id == step_id, TestStep.test_case_id == execution.test_case_id).first()
        if not step:
            raise ResourceNotFoundError("Step")

    evidence_type = get_evidence_type(file.filename, file.content_type)
    content = await file.read()
    if len(content) > EVIDENCE_LIMITS[evidence_type]:
        max_mb = EVIDENCE_LIMITS[evidence_type] // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"{evidence_type} exceeds max size of {max_mb}MB")

    upload_dir = Path(__file__).resolve().parents[3] / "uploads" / "execution_evidence"
    upload_dir.mkdir(parents=True, exist_ok=True)
    generated_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}_{file.filename}"
    target = upload_dir / generated_name
    with open(target, "wb") as output:
        output.write(content)

    evidence = ExecutionEvidence(
        execution_id=execution.id,
        test_case_id=execution.test_case_id,
        step_id=step_id,
        evidence_type=evidence_type,
        filename=file.filename,
        file_path=str(target),
        file_size=len(content),
        mime_type=file.content_type,
        uploaded_by_id=current_user.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {
        "id": evidence.id,
        "execution_id": evidence.execution_id,
        "step_id": evidence.step_id,
        "evidence_type": evidence.evidence_type,
        "filename": evidence.filename,
        "file_size": evidence.file_size,
        "mime_type": evidence.mime_type,
        "uploaded_at": evidence.uploaded_at,
    }


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_test_run(
    payload: CreateTestRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    test_run = TestRun(
        name=payload.name,
        description=payload.description,
        target_start_date=payload.target_start_date,
        target_end_date=payload.target_end_date,
        status="in_progress" if payload.test_case_ids else "planned",
        created_by_id=current_user.id,
    )
    db.add(test_run)
    db.flush()

    tester_ids = payload.tester_ids if payload.tester_ids else [None]
    for index, test_case_id in enumerate(payload.test_case_ids):
        assigned_tester_id = tester_ids[index % len(tester_ids)] if tester_ids else None
        item = TestRunItem(
            test_run_id=test_run.id,
            test_case_id=test_case_id,
            assigned_tester_id=assigned_tester_id,
            status=StepStatusEnum.NOT_EXECUTED.value,
        )
        db.add(item)

    db.commit()
    db.refresh(test_run)

    items = db.query(TestRunItem).filter(TestRunItem.test_run_id == test_run.id).all()
    return {
        "id": test_run.id,
        "name": test_run.name,
        "description": test_run.description,
        "target_start_date": test_run.target_start_date,
        "target_end_date": test_run.target_end_date,
        "status": test_run.status,
        "progress": compute_run_progress(items),
    }


@router.get("/runs", status_code=status.HTTP_200_OK)
async def list_test_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    runs = db.query(TestRun).order_by(TestRun.created_at.desc()).all()
    result = []
    for run in runs:
        items = db.query(TestRunItem).filter(TestRunItem.test_run_id == run.id).all()
        result.append({
            "id": run.id,
            "name": run.name,
            "description": run.description,
            "target_start_date": run.target_start_date,
            "target_end_date": run.target_end_date,
            "status": run.status,
            "progress": compute_run_progress(items),
        })
    return result


@router.get("/runs/{run_id}", status_code=status.HTTP_200_OK)
async def get_test_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise ResourceNotFoundError("Test run")

    items = db.query(TestRunItem).options(joinedload(TestRunItem.test_case)).filter(
        TestRunItem.test_run_id == run.id
    ).all()
    return {
        "id": run.id,
        "name": run.name,
        "description": run.description,
        "target_start_date": run.target_start_date,
        "target_end_date": run.target_end_date,
        "status": run.status,
        "progress": compute_run_progress(items),
        "items": [
            {
                "id": item.id,
                "test_case_id": item.test_case_id,
                "test_case_identifier": item.test_case.test_case_id if item.test_case else None,
                "test_case_title": item.test_case.title if item.test_case else None,
                "assigned_tester_id": item.assigned_tester_id,
                "status": item.status,
                "latest_execution_id": item.latest_execution_id,
            }
            for item in items
        ]
    }


@router.put("/runs/{run_id}/assign", status_code=status.HTTP_200_OK)
async def assign_test_run(
    run_id: int,
    payload: UpdateTestRunAssignmentsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise ResourceNotFoundError("Test run")

    items = db.query(TestRunItem).filter(TestRunItem.test_run_id == run.id).order_by(TestRunItem.id.asc()).all()
    if len(items) == 0:
        return {"run_id": run.id, "assigned": 0, "message": "No test cases in run"}

    if len(payload.tester_ids) == 0:
        for item in items:
            item.assigned_tester_id = None
    else:
        for index, item in enumerate(items):
            item.assigned_tester_id = payload.tester_ids[index % len(payload.tester_ids)]

    run.updated_at = datetime.utcnow()
    db.commit()

    return {
        "run_id": run.id,
        "assigned": len(items),
        "tester_ids": payload.tester_ids,
        "message": "Assignments updated"
    }

# ============ Version / Clone / Delete Admin ============

@router.get("/{test_case_id}/versions", response_model=List[TestCaseVersionHistoryResponse])
async def get_test_case_versions(
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not test_case:
        raise ResourceNotFoundError("Test case")

    versions = db.query(TestCaseVersionHistory).filter(
        TestCaseVersionHistory.test_case_id == test_case_id
    ).order_by(TestCaseVersionHistory.version_number.desc()).all()
    return versions


@router.post("/{test_case_id}/clone", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def clone_test_case(
    test_case_id: int,
    clone_data: CloneTestCaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    source = db.query(TestCase).options(
        joinedload(TestCase.steps),
        joinedload(TestCase.tags),
        joinedload(TestCase.attachments)
    ).filter(TestCase.id == test_case_id, TestCase.is_deleted == False).first()

    if not source:
        raise ResourceNotFoundError("Test case")

    cloned = TestCase(
        test_case_id=generate_test_case_id(db, source.project_id),
        title=source.title,
        description=source.description,
        module=source.module,
        priority=source.priority,
        severity=source.severity,
        type=source.type,
        status=TestCaseStatusEnum.DRAFT.value,
        pre_conditions=source.pre_conditions,
        test_data_requirements=source.test_data_requirements,
        environment_requirements=source.environment_requirements,
        post_conditions=source.post_conditions,
        cleanup_steps=source.cleanup_steps,
        project_id=source.project_id,
        created_by_id=current_user.id,
        owner_id=current_user.id,
        assigned_tester_id=source.assigned_tester_id,
        last_modified_by_id=current_user.id,
        estimated_duration=source.estimated_duration,
        automation_status=source.automation_status,
        automation_script_link=source.automation_script_link,
        version=1
    )
    db.add(cloned)
    db.flush()

    for step in source.steps:
        db.add(TestStep(
            test_case_id=cloned.id,
            step_number=step.step_number,
            action=step.action,
            test_data=step.test_data,
            expected_result=step.expected_result
        ))

    cloned.tags = source.tags[:]

    if clone_data.clone_attachments:
        for attachment in source.attachments:
            db.add(TestCaseAttachment(
                test_case_id=cloned.id,
                filename=attachment.filename,
                file_path=attachment.file_path,
                file_size=attachment.file_size,
                file_type=attachment.file_type,
                uploaded_by_id=current_user.id,
                description=attachment.description
            ))

    create_version_log(
        db=db,
        test_case=cloned,
        changed_by_id=current_user.id,
        change_summary=f"Cloned from {source.test_case_id}",
        changed_fields=["clone"]
    )

    db.commit()
    db.refresh(cloned)
    return cloned


@router.post("/{test_case_id}/restore", status_code=status.HTTP_200_OK)
async def restore_test_case(
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id, TestCase.is_deleted == True).first()
    if not test_case:
        raise ResourceNotFoundError("Deleted test case")

    test_case.is_deleted = False
    test_case.deleted_at = None
    test_case.deleted_by_id = None
    test_case.last_modified_by_id = current_user.id
    test_case.version += 1

    create_version_log(
        db=db,
        test_case=test_case,
        changed_by_id=current_user.id,
        change_summary="Restored soft deleted test case",
        changed_fields=["is_deleted"]
    )

    db.commit()
    return {"message": f"Restored {test_case.test_case_id}"}


@router.delete("/{test_case_id}/permanent", status_code=status.HTTP_200_OK)
async def permanently_delete_test_case(
    test_case_id: int,
    delete_data: DeleteTestCaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    if not delete_data.confirm:
        raise ValidationError("Deletion confirmation is required")

    test_case = db.query(TestCase).filter(TestCase.id == test_case_id, TestCase.is_deleted == True).first()
    if not test_case:
        raise ResourceNotFoundError("Deleted test case")

    db.delete(test_case)
    db.commit()
    return {"message": "Test case permanently deleted"}


# ============ Templates ============

@router.post("/templates", response_model=TestCaseTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template_from_test_case(
    payload: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    test_case = db.query(TestCase).options(joinedload(TestCase.steps), joinedload(TestCase.tags)).filter(
        TestCase.id == payload.test_case_id,
        TestCase.is_deleted == False
    ).first()
    if not test_case:
        raise ResourceNotFoundError("Test case")

    template_payload = {
        "title": test_case.title,
        "description": test_case.description,
        "module": test_case.module,
        "priority": test_case.priority.value,
        "severity": test_case.severity.value,
        "type": test_case.type.value,
        "pre_conditions": test_case.pre_conditions,
        "test_data_requirements": test_case.test_data_requirements,
        "environment_requirements": test_case.environment_requirements,
        "post_conditions": test_case.post_conditions,
        "cleanup_steps": test_case.cleanup_steps,
        "estimated_duration": test_case.estimated_duration,
        "automation_status": test_case.automation_status.value,
        "automation_script_link": test_case.automation_script_link,
        "tags": [tag.name for tag in test_case.tags],
        "steps": [
            {
                "step_number": step.step_number,
                "action": step.action,
                "test_data": step.test_data,
                "expected_result": step.expected_result
            }
            for step in test_case.steps
        ]
    }

    template = TestCaseTemplate(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        source_test_case_id=test_case.id,
        payload=json.dumps(template_payload),
        created_by_id=current_user.id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/templates", response_model=List[TestCaseTemplateResponse])
async def list_templates(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TestCaseTemplate)
    if category:
        query = query.filter(TestCaseTemplate.category == category)
    return query.order_by(TestCaseTemplate.name.asc()).all()


@router.post("/templates/{template_id}/create", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case_from_template(
    template_id: int,
    payload: CreateFromTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    template = db.query(TestCaseTemplate).filter(TestCaseTemplate.id == template_id).first()
    if not template:
        raise ResourceNotFoundError("Template")

    template_data = json.loads(template.payload)
    final_module = payload.module if payload.module else template_data.get("module")

    test_case = TestCase(
        test_case_id=generate_test_case_id(db, payload.project_id),
        title=template_data.get("title"),
        description=template_data.get("description"),
        module=final_module,
        priority=PriorityEnum(template_data.get("priority", PriorityEnum.MEDIUM.value)).value,
        severity=SeverityEnum(template_data.get("severity", SeverityEnum.MINOR.value)).value,
        type=TestTypeEnum(template_data.get("type", TestTypeEnum.FUNCTIONAL.value)).value,
        status=TestCaseStatusEnum.DRAFT.value,
        pre_conditions=template_data.get("pre_conditions"),
        test_data_requirements=template_data.get("test_data_requirements"),
        environment_requirements=template_data.get("environment_requirements"),
        post_conditions=template_data.get("post_conditions"),
        cleanup_steps=template_data.get("cleanup_steps"),
        project_id=payload.project_id,
        created_by_id=current_user.id,
        owner_id=current_user.id,
        assigned_tester_id=payload.assigned_tester_id,
        last_modified_by_id=current_user.id,
        estimated_duration=template_data.get("estimated_duration"),
        automation_status=AutomationStatusEnum(template_data.get("automation_status", AutomationStatusEnum.NOT_AUTOMATED.value)),
        automation_script_link=template_data.get("automation_script_link"),
        version=1
    )
    db.add(test_case)
    db.flush()

    for step in template_data.get("steps", []):
        db.add(TestStep(
            test_case_id=test_case.id,
            step_number=step.get("step_number"),
            action=step.get("action"),
            test_data=step.get("test_data"),
            expected_result=step.get("expected_result")
        ))

    tags = template_data.get("tags", [])
    if tags:
        test_case.tags = get_or_create_tags(db, tags)

    create_version_log(
        db=db,
        test_case=test_case,
        changed_by_id=current_user.id,
        change_summary=f"Created from template {template.name}",
        changed_fields=["template_create"]
    )

    db.commit()
    db.refresh(test_case)
    return test_case


# ============ Bulk Operations ============

@router.post("/bulk/update", status_code=status.HTTP_200_OK)
async def bulk_update_test_cases(
    payload: BulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    test_cases = db.query(TestCase).filter(
        TestCase.id.in_(payload.test_case_ids),
        TestCase.is_deleted == False
    ).all()

    updated = 0
    for test_case in test_cases:
        ensure_edit_access(test_case, current_user)
        changed_fields = []
        if payload.status is not None:
            test_case.status = payload.status
            changed_fields.append("status")
        if payload.priority is not None:
            test_case.priority = payload.priority
            changed_fields.append("priority")
        if payload.severity is not None:
            test_case.severity = payload.severity
            changed_fields.append("severity")
        if payload.assigned_tester_id is not None:
            test_case.assigned_tester_id = payload.assigned_tester_id
            changed_fields.append("assigned_tester_id")
        if payload.module is not None:
            test_case.module = payload.module
            changed_fields.append("module")

        if changed_fields:
            test_case.last_modified_by_id = current_user.id
            test_case.version += 1
            test_case.updated_at = datetime.utcnow()
            create_version_log(
                db=db,
                test_case=test_case,
                changed_by_id=current_user.id,
                change_summary=payload.change_summary,
                changed_fields=changed_fields
            )
            updated += 1

    db.commit()
    return {"message": f"Updated {updated} test cases"}


@router.post("/bulk/delete", status_code=status.HTTP_200_OK)
async def bulk_delete_test_cases(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    if not payload.confirm:
        raise ValidationError("Bulk deletion confirmation is required")

    test_cases = db.query(TestCase).filter(
        TestCase.id.in_(payload.test_case_ids),
        TestCase.is_deleted == False
    ).all()

    deleted = 0
    for test_case in test_cases:
        ensure_edit_access(test_case, current_user)
        test_case.is_deleted = True
        test_case.deleted_at = datetime.utcnow()
        test_case.deleted_by_id = current_user.id
        create_version_log(
            db=db,
            test_case=test_case,
            changed_by_id=current_user.id,
            change_summary="Bulk soft delete",
            changed_fields=["is_deleted", "deleted_at", "deleted_by_id"]
        )
        deleted += 1

    db.commit()
    return {"message": f"Deleted {deleted} test cases"}


@router.get("/bulk/export", status_code=status.HTTP_200_OK)
async def bulk_export_test_cases(
    test_case_ids: str = Query(..., description="Comma separated test case IDs"),
    format: str = Query("csv", description="csv or excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ids = [int(item.strip()) for item in test_case_ids.split(",") if item.strip().isdigit()]
    test_cases = db.query(TestCase).filter(TestCase.id.in_(ids), TestCase.is_deleted == False).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["test_case_id", "title", "module", "priority", "severity", "type", "status", "assigned_tester_id"])
    for tc in test_cases:
        writer.writerow([
            tc.test_case_id,
            tc.title,
            tc.module,
            tc.priority.value,
            tc.severity.value,
            tc.type.value,
            tc.status.value,
            tc.assigned_tester_id
        ])

    media_type = "text/csv" if format == "csv" else "application/vnd.ms-excel"
    filename = "test_cases_export.csv" if format == "csv" else "test_cases_export.xls"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ Import ============

@router.post("/import/preview", response_model=ImportPreviewResponse, status_code=status.HTTP_201_CREATED)
async def preview_import_test_cases(
    payload: ImportPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    errors: List[str] = []
    preview_rows: List[dict] = []
    valid_count = 0

    if payload.format.lower() not in {"csv", "excel", "json"}:
        raise ValidationError("format must be one of: csv, excel, json")

    for idx, record in enumerate(payload.records):
        mapped = {}
        for source_field, target_field in payload.field_mapping.items():
            mapped[target_field] = record.get(source_field)

        title = mapped.get("title")
        module = mapped.get("module")
        if not title:
            errors.append(f"Row {idx + 1}: title is required")
        if not module:
            errors.append(f"Row {idx + 1}: module is required")

        mapped["row_number"] = idx + 1
        preview_rows.append(mapped)

    valid_count = max(len(payload.records) - len({err.split(':')[0] for err in errors}), 0)

    batch = TestCaseImportBatch(
        format=payload.format.lower(),
        field_mapping=json.dumps(payload.field_mapping),
        preview_payload=json.dumps({"project_id": payload.project_id, "rows": preview_rows}),
        validation_errors=json.dumps(errors) if errors else None,
        created_by_id=current_user.id
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "valid_records": valid_count,
        "invalid_records": len(payload.records) - valid_count,
        "errors": errors,
        "preview": preview_rows[:25]
    }


@router.post("/import/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_import_test_cases(
    payload: ImportConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tester)
):
    if not payload.confirm:
        raise ValidationError("Import confirmation is required")

    batch = db.query(TestCaseImportBatch).filter(TestCaseImportBatch.id == payload.batch_id).first()
    if not batch:
        raise ResourceNotFoundError("Import batch")

    data = json.loads(batch.preview_payload)
    project_id = data.get("project_id")
    rows = data.get("rows", [])

    created = 0
    skipped = 0
    for row in rows:
        title = row.get("title")
        module = row.get("module")
        if not title or not module:
            skipped += 1
            continue

        test_case = TestCase(
            test_case_id=generate_test_case_id(db, project_id),
            title=title,
            description=row.get("description"),
            module=module,
            priority=PriorityEnum(row.get("priority", PriorityEnum.MEDIUM.value)).value,
            severity=SeverityEnum(row.get("severity", SeverityEnum.MINOR.value)).value,
            type=TestTypeEnum(row.get("type", TestTypeEnum.FUNCTIONAL.value)).value,
            status=TestCaseStatusEnum.DRAFT.value,
            project_id=project_id,
            created_by_id=current_user.id,
            owner_id=current_user.id,
            assigned_tester_id=row.get("assigned_tester_id"),
            last_modified_by_id=current_user.id,
            version=1
        )
        db.add(test_case)
        db.flush()

        create_version_log(
            db=db,
            test_case=test_case,
            changed_by_id=current_user.id,
            change_summary="Imported from external source",
            changed_fields=["import_create"]
        )
        created += 1

    db.commit()
    return {"message": f"Imported {created} test cases", "created": created, "skipped": skipped}
