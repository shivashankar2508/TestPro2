from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, case, desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.test_case import BugReport, BugStatusEnum, ExecutionEvidence, PriorityEnum, SeverityEnum, TestCase
from app.models.user import RoleEnum, User
from app.utils.auth_middleware import get_current_user
from app.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/api/bugs", tags=["Bug Reports"])


BUG_STATUS_TRANSITIONS = {
    BugStatusEnum.NEW.value: {BugStatusEnum.OPEN.value, BugStatusEnum.WONT_FIX.value, BugStatusEnum.DUPLICATE.value},
    BugStatusEnum.OPEN.value: {BugStatusEnum.IN_PROGRESS.value},
    BugStatusEnum.IN_PROGRESS.value: {BugStatusEnum.FIXED.value},
    BugStatusEnum.FIXED.value: {BugStatusEnum.VERIFIED.value, BugStatusEnum.REOPENED.value},
    BugStatusEnum.VERIFIED.value: {BugStatusEnum.CLOSED.value},
    BugStatusEnum.REOPENED.value: {BugStatusEnum.IN_PROGRESS.value},
    BugStatusEnum.WONT_FIX.value: set(),
    BugStatusEnum.DUPLICATE.value: set(),
    BugStatusEnum.CLOSED.value: set(),
}


class BugCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=3)
    steps_to_reproduce: str = Field(..., min_length=3)
    expected_behavior: str = Field(..., min_length=3)
    actual_behavior: str = Field(..., min_length=3)
    severity: SeverityEnum
    priority: PriorityEnum
    environment: Optional[str] = None
    affected_version: Optional[str] = Field(None, max_length=100)
    assigned_to_id: Optional[int] = None
    linked_test_case_id: Optional[int] = None
    linked_execution_id: Optional[int] = None
    linked_step_id: Optional[int] = None
    due_date: Optional[datetime] = None


class BugStatusUpdateRequest(BaseModel):
    status: str


def generate_bug_id(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(BugReport).filter(BugReport.bug_id.like(f"BUG-{year}-%")).count()
    return f"BUG-{year}-{str(count + 1).zfill(5)}"


def can_manage_bug(current_user: User, bug: BugReport) -> bool:
    if current_user.role == RoleEnum.ADMIN.value:
        return True
    if bug.assigned_to_id == current_user.id:
        return True
    if bug.created_by_id == current_user.id:
        return True
    return False


def serialize_bug(db: Session, bug: BugReport) -> dict:
    linked_test_case_identifier = None
    if bug.test_case:
        linked_test_case_identifier = bug.test_case.test_case_id

    evidence = []
    if bug.linked_execution_id:
        evidence = db.query(ExecutionEvidence).filter(
            ExecutionEvidence.execution_id == bug.linked_execution_id
        ).order_by(ExecutionEvidence.uploaded_at.desc()).all()

    return {
        "id": bug.id,
        "bug_id": bug.bug_id,
        "title": bug.title,
        "description": bug.description,
        "steps_to_reproduce": bug.steps_to_reproduce,
        "expected_behavior": bug.expected_behavior,
        "actual_behavior": bug.actual_behavior,
        "severity": bug.severity,
        "priority": bug.priority,
        "status": bug.status,
        "environment": bug.environment,
        "affected_version": bug.affected_version,
        "due_date": bug.due_date,
        "created_at": bug.created_at,
        "updated_at": bug.updated_at,
        "created_by_id": bug.created_by_id,
        "assigned_to_id": bug.assigned_to_id,
        "assigned_to_name": bug.assigned_to.full_name if bug.assigned_to else None,
        "linked_test_case_id": bug.linked_test_case_id,
        "linked_test_case_identifier": linked_test_case_identifier,
        "linked_execution_id": bug.linked_execution_id,
        "linked_step_id": bug.linked_step_id,
        "attachment_count": len(evidence),
        "attachments": [
            {
                "filename": item.filename,
                "evidence_type": item.evidence_type,
                "uploaded_at": item.uploaded_at,
            }
            for item in evidence
        ],
    }


@router.get("/meta/assignees", status_code=status.HTTP_200_OK)
async def list_bug_assignees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = db.query(User).filter(User.role.in_([RoleEnum.DEVELOPER.value, RoleEnum.ADMIN.value])).order_by(User.full_name.asc()).all()
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        }
        for user in users
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bug_report(
    payload: BugCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.linked_test_case_id:
        test_case = db.query(TestCase).filter(TestCase.id == payload.linked_test_case_id).first()
        if not test_case:
            raise ResourceNotFoundError("Test case")

    bug = BugReport(
        bug_id=generate_bug_id(db),
        title=payload.title,
        description=payload.description,
        steps_to_reproduce=payload.steps_to_reproduce,
        expected_behavior=payload.expected_behavior,
        actual_behavior=payload.actual_behavior,
        severity=payload.severity.value if hasattr(payload.severity, "value") else payload.severity,
        priority=payload.priority.value if hasattr(payload.priority, "value") else payload.priority,
        status=BugStatusEnum.NEW.value,
        environment=payload.environment,
        affected_version=payload.affected_version,
        due_date=payload.due_date,
        created_by_id=current_user.id,
        assigned_to_id=payload.assigned_to_id,
        linked_test_case_id=payload.linked_test_case_id,
        linked_execution_id=payload.linked_execution_id,
        linked_step_id=payload.linked_step_id,
    )
    db.add(bug)
    db.commit()
    db.refresh(bug)
    return serialize_bug(db, bug)


@router.get("", status_code=status.HTTP_200_OK)
async def list_bugs(
    search: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_to_id: Optional[int] = Query(None),
    mine_only: bool = Query(False),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(BugReport)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(BugReport.bug_id.ilike(like), BugReport.title.ilike(like), BugReport.description.ilike(like)))
    if priority:
        query = query.filter(BugReport.priority == priority)
    if severity:
        query = query.filter(BugReport.severity == severity)
    if status_filter:
        query = query.filter(BugReport.status == status_filter)
    if assigned_to_id:
        query = query.filter(BugReport.assigned_to_id == assigned_to_id)
    if mine_only:
        query = query.filter(BugReport.assigned_to_id == current_user.id)

    priority_sort = case(
        (BugReport.priority == PriorityEnum.CRITICAL.value, 1),
        (BugReport.priority == PriorityEnum.HIGH.value, 2),
        (BugReport.priority == PriorityEnum.MEDIUM.value, 3),
        else_=4,
    )
    severity_sort = case(
        (BugReport.severity == SeverityEnum.BLOCKER.value, 1),
        (BugReport.severity == SeverityEnum.CRITICAL.value, 2),
        (BugReport.severity == SeverityEnum.MAJOR.value, 3),
        (BugReport.severity == SeverityEnum.MINOR.value, 4),
        else_=5,
    )

    sort_column = BugReport.created_at
    if sort_by == "priority":
        sort_column = priority_sort
    elif sort_by == "severity":
        sort_column = severity_sort
    elif sort_by == "due_date":
        sort_column = BugReport.due_date
    elif sort_by == "age":
        sort_column = BugReport.created_at

    order_fn = asc if sort_order == "asc" else desc
    bugs = query.order_by(order_fn(sort_column), desc(BugReport.created_at)).all()
    return [serialize_bug(db, bug) for bug in bugs]


@router.get("/{bug_identifier}", status_code=status.HTTP_200_OK)
async def get_bug_report(
    bug_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bug = db.query(BugReport).filter(BugReport.bug_id == bug_identifier).first()
    if not bug:
        raise ResourceNotFoundError("Bug report")
    return serialize_bug(db, bug)


@router.put("/{bug_identifier}/status", status_code=status.HTTP_200_OK)
async def update_bug_status(
    bug_identifier: str,
    payload: BugStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bug = db.query(BugReport).filter(BugReport.bug_id == bug_identifier).first()
    if not bug:
        raise ResourceNotFoundError("Bug report")
    if not can_manage_bug(current_user, bug):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this bug")

    new_status = payload.status.strip().lower().replace(" ", "_")
    if new_status not in BUG_STATUS_TRANSITIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bug status")
    if new_status != bug.status and new_status not in BUG_STATUS_TRANSITIONS.get(bug.status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {bug.status} to {new_status}"
        )

    bug.status = new_status
    bug.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bug)
    return serialize_bug(db, bug)
