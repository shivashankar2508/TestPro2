import sys
sys.path.insert(0, 'c:\\Users\\HP\\Desktop\\Me\\testtrack-pro\\backend')

# Create or get a test user for testing
from app.database import SessionLocal
from app.models.user import User
from app.utils.security import hash_password

session = SessionLocal()

# Check if test user exists
user = session.query(User).filter(User.email == 'testuser@testtrack.com').first()
if not user:
    # Create test user
    user = User(
        email='testuser@testtrack.com',
        username='testuser',
        full_name='Test User',
        hashed_password=hash_password('TestPass123!'),
        role='tester',
        status='active',
        is_active=True,
        is_verified=True
    )
    session.add(user)
    session.commit()
    print(f"Created test user: {user.email}")
else:
    print(f"Test user exists: {user.email}, Role: {user.role}, Active: {user.is_active}")

session.close()

# Now test login
import requests

resp = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'testuser@testtrack.com',
    'password': 'TestPass123!'
})

print(f"\nLogin response status: {resp.status_code}")
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
    if tc_resp.status_code != 201:
        print(f"Error: {tc_resp.json()}")
    else:
        print(f"✓ Test case created successfully")
else:
    print(f"✗ Login failed: {resp.json()}")
