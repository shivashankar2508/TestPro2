#!/usr/bin/env python
"""Test creating a test case via API"""
import requests
import json

# Login first
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "admin@testtrack.com", "password": "Admin@123"}
)
print(f"Login: {login_response.status_code}")
token = login_response.json()["access_token"]

# Create test case
headers = {"Authorization": f"Bearer {token}"}
test_case_data = {
    "title": "Test Case 1",
    "description": "Test description",
    "priority": "medium",
    "severity": "minor",
    "status": "draft",
    "type": "functional",
    "automation_status": "not_automated",
    "module": "Login Module",
    "pre_conditions": "User logged out",
    "project_id": 1,
    "assigned_tester_id": None,
    "steps": [],
    "tags": []
}

print("\n=== Sending request ===")
print(json.dumps(test_case_data, indent=2))

response = requests.post(
    "http://localhost:8000/api/test-cases",
    headers=headers,
    json=test_case_data
)

print(f"\n=== Response ===")
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")

if response.status_code != 201:
    print("\n=== ERROR ===")
    try:
        error_data = response.json()
        print(json.dumps(error_data, indent=2))
    except:
        print(response.text)
