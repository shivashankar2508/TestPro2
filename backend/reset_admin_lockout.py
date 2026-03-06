#!/usr/bin/env python
"""Reset admin account login attempts"""

import sys
sys.path.insert(0, 'c:\\Users\\HP\\Desktop\\Me\\testtrack-pro\\backend')

from app.database import SessionLocal
from app.models.user import User

session = SessionLocal()

try:
    # Find admin user
    admin = session.query(User).filter(User.email == 'admin@testtrack.com').first()
    
    if admin:
        print(f"Found admin user: {admin.email}")
        print(f"  Current status: {admin.status}")
        print(f"  Failed attempts: {admin.failed_login_attempts}")
        print(f"  Locked until: {admin.locked_until}")
        
        # Reset lockout
        admin.failed_login_attempts = 0
        admin.locked_until = None
        if admin.status == 'locked':
            admin.status = 'active'
        
        session.commit()
        
        print("\n✓ Admin account unlocked!")
        print(f"  New status: {admin.status}")
        print(f"  Failed attempts: {admin.failed_login_attempts}")
    else:
        print("Admin user not found!")
finally:
    session.close()
