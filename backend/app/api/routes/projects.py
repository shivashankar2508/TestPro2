from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.user import User, Project, ProjectMember, RoleEnum, AuditLog
from app.utils.auth_middleware import require_admin, get_current_user
from app.exceptions import ValidationError, PermissionDeniedError, ResourceNotFoundError
import logging

router = APIRouter(prefix="/api/projects", tags=["Projects"])
logger = logging.getLogger(__name__)

# ============ Pydantic Schemas ============

class ProjectMemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    added_at: datetime
    
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    lead_id: Optional[int] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    lead_id: Optional[int] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    lead_id: Optional[int]
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    project_members: List[ProjectMemberResponse]

class ProjectListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    projects: List[ProjectResponse]

class AddProjectMemberRequest(BaseModel):
    user_id: int
    role: str = Field(default="member", description="lead, tester, viewer, member")

# ============ Project Management Endpoints ============

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all projects (accessible projects for current user)"""
    try:
        query = db.query(Project)
        
        # Filter by status if provided
        if status:
            query = query.filter(Project.status == status.lower())
        
        # Search by name
        if search:
            search_term = f"%{search}%"
            query = query.filter(Project.name.ilike(search_term))
        
        # Admin sees all projects, others see only their projects
        if current_user.role != RoleEnum.ADMIN:
            query = query.filter(
                (Project.created_by_id == current_user.id) |
                (Project.project_members.any(ProjectMember.user_id == current_user.id))
            )
        
        total = query.count()
        offset = (page - 1) * page_size
        projects = query.order_by(desc(Project.created_at)).offset(offset).limit(page_size).all()
        
        return ProjectListResponse(
            total=total,
            page=page,
            page_size=page_size,
            projects=projects
        )
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list projects")

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_create: ProjectCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new project (Admin only)"""
    try:
        # Check if project name already exists
        existing = db.query(Project).filter(Project.name == project_create.name).first()
        if existing:
            raise ValidationError("Project name already exists")
        
        new_project = Project(
            name=project_create.name,
            description=project_create.description,
            status="active",
            lead_id=project_create.lead_id,
            created_by_id=current_user.id
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="project_created",
            resource_type="project",
            resource_id=new_project.id,
            details=f"Created project: {project_create.name}"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Project {new_project.id} created by admin {current_user.id}")
        return new_project
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project details"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ResourceNotFoundError("Project")
    
    # Check access
    is_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == current_user.id
    ).first()
    
    if current_user.role != RoleEnum.ADMIN and project.created_by_id != current_user.id and not is_member:
        raise PermissionDeniedError("Cannot access this project")
    
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update project (Admin only)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ResourceNotFoundError("Project")
    
    if project_update.name:
        # Check if new name already exists
        existing = db.query(Project).filter(
            Project.name == project_update.name,
            Project.id != project_id
        ).first()
        if existing:
            raise ValidationError("Project name already exists")
        project.name = project_update.name
    
    if project_update.description is not None:
        project.description = project_update.description
    
    if project_update.status:
        project.status = project_update.status.lower()
    
    if project_update.lead_id is not None:
        project.lead_id = project_update.lead_id
    
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="project_updated",
        resource_type="project",
        resource_id=project_id,
        details=f"Updated project: {project.name}"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Project {project_id} updated by admin {current_user.id}")
    return project

@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(
    project_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete project (Admin only)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ResourceNotFoundError("Project")
    
    project_name = project.name
    db.delete(project)
    db.commit()
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="project_deleted",
        resource_type="project",
        resource_id=project_id,
        details=f"Deleted project: {project_name}"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Project {project_id} deleted by admin {current_user.id}")
    return {"message": f"Project {project_name} deleted successfully"}

@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: int,
    member_request: AddProjectMemberRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Add member to project (Admin only)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ResourceNotFoundError("Project")
    
    user = db.query(User).filter(User.id == member_request.user_id).first()
    if not user:
        raise ResourceNotFoundError("User")
    
    # Check if already a member
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_request.user_id
    ).first()
    if existing:
        raise ValidationError("User is already a project member")
    
    project_member = ProjectMember(
        project_id=project_id,
        user_id=member_request.user_id,
        role=member_request.role.lower(),
        added_by_id=current_user.id
    )
    
    db.add(project_member)
    db.commit()
    db.refresh(project_member)
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="project_member_added",
        resource_type="project",
        resource_id=project_id,
        details=f"Added user {user.email} as {member_request.role} to project"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"User {member_request.user_id} added to project {project_id}")
    return {
        "message": f"User {user.email} added to project",
        "member": {
            "id": project_member.id,
            "user_id": project_member.user_id,
            "role": project_member.role
        }
    }

@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Remove member from project (Admin only)"""
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    
    if not member:
        raise ResourceNotFoundError("Project member")
    
    user = db.query(User).filter(User.id == user_id).first()
    db.delete(member)
    db.commit()
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="project_member_removed",
        resource_type="project",
        resource_id=project_id,
        details=f"Removed user from project"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"User {user_id} removed from project {project_id}")
    return {"message": f"User removed from project"}
