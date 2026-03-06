#!/usr/bin/env python
"""Fix database schema and initialize admin features"""
from app.database import SessionLocal
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError

db = SessionLocal()

try:
    # Check current schema
    inspector = inspect(db.get_bind())
    
    # Fix projects table
    proj_cols = {col['name'] for col in inspector.get_columns('projects')}
    if 'status' not in proj_cols:
        print("Adding 'status' column to projects...")
        db.execute(text("ALTER TABLE projects ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))
    if 'lead_id' not in proj_cols:
        print("Adding 'lead_id' column to projects...")
        db.execute(text("ALTER TABLE projects ADD COLUMN lead_id INTEGER"))
    
    # Check and initialize permissions
    perms_count = db.execute(text("SELECT COUNT(*) FROM permissions")).scalar()
    if perms_count == 0:
        print("Initializing default permissions...")
        default_perms = [
            ('users.create', 'Create users', 'users'),
            ('users.read', 'Read user information', 'users'),
            ('users.update', 'Update user details', 'users'),
            ('users.delete', 'Delete users', 'users'),
            ('users.manage_roles', 'Manage user roles', 'users'),
            ('users.view_audit_logs', 'View audit logs', 'users'),
            ('projects.create', 'Create projects', 'projects'),
            ('projects.read', 'Read projects', 'projects'),
            ('projects.update', 'Update projects', 'projects'),
            ('projects.delete', 'Delete projects', 'projects'),
            ('projects.manage_members', 'Manage project members', 'projects'),
            ('test_cases.create', 'Create test cases', 'test_cases'),
            ('test_cases.read', 'Read test cases', 'test_cases'),
            ('test_cases.update', 'Update test cases', 'test_cases'),
            ('test_cases.delete', 'Delete test cases', 'test_cases'),
            ('test_cases.execute', 'Execute test cases', 'test_cases'),
            ('test_cases.create_templates', 'Create test templates', 'test_cases'),
            ('system.config', 'Configure system settings', 'system'),
            ('system.health_check', 'Run health checks', 'system'),
            ('system.view_logs', 'View system logs', 'system'),
            ('backups.create', 'Create backups', 'backups'),
            ('backups.restore', 'Restore backups', 'backups'),
            ('backups.delete', 'Delete backups', 'backups'),
            ('backups.view', 'View backups', 'backups'),
            ('reports.create', 'Create reports', 'reports'),
            ('reports.view', 'View reports', 'reports'),
        ]
        
        for name, desc, cat in default_perms:
            db.execute(text(
                "INSERT INTO permissions (name, description, category, created_at) VALUES (:name, :desc, :cat, datetime('now'))"
            ), {'name': name, 'desc': desc, 'cat': cat})
        
        print(f"  Created {len(default_perms)} permissions")
    
    # Check and initialize system configuration
    config_count = db.execute(text("SELECT COUNT(*) FROM system_configurations")).scalar()
    if config_count == 0:
        print("Initializing system configurations...")
        configs = [
            ('app.name', 'TestTrack Pro', 'string'),
            ('app.version', '1.0.0', 'string'),
            ('app.environment', 'development', 'string'),
            ('email.smtp_server', 'smtp.gmail.com', 'string'),
            ('email.smtp_port', '587', 'string'),
            ('email.from_address', 'noreply@testtrackpro.dev', 'string'),
            ('security.session_timeout_minutes', '15', 'integer'),
            ('security.max_login_attempts', '5', 'integer'),
            ('storage.max_file_size_mb', '100', 'integer'),
            ('backup.auto_backup_enabled', 'false', 'boolean'),
            ('backup.retention_days', '30', 'integer'),
        ]
        
        for key, val, dtype in configs:
            db.execute(text(
                "INSERT INTO system_configurations (key, value, data_type, is_encrypted, updated_at) VALUES (:key, :val, :dtype, 0, datetime('now'))"
            ), {'key': key, 'val': val, 'dtype': dtype})
        
        print(f"  Created {len(configs)} system configurations")
    
    db.commit()
    print("Commit successful!")
    print("\n[SUCCESS] Database schema and admin features initialized")
    
except Exception as e:
    print(f"[ERROR] {e}")
    db.rollback()
finally:
    db.close()
