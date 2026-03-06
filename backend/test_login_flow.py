#!/usr/bin/env python
"""
Test the complete login flow:
1. Login with test credentials
2. Store the returned token
3. Use token to call /users/me endpoint
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8001/api"

def log(msg, data=None):
    """Log with timestamp"""
    ts = datetime.now().isoformat(timespec='milliseconds')
    print(f"[{ts}] {msg}")
    if data:
        print(f"  {json.dumps(data, indent=2)}")

def test_login_flow():
    """Test complete login flow"""
    
    # Step 1: Login
    log("STEP 1: Attempting login...")
    login_response = requests.post(f"{API_BASE}/auth/login", json={
        "email": "admin@testtrack.com",
        "password": "Admin@123",
        "remember_me": False
    })
    
    log(f"Login Response: status={login_response.status_code}")
    
    if login_response.status_code != 200:
        log("ERROR: Login failed!")
        log("Response:", login_response.json())
        return
    
    login_data = login_response.json()
    access_token = login_data.get('access_token')
    refresh_token = login_data.get('refresh_token')
    
    log("Login successful!", {
        "access_token_length": len(access_token) if access_token else 0,
        "refresh_token_length": len(refresh_token) if refresh_token else 0,
        "has_access_token": bool(access_token),
        "token_type": login_data.get('token_type'),
        "expires_in": login_data.get('expires_in')
    })
    
    if not access_token:
        log("ERROR: No access_token in response!")
        return
    
    # Step 2: Use token to call /users/me
    log("\nSTEP 2: Calling /users/me with token...")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    log("Request headers:", {
        "Authorization_header": headers.get('Authorization', 'MISSING')[:50] + "..." if headers.get('Authorization') else 'MISSING'
    })
    
    users_me_response = requests.get(
        f"{API_BASE}/users/me",
        headers=headers
    )
    
    log(f"/users/me Response: status={users_me_response.status_code}")
    
    if users_me_response.status_code == 200:
        user_data = users_me_response.json()
        log("SUCCESS! User data retrieved:", {
            "email": user_data.get('email'),
            "full_name": user_data.get('full_name'),
            "role": user_data.get('role')
        })
    else:
        log("ERROR: /users/me failed!")
        log("Response:", users_me_response.json())
        log("\nDiagnostics:")
        log("Status code:", users_me_response.status_code)
        log("Headers sent:", headers)
        
        # Try without token to see if endpoint exists
        log("\nSTEP 3: Calling /users/me WITHOUT token (control test)...")
        control_response = requests.get(f"{API_BASE}/users/me")
        log(f"Control test status: {control_response.status_code}")
        
        # Check if /users exists
        log("\nSTEP 4: Testing /users endpoint...")
        users_response = requests.get(
            f"{API_BASE}/users",
            headers=headers
        )
        log(f"/users Response: status={users_response.status_code}")

if __name__ == '__main__':
    print("=" * 80)
    print("Testing Complete Login Flow")
    print("=" * 80)
    test_login_flow()
    print("=" * 80)
