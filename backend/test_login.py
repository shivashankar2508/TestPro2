#!/usr/bin/env python
"""
Test login functionality
"""
import requests
import json

API_URL = "http://localhost:8000/api"

def test_login(email, password):
    """Test login with credentials"""
    print(f"\n🔐 Testing login for: {email}")
    
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={
                "email": email,
                "password": password
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access Token: {data.get('access_token', 'N/A')[:50]}...")
            return True
        else:
            print(f"❌ Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Login Functionality")
    print("=" * 60)
    
    # Test with admin user
    test_login("admin@testtrack.com", "Admin@123")
    
    # Test with test@test.com (if password is known)
    test_login("test@test.com", "Test@123")
    test_login("test@test.com", "test123")
    test_login("test@test.com", "password")
    
    print("\n" + "=" * 60)
