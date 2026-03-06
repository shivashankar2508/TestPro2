from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.user import User, Permission, RolePermission, AuditLog
from app.utils.auth_middleware import require_admin, get_current_user
from app.exceptions import ValidationError, ResourceNotFoundError
import logging

router = APIRouter(prefix="/api/permissions", tags=["Permission Management"])
logger = logging.getLogger(__name__)

# ============ Pydantic Schemas ============

class PermissionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    category: str = Field(..., description="users, projects, system, backups, test_cases, reports")

class RolePermissionResponse(BaseModel):
    id: int
    role: str
    permission: PermissionResponse
    granted_at: datetime
    
    class Config:
        from_attributes = True

class AssignPermissionRequest(BaseModel):
    role: str = Field(..., description="admin, developer, tester, custom")
    permission_id: int

class RolePermissionsResponse(BaseModel):
    role: str
    total_permissions: int
    permissions: List[PermissionResponse]

# ============ Default Permissions ============

DEFAULT_PERMISSIONS = {
    "users": [
        {"name": "users.create", "description": "Create new user"},
        {"name": "users.read", "description": "View user details"},
        {"name": "users.update", "description": "Update user information"},
        {"name": "users.delete", "description": "Delete/deactivate user"},
        {"name": "users.manage_roles", "description": "Manage user roles"},
        {"name": "users.view_audit_logs", "description": "View user audit logs"},
    ],
    "projects": [
        {"name": "projects.create", "description": "Create new project"},
        {"name": "projects.read", "description": "View project details"},
        {"name": "projects.update", "description": "Update project"},
        {"name": "projects.delete", "description": "Delete project"},
        {"name": "projects.manage_members", "description": "Manage project members"},
    ],
    "test_cases": [
        {"name": "test_cases.create", "description": "Create test cases"},
        {"name": "test_cases.read", "description": "View test cases"},
        {"name": "test_cases.update", "description": "Update test cases"},
        {"name": "test_cases.delete", "description": "Delete test cases"},
        {"name": "test_cases.execute", "description": "Execute test cases"},
        {"name": "test_cases.create_templates", "description": "Create test case templates"},
    ],
    "system": [
        {"name": "system.config", "description": "Manage system configuration"},
        {"name": "system.health_check", "description": "Perform system health checks"},
        {"name": "system.view_logs", "description": "View system logs"},
    ],
    "backups": [
        {"name": "backups.create", "description": "Create backups"},
        {"name": "backups.restore", "description": "Restore from backups"},
        {"name": "backups.delete", "description": "Delete backups"},
        {"name": "backups.view", "description": "View backup history"},
    ],
    "reports": [
        {"name": "reports.create", "description": "Generate reports"},
        {"name": "reports.view", "description": "View reports"},
        {"name": "reports.export", "description": "Export reports"},
    ]
}

# ============ Role Permission Mappings ============

ROLE_DEFAULT_PERMISSIONS = {
    "admin": [
        "users.create", "users.read", "users.update", "users.delete", "users.manage_roles", "users.view_audit_logs",
        "projects.create", "projects.read", "projects.update", "projects.delete", "projects.manage_members",
        "test_cases.create", "test_cases.read", "test_cases.update", "test_cases.delete", "test_cases.execute", "test_cases.create_templates",
        "system.config", "system.health_check", "system.view_logs",
        "backups.create", "backups.restore", "backups.delete", "backups.view",
        "reports.create", "reports.view", "reports.export"
    ],
    "developer": [
        "projects.read", "projects.update",
        "test_cases.create", "test_cases.read", "test_cases.update", "test_cases.delete", "test_cases.execute", "test_cases.create_templates",
        "reports.view", "reports.export"
    ],
    "tester": [
        "test_cases.read", "test_cases.execute",
        "reports.view"
    ]
}

# ============ Permission Endpoints ============

@router.get("", response_model=List[PermissionResponse])
async def list_permissions(
    category: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all permissions (Admin only)"""
    query = db.query(Permission)
    
    if category:
        query = query.filter(Permission.category == category.lower())
    
    permissions = query.order_by(Permission.category, Permission.name).all()
    
    # Initialize default permissions if empty
    if not permissions:
        for category_name, perms in DEFAULT_PERMISSIONS.items():
            for perm in perms:
                new_perm = Permission(
                    name=perm["name"],
                    description=perm["description"],
                    category=category_name
                )
                db.add(new_perm)
        db.commit()
        permissions = db.query(Permission).all()
    
    return permissions

@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    perm_create: PermissionCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new permission (Admin only)"""
    # Check if permission already exists
    existing = db.query(Permission).filter(Permission.name == perm_create.name).first()
    if existing:
        raise ValidationError("Permission already exists")
    
    permission = Permission(
        name=perm_create.name,
        description=perm_create.description,
        category=perm_create.category.lower()
    )
    
    db.add(permission)
    db.commit()
    db.refresh(permission)
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="permission_created",
        resource_type="permission",
        resource_id=permission.id,
        details=f"Created permission: {perm_create.name}"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Permission {permission.id} created")
    return permission

@router.get("/role/{role}", response_model=RolePermissionsResponse)
async def get_role_permissions(
    role: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all permissions for a role"""
    role_perms = db.query(RolePermission).filter(RolePermission.role == role.lower()).all()
    
    permissions = [rp.permission for rp in role_perms]
    
    return RolePermissionsResponse(
        role=role.lower(),
        total_permissions=len(permissions),
        permissions=permissions
    )

@router.post("/assign", status_code=status.HTTP_201_CREATED)
async def assign_permission_to_role(
    assign_request: AssignPermissionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Assign permission to role (Admin only)"""
    # Check if permission exists
    permission = db.query(Permission).filter(Permission.id == assign_request.permission_id).first()
    if not permission:
        raise ResourceNotFoundError("Permission")
    
    # Check if already assigned
    existing = db.query(RolePermission).filter(
        RolePermission.role == assign_request.role.lower(),
        RolePermission.permission_id == assign_request.permission_id
    ).first()
    
    if existing:
        raise ValidationError("Permission already assigned to this role")
    
    role_permission = RolePermission(
        role=assign_request.role.lower(),
        permission_id=assign_request.permission_id,
        granted_by_id=current_user.id
    )
    
    db.add(role_permission)
    db.commit()
    db.refresh(role_permission)
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="permission_assigned",
        resource_type="role_permission",
        resource_id=role_permission.id,
        details=f"Assigned {permission.name} to {assign_request.role} role"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Permission {permission.name} assigned to role {assign_request.role}")
    return {
        "message": f"Permission assigned successfully",
        "role": assign_request.role,
        "permission": permission.name
    }

@router.delete("/revoke/{role}/{permission_id}", status_code=status.HTTP_200_OK)
async def revoke_permission_from_role(
    role: str,
    permission_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Revoke permission from role (Admin only)"""
    role_permission = db.query(RolePermission).filter(
        RolePermission.role == role.lower(),
        RolePermission.permission_id == permission_id
    ).first()
    
    if not role_permission:
        raise ResourceNotFoundError("Role permission assignment")
    
    permission = role_permission.permission
    db.delete(role_permission)
    db.commit()
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="permission_revoked",
        resource_type="role_permission",
        details=f"Revoked {permission.name} from {role} role"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Permission {permission.name} revoked from role {role}")
    return {
        "message": "Permission revoked successfully",
        "role": role,
        "permission": permission.name
    }

@router.post("/initialize-defaults", status_code=status.HTTP_200_OK)
async def initialize_default_permissions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Initialize default permissions and role assignments (Admin only)"""
    try:
        # Create default permissions
        for category_name, perms in DEFAULT_PERMISSIONS.items():
            for perm in perms:
                existing = db.query(Permission).filter(Permission.name == perm["name"]).first()
                if not existing:
                    new_perm = Permission(
                        name=perm["name"],
                        description=perm["description"],
                        category=category_name
                    )
                    db.add(new_perm)
        
        db.commit()
        
        # Assign default permissions to roles
        for role, perm_names in ROLE_DEFAULT_PERMISSIONS.items():
            for perm_name in perm_names:
                permission = db.query(Permission).filter(Permission.name == perm_name).first()
                if permission:
                    existing = db.query(RolePermission).filter(
                        RolePermission.role == role,
                        RolePermission.permission_id == permission.id
                    ).first()
                    if not existing:
                        role_perm = RolePermission(
                            role=role,
                            permission_id=permission.id,
                            granted_by_id=current_user.id
                        )
                        db.add(role_perm)
        
        db.commit()
        
        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="permissions_initialized",
            resource_type="system",
            details="Initialized default permissions and role assignments"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info("Default permissions initialized")
        return {
            "message": "Default permissions initialized successfully",
            "total_permissions": len(DEFAULT_PERMISSIONS),
            "roles_configured": list(ROLE_DEFAULT_PERMISSIONS.keys())
        }
        
    except Exception as e:
        logger.error(f"Error initializing permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="Initialization failed")
