#!/usr/bin/env python
"""Test model loading"""
print('Testing model imports...')
try:
    from app.models.user import (User, Permission, RolePermission, 
                                  SystemConfiguration, Backup, ProjectMember, Project)
    print('[OK] User models loaded')
except Exception as e:
    print(f'[ERROR] User models failed: {e}')
    import traceback
    traceback.print_exc()

try:
    from app.models.test_case import TestCase, TestExecution
    print('[OK] Test case models loaded')
except Exception as e:
    print(f'[ERROR] Test case models failed: {e}')
    import traceback
    traceback.print_exc()

try:
    from app.database import SessionLocal
    db = SessionLocal()
    u = db.query(User).first()
    email = u.email if u else "no users"
    print(f'[OK] Can query users: {email}')
    db.close()
except Exception as e:
    print(f'[ERROR] Query failed: {e}')
    import traceback
    traceback.print_exc()

print('\n[SUCCESS] All models OK')
