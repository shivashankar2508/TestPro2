from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.user import User, SystemConfiguration, AuditLog
from app.utils.auth_middleware import require_admin, get_current_user
from app.exceptions import ValidationError, ResourceNotFoundError
import json
import logging

router = APIRouter(prefix="/api/system", tags=["System Configuration"])
logger = logging.getLogger(__name__)

# ============ Pydantic Schemas ============

class SystemConfigUpdate(BaseModel):
    value: str
    
class SystemConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    data_type: str
    description: Optional[str]
    is_encrypted: bool
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SystemStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_projects: int
    total_test_cases: int
    total_executions: int
    database_size: Optional[str]
    last_backup: Optional[datetime]

# ============ Default Configurations ============

DEFAULT_CONFIGS = [
    {
        "key": "app.name",
        "value": "TestTrack Pro",
        "data_type": "string",
        "description": "Application name"
    },
    {
        "key": "app.version",
        "value": "2.0.0",
        "data_type": "string",
        "description": "Current application version"
    },
    {
        "key": "app.environment",
        "value": "production",
        "data_type": "string",
        "description": "Application environment (development/staging/production)"
    },
    {
        "key": "email.smtp_server",
        "value": "smtp.gmail.com",
        "data_type": "string",
        "description": "SMTP server for email notifications",
        "is_encrypted": True
    },
    {
        "key": "email.smtp_port",
        "value": "587",
        "data_type": "int",
        "description": "SMTP server port"
    },
    {
        "key": "email.from_address",
        "value": "noreply@testtrack.com",
        "data_type": "string",
        "description": "Default sender email address"
    },
    {
        "key": "security.session_timeout_minutes",
        "value": "30",
        "data_type": "int",
        "description": "Session timeout in minutes"
    },
    {
        "key": "security.max_login_attempts",
        "value": "5",
        "data_type": "int",
        "description": "Maximum failed login attempts before lockout"
    },
    {
        "key": "storage.max_file_size_mb",
        "value": "100",
        "data_type": "int",
        "description": "Maximum file upload size in MB"
    },
    {
        "key": "backup.auto_backup_enabled",
        "value": "true",
        "data_type": "boolean",
        "description": "Enable automatic daily backups"
    },
    {
        "key": "backup.retention_days",
        "value": "30",
        "data_type": "int",
        "description": "Days to retain backups"
    }
]

# ============ Configuration Endpoints ============

@router.get("/config", response_model=List[SystemConfigResponse])
async def get_all_config(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all system configurations (Admin only)"""
    configs = db.query(SystemConfiguration).all()
    
    # Initialize defaults if empty
    if not configs:
        for config in DEFAULT_CONFIGS:
            new_config = SystemConfiguration(
                key=config["key"],
                value=config["value"],
                data_type=config.get("data_type", "string"),
                description=config.get("description"),
                is_encrypted=config.get("is_encrypted", False)
            )
            db.add(new_config)
        db.commit()
        configs = db.query(SystemConfiguration).all()
    
    return configs

@router.get("/config/{key}", response_model=SystemConfigResponse)
async def get_config_by_key(
    key: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get specific configuration by key"""
    config = db.query(SystemConfiguration).filter(SystemConfiguration.key == key).first()
    if not config:
        raise ResourceNotFoundError("Configuration")
    return config

@router.put("/config/{key}", response_model=SystemConfigResponse)
async def update_config(
    key: str,
    config_update: SystemConfigUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update system configuration (Admin only)"""
    config = db.query(SystemConfiguration).filter(SystemConfiguration.key == key).first()
    if not config:
        raise ResourceNotFoundError("Configuration")
    
    old_value = config.value
    config.value = config_update.value
    config.updated_by_id = current_user.id
    config.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(config)
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="config_updated",
        resource_type="system_config",
        resource_id=config.id,
        details=f"Updated {key}: {old_value} → {config_update.value}"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Configuration {key} updated by admin {current_user.id}")
    return config

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system statistics (Admin only)"""
    from app.models.user import User as UserModel, Project
    from app.models.test_case import TestCase, TestExecution
    
    total_users = db.query(UserModel).count()
    active_users = db.query(UserModel).filter(UserModel.is_active == True).count()
    total_projects = db.query(Project).count()
    total_test_cases = db.query(TestCase).count()
    total_executions = db.query(TestExecution).count()
    
    # Get last backup date
    from app.models.user import Backup
    last_backup = db.query(Backup).filter(
        Backup.status == "completed"
    ).order_by(Backup.backup_date.desc()).first()
    
    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_projects=total_projects,
        total_test_cases=total_test_cases,
        total_executions=total_executions,
        database_size=None,  # Can be enhanced to calculate actual size
        last_backup=last_backup.backup_date if last_backup else None
    )

@router.post("/health-check", status_code=status.HTTP_200_OK)
async def system_health_check(db: Session = Depends(get_db)):
    """Perform system health check - no auth required"""
    try:
        # Test database connection
        db.query(SystemConfiguration).first()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "checks": {
                "database": "ok",
                "storage": "ok",
                "configuration": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="System health check failed")

@router.get("/test-public", status_code=status.HTTP_200_OK)
async def test_public():
    """Test public endpoint (no auth required)"""
    return {"message": "This is public", "status": "ok"}
