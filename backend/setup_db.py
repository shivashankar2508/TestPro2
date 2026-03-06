#!/usr/bin/env python
"""
Setup script to initialize database and create default users
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.user import User, RoleEnum, UserStatusEnum
from app.utils.security import hash_password
from datetime import datetime

def setup_database():
    """Initialize database and create default users"""
    print("🔧 Setting up database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if users exist
        user_count = db.query(User).count()
        print(f"📊 Current users in database: {user_count}")
        
        if user_count == 0:
            print("\n📝 Creating default users...")
            
            # Create admin user
            admin = User(
                email="admin@testtrack.com",
                hashed_password=hash_password("Admin@123"),
                full_name="Admin User",
                role=RoleEnum.ADMIN,
                status=UserStatusEnum.ACTIVE,
                is_active=True,
                is_verified=True,
                email_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin)
            
            # Create tester user
            tester = User(
                email="tester@testtrack.com",
                hashed_password=hash_password("Tester@123"),
                full_name="Test User",
                role=RoleEnum.TESTER,
                status=UserStatusEnum.ACTIVE,
                is_active=True,
                is_verified=True,
                email_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tester)
            
            # Create developer user
            developer = User(
                email="dev@testtrack.com",
                hashed_password=hash_password("Dev@123"),
                full_name="Developer User",
                role=RoleEnum.DEVELOPER,
                status=UserStatusEnum.ACTIVE,
                is_active=True,
                is_verified=True,
                email_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(developer)
            
            db.commit()
            print("✓ Default users created successfully!")
            print("\n📋 Login Credentials:")
            print("   Admin:     admin@testtrack.com / Admin@123")
            print("   Tester:    tester@testtrack.com / Tester@123")
            print("   Developer: dev@testtrack.com / Dev@123")
        else:
            print("\n👥 Existing users:")
            users = db.query(User).all()
            for user in users:
                role = user.role.value if hasattr(user.role, 'value') else user.role
                print(f"   - {user.email} ({role}) - Active: {user.is_active}")
        
        print("\n✅ Database setup complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()
