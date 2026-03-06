#!/usr/bin/env python
"""Debug login endpoint issues"""
import sys
import traceback

# Add current directory to path
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.user import User
from app.utils.security import verify_password

db = SessionLocal()

try:
    # Check if admin user exists
    user = db.query(User).filter(User.email == 'admin@testtrack.com').first()
    print(f"✓ User found: {user is not None}")
    
    if user:
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")
        print(f"  Hashed password exists: {user.hashed_password is not None}")
        
        # Test password verification
        password_match = verify_password('Admin@123', user.hashed_password)
        print(f"  Password matches: {password_match}")
        
        if not password_match:
            print("  ERROR: Password doesn't match despite correct creds")
    else:
        print("  ERROR: Admin user not found in database")
        
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
finally:
    db.close()
