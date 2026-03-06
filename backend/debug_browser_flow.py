#!/usr/bin/env python
"""
Debug script to test the exact same flow as the browser
"""
import requests
import json
import time

API_BASE = "http://localhost:8001/api"

# Session to maintain cookies, etc
session = requests.Session()

print("="*80)
print("STEP 1: Login")
print("="*80)

try:
    resp = session.post(f"{API_BASE}/auth/login", json={
        "email": "admin@testtrack.com",
        "password": "Admin@123",
        "remember_me": False
    }, timeout=5)
    
    print(f"Status: {resp.status_code}")
    data = resp.json()
    
    if resp.status_code == 200:
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        
        print(f"✓ Login successful!")
        print(f"  Access Token Length: {len(access_token)}")
        print(f"  Token Type: {data.get('token_type')}")
        print(f"  Expires In: {data.get('expires_in')} seconds")
        print(f"  Access Token: {access_token[:50]}...")
    else:
        print(f"✗ Login failed: {data.get('detail')}")
        exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

print("\n" + "="*80)
print("STEP 2: Test /users/me with Bearer token")
print("="*80)

try:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    print(f"Headers being sent:")
    print(f"  Authorization: Bearer {access_token[:50]}...")
    print(f"  Content-Type: application/json")
    
    # Simulate exactly what browser does - use requests library like fetch
    resp = session.get(f"{API_BASE}/users/me", headers=headers, timeout=5)
    
    print(f"\nResponse Status: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    
    if resp.status_code == 200:
        user = resp.json()
        print(f"✓ User retrieved successfully!")
        print(f"  Email: {user.get('email')}")
        print(f"  Role: {user.get('role')}")
        print(f"  Full Name: {user.get('full_name')}")
        print(f"\n✓✓✓ FLOW WORKS PERFECTLY ✓✓✓")
    else:
        print(f"\n✗ /users/me failed!")
        try:
            error_data = resp.json()
            print(f"Error Response: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Response Body: {resp.text}")
        print(f"\nThis is the error the browser would see!")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("STEP 3: Check if issue is timing-related (wait like browser does)")
print("="*80)

print("Waiting 2 seconds to simulate browser redirect delay...")
time.sleep(2)

try:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    resp = session.get(f"{API_BASE}/users/me", headers=headers, timeout=5)
    
    if resp.status_code == 200:
        print(f"✓ Still works after 2 second delay")
    else:
        print(f"✗ Failed after delay: {resp.status_code}")
        error_data = resp.json()
        print(f"Error: {error_data.get('detail')}")
        
except Exception as e:
    print(f"✗ Error after delay: {e}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("If both STEP 2 and STEP 3 succeeded, the backend is working.")
print("The issue must be in how the browser is sending the request.")
print("")
