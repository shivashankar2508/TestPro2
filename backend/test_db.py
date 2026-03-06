#!/usr/bin/env python
"""Test database initialization"""
import sys
import traceback

try:
    print("Starting database test...")
    from app.database import Base, engine
    from app.models.user import User
    print("✓ Imports successful")
    
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully!")
    
    # Try to add a test user
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    from app.utils.security import hash_password
    test_user = User(
        email="test@test.com",
        username="testuser",
        full_name="Test User",
        hashed_password=hash_password("TestPass@123"),
        is_verified=True,
        is_active=True,
        role="tester",
        status="active"
    )
    db.add(test_user)
    db.commit()
    print(f"✓ Test user created with ID: {test_user.id}")
    db.close()
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    traceback.print_exc()
    sys.exit(1)
