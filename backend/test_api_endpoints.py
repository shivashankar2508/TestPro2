import sys
import requests
import json

# Test login
resp = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'testuser@testtrack.com',
    'password': 'TestPass123!'
})

print(f"Login response status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    token = data.get('access_token')
    print(f"✓ Login successful! Token: {token[:50]}...")
    
    # Test create test case
    print("\n=== Testing Create Test Case ===")
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        'project_id': 1,
        'title': 'Test Case 1',
        'description': 'Test description',
        'module': 'Module A',
        'priority': 'high',
        'severity': 'high',
        'type': 'functional',
        'status': 'draft',
        'steps': [{'step_number': 1, 'action': 'Click', 'test_data': '', 'expected_result': 'Clicked'}],
        'tags': []
    }
    
    tc_resp = requests.post('http://localhost:8000/api/test-cases', json=payload, headers=headers)
    print(f"Create test case status: {tc_resp.status_code}")
    if tc_resp.status_code not in [200, 201]:
        print(f"✗ Error: {json.dumps(tc_resp.json(), indent=2)}")
    else:
        print(f"✓ Test case created successfully")
        print(f"Response: {json.dumps(tc_resp.json(), indent=2)[:300]}")
    
    # Test list test cases
    print("\n=== Testing List Test Cases ===")
    list_resp = requests.get('http://localhost:8000/api/test-cases', headers=headers)
    print(f"List test cases status: {list_resp.status_code}")
    if list_resp.status_code != 200:
        print(f"✗ Error: {json.dumps(list_resp.json(), indent=2)}")
    else:
        data = list_resp.json()
        print(f"✓ Test cases listed successfully")
        print(f"Total: {data.get('total')}, Page: {data.get('page')}")
    
else:
    print(f"✗ Login failed: {resp.json()}")
