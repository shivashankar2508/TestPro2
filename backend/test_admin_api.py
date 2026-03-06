#!/usr/bin/env python
"""Test admin API endpoints"""
import requests
import json

# Login as admin
print("1. Logging in as admin...")
login_resp = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'admin@testtrack.com',
    'password': 'Admin@123'
})

if login_resp.status_code != 200:
    print(f"[FAIL] Login failed: {login_resp.text}")
    exit(1)

token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print(f"[OK] Login successful")

# Test system stats
print("\n2. Testing /api/system/stats:")
stats_resp = requests.get('http://localhost:8000/api/system/stats', headers=headers)
print(f"   Status: {stats_resp.status_code}")
if stats_resp.status_code == 200:
    stats = stats_resp.json()
    print(f"   [OK] Stats received:")
    print(f"     Total Users: {stats.get('total_users')}")
    print(f"     Active Users: {stats.get('active_users')}")
    print(f"     Total Projects: {stats.get('total_projects')}")
    print(f"     Total Test Cases: {stats.get('total_test_cases')}")
    print(f"     Total Executions: {stats.get('total_executions')}")
    print(f"     Last Backup: {stats.get('last_backup')}")
else:
    print(f"   [FAIL] Error: {stats_resp.text}")

# Test permissions endpoint
print("\n3. Testing /api/permissions:")
perms_resp = requests.get('http://localhost:8000/api/permissions', headers=headers)
print(f"   Status: {perms_resp.status_code}")
if perms_resp.status_code == 200:
    perms = perms_resp.json()
    perms_list = perms if isinstance(perms, list) else perms.get('permissions', [])
    print(f"   [OK] Permissions received: {len(perms_list)} permissions")
else:
    print(f"   [FAIL] Error: {perms_resp.text}")

# Test projects endpoint
print("\n4. Testing /api/projects:")
projects_resp = requests.get('http://localhost:8000/api/projects', headers=headers)
print(f"   Status: {projects_resp.status_code}")
if projects_resp.status_code == 200:
    projects = projects_resp.json()
    proj_list = projects if isinstance(projects, list) else projects.get('projects', [])
    print(f"   [OK] Projects received: {len(proj_list)} projects")
else:
    print(f"   [FAIL] Error: {projects_resp.text}")

# Test health check
print("\n5. Testing /api/system/health-check:")
health_resp = requests.post('http://localhost:8000/api/system/health-check', headers=headers)
print(f"   Status: {health_resp.status_code}")
if health_resp.status_code == 200:
    health = health_resp.json()
    print(f"   [OK] Health: {health.get('status')} - Database: {health.get('database')}")
else:
    print(f"   [FAIL] Error: {health_resp.text}")

print("\n[OK] All tests complete")
