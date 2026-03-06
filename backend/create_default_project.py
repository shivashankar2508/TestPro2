#!/usr/bin/env python
"""Create a default project for test cases"""
import sys
from app.database import SessionLocal
from app.models.user import User, Project
from datetime import datetime

try:
    db = SessionLocal()
    
    # Check if default project exists
    default_project = db.query(Project).filter(Project.name == "Default Project").first()
    
    if default_project:
        print(f"✓ Default project already exists (ID: {default_project.id})")
    else:
        # Get first user (should be admin or tester)
        first_user = db.query(User).first()
        
        if not first_user:
            print("✗ No users found. Please create a user first.")
            sys.exit(1)
        
        # Create default project
        project = Project(
            name="Default Project",
            description="Default project for test cases",
            created_by_id=first_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        print(f"✓ Default project created (ID: {project.id})")
    
    db.close()
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
