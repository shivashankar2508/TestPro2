#!/usr/bin/env python
"""Test login by simulating form submission"""
import asyncio
from app.schemas.auth import UserLogin
from app.api.routes.auth import login
from app.database import SessionLocal
from unittest.mock import Mock

async def test_login():
    print("Testing login endpoint...")
    
    try:
        # Mock
        request_mock = Mock()
        request_mock.client = Mock()
        request_mock.client.host = '127.0.0.1'
        request_mock.headers.get = lambda x: 'test'
        
        db = SessionLocal()
        login_data = UserLogin(email='admin@testtrack.com', password='Admin@123')
        
        # Call login
        result = await login(login_data, db, request_mock)
        print(f"[OK] Login successful")
        print(f"     Access Token: {str(result.access_token)[:40]}...")
        
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            db.close()
        except:
            pass

asyncio.run(test_login())
