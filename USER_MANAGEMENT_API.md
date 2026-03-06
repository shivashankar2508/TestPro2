# User Management API Documentation

## Overview

The User Management API provides comprehensive endpoints for managing users, roles, permissions, and account operations. All administrative operations require admin role authentication.

## Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/users/me` | User | Get current user info |
| PUT | `/api/users/me` | User | Update current user profile |
| GET | `/api/users` | Admin | List all users (paginated) |
| GET | `/api/users/{user_id}` | Admin/Self | Get user details |
| POST | `/api/users` | Admin | Create new user |
| PUT | `/api/users/{user_id}` | Admin | Update user |
| PUT | `/api/users/{user_id}/role` | Admin | Change user role |
| POST | `/api/users/{user_id}/lock` | Admin | Lock user account |
| POST | `/api/users/{user_id}/unlock` | Admin | Unlock user account |
| DELETE | `/api/users/{user_id}` | Admin | Deactivate user account |
| GET | `/api/users/{user_id}/audit-logs` | Admin/Self | Get user audit logs |
| GET | `/api/users/stats/overview` | Admin | Get user statistics |

---

## User Endpoints (Self-Service)

### Get Current User Info

**Endpoint:** `GET /api/users/me`

**Authentication:** Required (any role)

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "tester",
  "is_verified": true,
  "is_active": true,
  "status": "active",
  "last_login": "2026-03-02T10:30:00",
  "created_at": "2026-03-01T08:00:00"
}
```

### Update Current User Profile

**Endpoint:** `PUT /api/users/me`

**Authentication:** Required (any role)

**Request Body:**
```json
{
  "full_name": "John Updated Doe",
  "email": "newemail@example.com"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "newemail@example.com",
  "username": "johndoe",
  "full_name": "John Updated Doe",
  ...
}
```

---

## Admin Endpoints

### List Users (Paginated)

**Endpoint:** `GET /api/users`

**Authentication:** Admin only

**Query Parameters:**
- `page` (default: 1) - Page number
- `page_size` (default: 10, max: 100) - Items per page
- `role` (optional) - Filter by role: tester, developer, admin
- `status` (optional) - Filter by status: active, inactive, locked, pending_verification
- `search` (optional) - Search by email or username

**Example Request:**
```bash
GET /api/users?page=1&page_size=20&role=tester&search=john
```

**Response:**
```json
{
  "total": 145,
  "page": 1,
  "page_size": 20,
  "users": [
    {
      "id": 1,
      "email": "user@example.com",
      "username": "johndoe",
      "full_name": "John Doe",
      "role": "tester",
      "is_verified": true,
      "is_active": true,
      "status": "active",
      "last_login": "2026-03-02T10:30:00",
      "created_at": "2026-03-01T08:00:00"
    },
    ...
  ]
}
```

### Get User Details

**Endpoint:** `GET /api/users/{user_id}`

**Authentication:** Admin or self

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "tester",
  "is_verified": true,
  "is_active": true,
  "status": "active",
  "last_login": "2026-03-02T10:30:00",
  "created_at": "2026-03-01T08:00:00"
}
```

### Create User

**Endpoint:** `POST /api/users`

**Authentication:** Admin only

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "username": "newusername",
  "full_name": "New User",
  "role": "tester",
  "temporary_password": "TempPass123!" // optional
}
```

**Response:**
```json
{
  "id": 42,
  "email": "newuser@example.com",
  "username": "newusername",
  "full_name": "New User",
  "role": "tester",
  "is_verified": true,
  "is_active": true,
  "status": "active",
  "created_at": "2026-03-02T11:00:00"
}
```

**Notes:**
- Admin can create users directly (bypasses email verification)
- If no temporary password provided, a random one is generated
- Welcome email sent with credentials (or password reset link)

### Update User

**Endpoint:** `PUT /api/users/{user_id}`

**Authentication:** Admin only

**Request Body:**
```json
{
  "full_name": "Updated Name",
  "email": "updatedemail@example.com"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "updatedemail@example.com",
  "full_name": "Updated Name",
  ...
}
```

### Change User Role

**Endpoint:** `PUT /api/users/{user_id}/role`

**Authentication:** Admin only

**Request Body:**
```json
{
  "role": "developer"  // tester, developer, or admin
}
```

**Response:**
```json
{
  "id": 1,
  "role": "developer",
  ...
}
```

**Notes:**
- Cannot demote last admin user
- Sends email notification to user
- Logged in audit trail

### Lock User Account

**Endpoint:** `POST /api/users/{user_id}/lock`

**Authentication:** Admin only

**Response:**
```json
{
  "message": "User account locked until 2026-04-01T10:00:00",
  "locked_until": "2026-04-01T10:00:00"
}
```

**Notes:**
- Account locked for 30 days by default
- User cannot login until unlocked
- Sends email notification to user

### Unlock User Account

**Endpoint:** `POST /api/users/{user_id}/unlock`

**Authentication:** Admin only

**Response:**
```json
{
  "message": "User account unlocked"
}
```

**Notes:**
- Resets failed login attempts
- Sends email notification to user

### Deactivate User (Soft Delete)

**Endpoint:** `DELETE /api/users/{user_id}`

**Authentication:** Admin only

**Response:**
```json
{
  "message": "User johndoe has been deactivated",
  "user_id": 1
}
```

**Notes:**
- Soft delete (data preserved)
- User cannot login
- Cannot delete last admin user
- Sends email notification to user

---

## Audit & Statistics

### Get User Audit Logs

**Endpoint:** `GET /api/users/{user_id}/audit-logs`

**Authentication:** Admin or self

**Query Parameters:**
- `page` (default: 1)
- `page_size` (default: 20, max: 100)

**Response:**
```json
[
  {
    "id": 1,
    "action": "profile_update",
    "resource_type": "user",
    "resource_id": 1,
    "details": "Updated profile: full_name=John Doe",
    "ip_address": "192.168.1.100",
    "created_at": "2026-03-02T10:30:00"
  },
  ...
]
```

### Get User Statistics

**Endpoint:** `GET /api/users/stats/overview`

**Authentication:** Admin only

**Response:**
```json
{
  "total_users": 145,
  "active_users": 120,
  "verified_users": 118,
  "locked_users": 2,
  "by_role": {
    "testers": 100,
    "developers": 40,
    "admins": 5
  }
}
```

---

## Error Responses

### User Not Found
```json
{
  "error_code": "USER_NOT_FOUND",
  "message": "User not found"
}
```

### Permission Denied
```json
{
  "error_code": "PERMISSION_DENIED",
  "message": "You don't have permission to access this resource"
}
```

### User Already Exists
```json
{
  "error_code": "USER_EXISTS",
  "message": "User already exists"
}
```

### Cannot Delete Last Admin
```json
{
  "error_code": "CANNOT_DELETE",
  "message": "Cannot deactivate the last admin user"
}
```

### Invalid Role
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid role: super_admin"
}
```

---

## Features Implemented

### ✅ Security
- Role-based access control (RBAC)
- Admin-only operations protected
- Self-service operations available
- Audit logging for all admin actions
- Email notifications for account changes

### ✅ User Management
- Create, update, deactivate users
- Role assignment (tester, developer, admin)
- Account locking/unlocking (admin/automated)
- Soft delete (preserves data)
- Last admin protection (cannot delete/demote)

### ✅ Pagination & Search
- Paginated user lists
- Filter by role, status
- Search by email/username
- Configurable page size (max 100)

### ✅ Audit Trail
- All admin actions logged
- User profile updates logged
- Accessible to admins and users (own logs)
- Includes IP address tracking

### ✅ Email Notifications
- Welcome emails (with temp password)
- Role change notifications
- Account locked/unlocked notifications
- Account deactivation notifications

---

## Usage Examples

### Bash (cURL)

**List users:**
```bash
curl -X GET "http://localhost:8000/api/users?page=1&page_size=20&role=tester" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Create user:**
```bash
curl -X POST "http://localhost:8000/api/users" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "full_name": "New User",
    "role": "tester"
  }'
```

**Change role:**
```bash
curl -X PUT "http://localhost:8000/api/users/1/role" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "developer"}'
```

### Python (httpx)

```python
import httpx

BASE_URL = "http://localhost:8000/api"
ADMIN_TOKEN = "your_admin_token"

# List users
response = await httpx.get(
    f"{BASE_URL}/users",
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    params={"page": 1, "page_size": 20}
)
users_data = response.json()

# Create user
new_user = {
    "email": "newuser@example.com",
    "username": "newuser",
    "full_name": "New User",
    "role": "tester"
}

response = await httpx.post(
    f"{BASE_URL}/users",
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    json=new_user
)
created_user = response.json()
```

---

## Testing

Run user management tests:
```bash
pytest backend/tests/test_users.py -v
```

---

**Created:** March 2, 2026
**Status:** Production Ready ✅
