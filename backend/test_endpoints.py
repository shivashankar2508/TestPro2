#!/usr/bin/env python
"""Test endpoints after Enum fixes"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Test login endpoint"""
    print("\n=== Testing Login ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": "admin@testtrack.com",
            "password": "Admin123!"
        }
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:200]}")
    return data.get("access_token")

def test_create_test_case(token):
    """Test test case creation"""
    print("\n=== Testing Create Test Case ===")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "project_id": 1,
        "title": "Test Case 1",
        "description": "Test description",
        "module": "Module A",
        "priority": "high",
        "severity": "high",
        "type": "functional",
        "status": "draft",
        "steps": [
            {
                "step_number": 1,
                "action": "Click Button",
                "test_data": "",
                "expected_result": "Button clicked"
            }
        ],
        "tags": []
    }
    response = requests.post(
        f"{BASE_URL}/api/test-cases",
        json=payload,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
    return response

def test_list_users(token):
    """Test list users endpoint"""
    print("\n=== Testing List Users ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/users",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
    return response

def test_list_users_filter(token):
    """Test list users with role filter"""
    print("\n=== Testing List Users with Filter ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/users?role=admin",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
    return response

def test_list_test_cases(token):
    """Test list test cases endpoint"""
    print("\n=== Testing List Test Cases ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/test-cases",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
    return response

if __name__ == "__main__":
    try:
        token = test_login()
        if token:
            test_create_test_case(token)
            test_list_users(token)
            test_list_users_filter(token)
            test_list_test_cases(token)
        else:
            print("Failed to get token!")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
