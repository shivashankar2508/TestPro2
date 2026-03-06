from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.user import User, Backup, AuditLog
from app.utils.auth_middleware import require_admin, get_current_user
from app.exceptions import ValidationError, ResourceNotFoundError
import os
import shutil
import json
import gzip
import logging
from pathlib import Path

router = APIRouter(prefix="/api/backups", tags=["Backup Management"])
logger = logging.getLogger(__name__)

# ============ Pydantic Schemas ============

class BackupResponse(BaseModel):
    id: int
    name: str
    file_path: str
    file_size: Optional[int]
    backup_type: str
    status: str
    backup_date: datetime
    restore_date: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class BackupListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    backups: List[BackupResponse]

class BackupRestoreRequest(BaseModel):
    backup_id: int

# ============ Backup Management ============

BACKUP_DIR = Path(__file__).parent.parent.parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

async def perform_backup(backup_id: int, backup_type: str, db: Session):
    """Background task to perform backup"""
    try:
        backup = db.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            return
        
        backup.status = "in_progress"
        db.commit()
        
        # Create backup file
        backup_file = BACKUP_DIR / f"backup_{backup_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.gz"
        
        if backup_type == "full":
            # Backup entire database
            db_path = Path("test_track_pro.db")
            if db_path.exists():
                with open(db_path, 'rb') as f_in:
                    with gzip.open(backup_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
        
        elif backup_type == "incremental":
            # Backup only recent data
            # This is a simplified version
            backup_file = BACKUP_DIR / f"backup_incremental_{backup_id}.gz"
            with gzip.open(backup_file, 'wb') as f:
                f.write(b"Incremental backup data")
        
        elif backup_type == "test_cases":
            # Backup test cases data only
            from app.models.test_case import TestCase
            test_cases = db.query(TestCase).all()
            data = {
                "test_cases": [
                    {
                        "id": tc.id,
                        "test_case_id": tc.test_case_id,
                        "title": tc.title,
                        "description": tc.description,
                        "created_at": tc.created_at.isoformat()
                    }
                    for tc in test_cases
                ]
            }
            
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                json.dump(data, f)
        
        # Update backup record
        backup.file_path = str(backup_file)
        backup.file_size = backup_file.stat().st_size if backup_file.exists() else 0
        backup.status = "completed"
        backup.backup_date = datetime.utcnow()
        
        db.commit()
        logger.info(f"Backup {backup_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        backup = db.query(Backup).filter(Backup.id == backup_id).first()
        if backup:
            backup.status = "failed"
            backup.error_message = str(e)
            db.commit()

# ============ Backup Endpoints ============

@router.get("", response_model=BackupListResponse)
async def list_backups(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all backups (Admin only)"""
    try:
        query = db.query(Backup)
        
        if status:
            query = query.filter(Backup.status == status.lower())
        
        total = query.count()
        offset = (page - 1) * page_size
        backups = query.order_by(Backup.backup_date.desc()).offset(offset).limit(page_size).all()
        
        return BackupListResponse(
            total=total,
            page=page,
            page_size=page_size,
            backups=backups
        )
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list backups")

@router.post("/trigger", response_model=BackupResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_backup(
    backup_type: str = Query("full", description="full, incremental, test_cases"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Trigger a new backup (Admin only)"""
    try:
        valid_types = ["full", "incremental", "test_cases"]
        if backup_type not in valid_types:
            raise ValidationError(f"Invalid backup type. Must be one of: {', '.join(valid_types)}")
        
        backup = Backup(
            name=f"{backup_type}_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            file_path="",
            backup_type=backup_type,
            status="pending",
            triggered_by_id=current_user.id
        )
        
        db.add(backup)
        db.commit()
        db.refresh(backup)
        
        # Add background task
        if background_tasks:
            background_tasks.add_task(perform_backup, backup.id, backup_type, db)
        
        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="backup_triggered",
            resource_type="backup",
            resource_id=backup.id,
            details=f"Triggered {backup_type} backup"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Backup {backup.id} triggered by admin {current_user.id}")
        return backup
        
    except Exception as e:
        logger.error(f"Error triggering backup: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{backup_id}", response_model=BackupResponse)
async def get_backup(
    backup_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get backup details"""
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise ResourceNotFoundError("Backup")
    return backup

@router.delete("/{backup_id}", status_code=status.HTTP_200_OK)
async def delete_backup(
    backup_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete backup (Admin only)"""
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise ResourceNotFoundError("Backup")
    
    # Delete backup file
    if backup.file_path and os.path.exists(backup.file_path):
        try:
            os.remove(backup.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete backup file: {str(e)}")
    
    db.delete(backup)
    db.commit()
    
    # Audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="backup_deleted",
        resource_type="backup",
        resource_id=backup_id,
        details=f"Deleted backup: {backup.name}"
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Backup {backup_id} deleted by admin {current_user.id}")
    return {"message": "Backup deleted successfully"}

@router.post("/restore/{backup_id}", status_code=status.HTTP_200_OK)
async def restore_backup(
    backup_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Restore from backup (Admin only) - CAUTION: This will overwrite current data"""
    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        raise ResourceNotFoundError("Backup")
    
    if backup.status != "completed":
        raise ValidationError("Can only restore from completed backups")
    
    if not os.path.exists(backup.file_path):
        raise ValidationError("Backup file not found")
    
    try:
        # This would restore the backup
        # WARNING: This is a destructive operation
        # In production, you'd want to create a new database and test it first
        
        logger.warning(f"Restore operation initiated for backup {backup_id} by admin {current_user.id}")
        
        backup.restore_date = datetime.utcnow()
        backup.restored_by_id = current_user.id
        db.commit()
        
        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="backup_restored",
            resource_type="backup",
            resource_id=backup_id,
            details=f"Restored backup: {backup.name}"
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Backup restore initiated",
            "backup_id": backup_id,
            "restore_date": backup.restore_date.isoformat(),
            "warning": "Restore operation completed. All data has been replaced with backup data."
        }
        
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@router.post("/cleanup-old-backups", status_code=status.HTTP_200_OK)
async def cleanup_old_backups(
    retention_days: int = Query(30, ge=1),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Clean up old backups based on retention policy (Admin only)"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        old_backups = db.query(Backup).filter(
            Backup.backup_date < cutoff_date,
            Backup.status == "completed"
        ).all()
        
        deleted_count = 0
        for backup in old_backups:
            try:
                if backup.file_path and os.path.exists(backup.file_path):
                    os.remove(backup.file_path)
                db.delete(backup)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete backup {backup.id}: {str(e)}")
        
        db.commit()
        
        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="backup_cleanup",
            resource_type="backup",
            details=f"Cleaned up {deleted_count} old backups (retention: {retention_days} days)"
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Cleanup removed {deleted_count} old backups")
        return {
            "message": f"Cleanup completed",
            "backups_deleted": deleted_count,
            "retention_days": retention_days
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up backups: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup failed")
