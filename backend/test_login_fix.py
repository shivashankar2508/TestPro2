#!/usr/bin/env python3
"""Test login endpoint after fixing Request parameter issue"""

import requests
import json
import sys
import time

time.sleep(1)  # Give backend time to fully start

try:
    print("Testing login endpoint...")
    response = requests.post(
        'http://localhost:8000/api/auth/login',
        json={
            'email': 'admin@testtrack.com',
            'password': 'Admin@123'
        },
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body:\n{response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✓ SUCCESS - Login worked!")
        print(f"  Token Type: {data.get('token_type')}")
        print(f"  Token Length: {len(data.get('access_token', ''))}")
    else:
        print(f"\n✗ FAILED - Status {response.status_code}")
        
except requests.exceptions.ConnectionError as e:
    print(f"✗ Connection Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
