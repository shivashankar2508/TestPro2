from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import Optional, List
from app.database import get_db
from app.models.user import User, RoleEnum, UserStatusEnum, AuditLog
from app.schemas.auth import UserResponse, UserDetailResponse, RoleEnum as SchemaRoleEnum
from app.utils.auth_middleware import require_admin, get_current_user
from app.exceptions import (
    UserNotFoundError, PermissionDeniedError, ValidationError,
    UserAlreadyExistsError, CannotDeleteError
)
from app.utils.security import hash_password
from app.utils.email_service import EmailService
import logging

router = APIRouter(prefix="/api/users", tags=["User Management"])
logger = logging.getLogger(__name__)

# ============ Pydantic Schemas for User Management ============

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional

class UserUpdate(BaseModel):
    """Update user information"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    
    class Config:
        from_attributes = True

class UserRoleUpdate(BaseModel):
    """Update user role"""
    role: SchemaRoleEnum = Field(..., description="New role: tester, developer, or admin")
    
    class Config:
        from_attributes = True

class AdminCreateUser(BaseModel):
    """Admin creating a new user"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: SchemaRoleEnum = Field(default=SchemaRoleEnum.TESTER)
    temporary_password: Optional[str] = None  # Will generate if not provided

class UserListResponse(BaseModel):
    """Response for user list with pagination"""
    total: int
    page: int
    page_size: int
    users: List[UserDetailResponse]

class UserAccountUpdate(BaseModel):
    """User updating their own account"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    current_password: Optional[str] = None  # Required if changing sensitive info
    email: Optional[EmailStr] = None

# ============ Public User Endpoints ============

@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's information"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise UserNotFoundError()
    
    return user

@router.put("/me", response_model=UserDetailResponse)
async def update_current_user(
    user_update: UserAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's information"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise UserNotFoundError()
    
    # Update full name if provided
    if user_update.full_name:
        user.full_name = user_update.full_name
    
    # Update email if provided
    if user_update.email:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != user.id
        ).first()
        
        if existing:
            raise UserAlreadyExistsError()
        
        user.email = user_update.email
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user.id} updated their profile")
    
    # Audit log
    audit_log = AuditLog(
        user_id=user.id,
        action="profile_update",
        resource_type="user",
        resource_id=user.id,
        details=f"Updated profile: full_name={user_update.full_name}, email={user_update.email}"
    )
    db.add(audit_log)
    db.commit()
    
    return user

# ============ Admin User Management ============

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by email or username"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users with pagination and filtering (Admin only)"""
    
    try:
        query = db.query(User)
        
        # Apply filters
        if role:
            # Since role is stored as string in database, compare directly
            role_value = role.lower()
            query = query.filter(User.role == role_value)
        
        if status:
            # Since status is stored as string in database, compare directly
            status_value = status.lower().replace('_', '_')
            query = query.filter(User.status == status_value)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_term)) | (User.username.ilike(search_term))
            )
        
        # Get total count
        total = query.count()
        
        # Pagination
        offset = (page - 1) * page_size
        users = query.order_by(desc(User.created_at)).offset(offset).limit(page_size).all()
        
        logger.info(f"Admin {current_user.id} listed users (page {page}, size {page_size})")
        
        return UserListResponse(
            total=total,
            page=page,
            page_size=page_size,
            users=users
        )
    
    except Exception as e:
        print(f"ERROR listing users: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )

@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user details (Admin or self)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    # Check permissions: allow if admin or viewing self
    if current_user.role != RoleEnum.ADMIN and current_user.id != user.id:
        raise PermissionDeniedError("Cannot view other users' details")
    
    return user

@router.post("", response_model=UserDetailResponse)
async def create_user(
    user_create: AdminCreateUser,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new user (Admin only)"""
    
    # Check if user already exists
    existing_email = db.query(User).filter(User.email == user_create.email).first()
    if existing_email:
        raise UserAlreadyExistsError()
    
    existing_username = db.query(User).filter(User.username == user_create.username).first()
    if existing_username:
        raise ValidationError("Username already exists")
    
    # Generate password if not provided
    if user_create.temporary_password:
        hashed_password = hash_password(user_create.temporary_password)
        temp_password = user_create.temporary_password
    else:
        temp_password = None
        hashed_password = hash_password("TempPass" + str(uuid.uuid4())[:8])
    
    # Create user
    new_user = User(
        email=user_create.email,
        username=user_create.username,
        full_name=user_create.full_name,
        hashed_password=hashed_password,
        role=RoleEnum[user_create.role.upper()].value,
        is_active=True,
        is_verified=True,
        verified_at=datetime.utcnow(),
        status=UserStatusEnum.ACTIVE.value
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Admin {current_user.id} created new user {new_user.id}")
    
    # Send welcome email
    try:
        if temp_password:
            EmailService.send_welcome_email(new_user.email, new_user.full_name, temp_password)
        else:
            EmailService.send_welcome_email_temp_password(new_user.email, new_user.full_name)
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_created",
        resource_type="user",
        resource_id=new_user.id,
        details=f"Created user: {new_user.username} ({new_user.email}) with role {new_user.role}"
    )
    db.add(audit_log)
    db.commit()
    
    return new_user

@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user information (Admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    # Update fields
    if user_update.full_name:
        user.full_name = user_update.full_name
    
    if user_update.email:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        
        if existing:
            raise UserAlreadyExistsError()
        
        user.email = user_update.email
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {current_user.id} updated user {user_id}")
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_updated",
        resource_type="user",
        resource_id=user_id,
        details=f"Updated: {user_update}"
    )
    db.add(audit_log)
    db.commit()
    
    return user

@router.put("/{user_id}/role", response_model=UserDetailResponse)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role (Admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    # Prevent removing last admin
    if user.role == "admin" and role_update.role != SchemaRoleEnum.ADMIN:
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count == 1:
            raise CannotDeleteError("Cannot remove the last admin user")
    
    old_role = user.role
    user.role = RoleEnum[role_update.role.upper()].value
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {current_user.id} changed user {user_id} role from {old_role} to {user.role}")
    
    # Send notification email
    try:
        EmailService.send_role_change_notification(user.email, user.full_name, user.role)
    except Exception as e:
        logger.error(f"Failed to send role change email: {str(e)}")
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="role_changed",
        resource_type="user",
        resource_id=user_id,
        details=f"Role changed from {old_role} to {user.role}"
    )
    db.add(audit_log)
    db.commit()
    
    return user

@router.post("/{user_id}/lock")
async def lock_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lock user account (Admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    if user.status == UserStatusEnum.LOCKED:
        raise ValidationError("User account is already locked")
    
    user.status = UserStatusEnum.LOCKED
    user.locked_until = datetime.utcnow() + timedelta(days=30)  # Lock for 30 days
    db.commit()
    
    logger.info(f"Admin {current_user.id} locked user account {user_id}")
    
    # Send notification email
    try:
        EmailService.send_account_locked_notification(user.email, user.full_name)
    except Exception as e:
        logger.error(f"Failed to send lock notification: {str(e)}")
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="account_locked",
        resource_type="user",
        resource_id=user_id,
        details=f"Admin locked account until {user.locked_until}"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "message": f"User account locked until {user.locked_until.isoformat()}",
        "locked_until": user.locked_until.isoformat()
    }

@router.post("/{user_id}/unlock")
async def unlock_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Unlock user account (Admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    if user.status != UserStatusEnum.LOCKED:
        raise ValidationError("User account is not locked")
    
    user.status = UserStatusEnum.ACTIVE
    user.locked_until = None
    user.failed_login_attempts = 0
    db.commit()
    
    logger.info(f"Admin {current_user.id} unlocked user account {user_id}")
    
    # Send notification email
    try:
        EmailService.send_account_unlocked_notification(user.email, user.full_name)
    except Exception as e:
        logger.error(f"Failed to send unlock notification: {str(e)}")
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="account_unlocked",
        resource_type="user",
        resource_id=user_id,
        details="Admin unlocked account"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "User account unlocked"}

@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate user account (Admin only, soft delete)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    # Prevent deleting last admin
    if user.role == RoleEnum.ADMIN:
        admin_count = db.query(User).filter(User.role == RoleEnum.ADMIN).count()
        if admin_count == 1:
            raise CannotDeleteError("Cannot deactivate the last admin user")
    
    # Soft delete - just deactivate
    user.is_active = False
    user.status = UserStatusEnum.INACTIVE
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Admin {current_user.id} deactivated user {user_id}")
    
    # Send notification email
    try:
        EmailService.send_account_deactivated_notification(user.email, user.full_name)
    except Exception as e:
        logger.error(f"Failed to send deactivation email: {str(e)}")
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="account_deactivated",
        resource_type="user",
        resource_id=user_id,
        details="Admin deactivated user account"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "message": f"User {user.username} has been deactivated",
        "user_id": user_id
    }

# ============ Audit Logs ============

@router.get("/{user_id}/audit-logs", response_model=List[dict])
async def get_user_audit_logs(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit logs for user (Admin or self)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError()
    
    # Check permissions
    if current_user.role != RoleEnum.ADMIN and current_user.id != user_id:
        raise PermissionDeniedError("Cannot view audit logs for other users")
    
    # Get audit logs
    offset = (page - 1) * page_size
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == user_id
    ).order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()
    
    return [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]

# ============ User Statistics (Admin only) ============

@router.get("/stats/overview")
async def get_user_statistics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user statistics (Admin only)"""
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    locked_users = db.query(User).filter(User.status == UserStatusEnum.LOCKED).count()
    
    # Count by role
    testers = db.query(User).filter(User.role == RoleEnum.TESTER).count()
    developers = db.query(User).filter(User.role == RoleEnum.DEVELOPER).count()
    admins = db.query(User).filter(User.role == RoleEnum.ADMIN).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "locked_users": locked_users,
        "by_role": {
            "testers": testers,
            "developers": developers,
            "admins": admins
        }
    }

import uuid
