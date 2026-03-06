#!/usr/bin/env python
"""Add missing columns to projects table"""
from app.database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

try:
    # Add status column
    print("Adding 'status' column to projects table...")
    db.execute(text("ALTER TABLE projects ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))
    
    # Add lead_id column  
    print("Adding 'lead_id' column to projects table...")
    db.execute(text("ALTER TABLE projects ADD COLUMN lead_id INTEGER"))
    
    db.commit()
    print("✓ Successfully added columns to projects table")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
