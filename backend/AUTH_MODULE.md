# Authentication & Authorization Module Documentation

## Overview
Comprehensive authentication and authorization system for TestTrack Pro with role-based access control (RBAC).

## Features Implemented

### 1. User Registration (FR-AUTH-001) ✅
- Email and password registration
- Email verification required before account activation
- Password strength requirements:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character
- Verification token expires in 24 hours
- Audit logging

**Endpoint**: `POST /api/auth/register`

### 2. User Login (FR-AUTH-002) ✅
- Email/password authentication with JWT tokens
- Account lockout after 5 failed attempts (15-minute lockout)
- "Remember me" functionality (extended session: 24 hours instead of 15 minutes)
- Access token expiry: 15 minutes
- Refresh token expiry: 7 days
- Audit logging with IP address and user agent
- Automatic account unlock after lockout period

**Endpoint**: `POST /api/auth/login`

### 3. Password Management (FR-AUTH-003) ✅
- Forgot password flow with email reset link
- Reset link expires in 1 hour
- Password change requires current password verification
- Password history check (cannot reuse last 5 passwords)
- Secure token-based password reset
- Audit logging

**Endpoints**:
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/change-password`

### 4. Session Management (FR-AUTH-004) ✅
- JWT-based authentication with access and refresh tokens
- Seamless token refresh using refresh tokens
- Logout from single device (revoke current refresh token)
- Logout from all devices (revoke all refresh tokens)
- Token type verification
- Secure token storage with expiry tracking

**Endpoints**:
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all-devices`

### 5. Email Verification ✅
- Email verification with token-based system
- 24-hour expiration
- Resend capability
- HTML email templates

**Endpoint**: `POST /api/auth/verify-email`

## Database Models

### Users Table
```sql
- id (Primary Key)
- email (Unique, Indexed)
- username (Unique, Indexed)
- full_name
- hashed_password
- is_active (Boolean)
- is_verified (Boolean)
- verification_token
- verification_token_expiry
- verified_at
- role (tester, developer, admin)
- status (active, inactive, locked, pending_verification)
- failed_login_attempts (Security)
- locked_until (Security)
- google_id (OAuth)
- github_id (OAuth)
- last_login
- created_at
- updated_at
```

### Supporting Tables
- **password_history**: Track last 5 passwords to prevent reuse
- **refresh_tokens**: Store refresh tokens with expiry and revocation status
- **audit_logs**: Track all user actions (login, logout, password change, etc.)
- **oauth_providers**: Store OAuth account linkings

## Role-Based Access Control (RBAC)

### Available Roles
1. **TESTER**: Can create, edit, execute test cases
2. **DEVELOPER**: Can view reports, update issues
3. **ADMIN**: System administration (bonus feature)

### Role Checking Dependencies
```python
# Tester only
@router.get("/tests", dependencies=[Depends(require_tester)])

# Developer only
@router.get("/reports", dependencies=[Depends(require_developer)])

# Admin only
@router.get("/admin", dependencies=[Depends(require_admin)])

# Any authenticated user
@router.get("/profile", dependencies=[Depends(get_current_user)])
```

## Security Features

### Password Security
- Bcrypt hashing with salt
- Strength validation on registration and reset
- Password history tracking (last 5)
- Can change only with current password verification

### Token Security
- JWT with HS256 algorithm
- Separate access and refresh tokens
- Token type verification
- Token expiry tracking
- Refresh token revocation capability
- Token blacklisting (in database)

### Rate Limiting & Lockout
- Account lockout after 5 failed login attempts
- 15-minute lockout duration
- Automatic unlock after timeout
- Email notification on lockout
- Failed attempt counter reset on successful login

### Email Security
- Email verification before account activation
- Secure token generation (secrets.token_urlsafe)
- Token expiry enforcement
- One-time use tokens

### Audit Logging
- Track all authentication actions
- Record IP address and user agent
- Timestamps for all actions
- User identification for audit trail

## API Endpoints

### Authentication Routes

#### Register
```
POST /api/auth/register
Content-Type: application/json

{
  "email": "john.tester@company.com",
  "username": "johntester",
  "full_name": "John Tester",
  "password": "SecurePass@123"
}

Response (201):
{
  "id": 1,
  "email": "john.tester@company.com",
  "username": "johntester",
  "full_name": "John Tester",
  "role": "tester",
  "is_verified": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Verify Email
```
POST /api/auth/verify-email
{
  "token": "email-verification-token"
}

Response (200):
{
  "message": "Email verified successfully"
}
```

#### Login
```
POST /api/auth/login
{
  "email": "john.tester@company.com",
  "password": "SecurePass@123",
  "remember_me": true
}

Response (200):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### Refresh Token
```
POST /api/auth/refresh
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response (200):
{
  "access_token": "new-access-token",
  "refresh_token": "original-refresh-token",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### Forgot Password
```
POST /api/auth/forgot-password
{
  "email": "john.tester@company.com"
}

Response (200):
{
  "message": "If email exists, reset link has been sent"
}
```

#### Reset Password
```
POST /api/auth/reset-password
{
  "token": "password-reset-token",
  "new_password": "NewSecurePass@123"
}

Response (200):
{
  "message": "Password reset successfully"
}
```

#### Change Password
```
POST /api/auth/change-password
Authorization: Bearer {access_token}

{
  "current_password": "OldPass@123",
  "new_password": "NewSecurePass@456"
}

Response (200):
{
  "message": "Password changed successfully"
}
```

#### Logout
```
POST /api/auth/logout
Authorization: Bearer {access_token}

Response (200):
{
  "message": "Logged out successfully"
}
```

#### Logout All Devices
```
POST /api/auth/logout-all-devices
Authorization: Bearer {access_token}

Response (200):
{
  "message": "Logged out from all devices"
}
```

## Environment Configuration

Required environment variables (see `.env.example`):

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/testtrack_pro

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SENDER_NAME=TestTrack Pro
FRONTEND_URL=http://localhost:3000

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Usage Examples

### Using Authentication in Protected Routes

```python
from fastapi import APIRouter, Depends
from backend.app.utils.auth_middleware import (
    get_current_user, require_tester, require_developer, require_admin
)

router = APIRouter()

# Any authenticated user
@router.get("/profile")
async def get_profile(current_user = Depends(get_current_user)):
    return {"user": current_user.email, "role": current_user.role}

# Only testers
@router.post("/test-cases")
async def create_test_case(
    test_data: TestCaseCreate,
    current_user = Depends(require_tester)
):
    # Only testers can reach here
    pass

# Only developers
@router.get("/assigned-issues")
async def get_assigned_issues(current_user = Depends(require_developer)):
    # Only developers can reach here
    pass

# Only admins
@router.get("/admin/users")
async def list_users(current_user = Depends(require_admin)):
    # Only admins can reach here
    pass
```

## Testing

Run tests with:
```bash
pytest backend/tests/test_auth.py -v
pytest backend/tests/test_security.py -v
```

### Test Coverage
- ✅ User registration with valid/invalid data
- ✅ Password strength validation
- ✅ Email verification
- ✅ Login flow
- ✅ Account lockout
- ✅ Password reset
- ✅ Token generation and validation
- ✅ Token refresh
- ✅ JWT operations

## Future Enhancements

### OAuth Integration (FR-AUTH-005)
- Google OAuth login
- GitHub OAuth login
- Account linking for existing users
- Social login button integration

### Advanced Features
- Two-factor authentication (2FA)
- Biometric authentication
- Single Sign-On (SSO)
- Social media integration
- IP-based restrictions
- Geolocation tracking

## Security Best Practices

1. **HTTPS Only**: Always use HTTPS in production
2. **Secret Key**: Change SECRET_KEY in production to a strong random value
3. **Token Storage**: Store tokens securely in HTTP-only cookies
4. **CORS**: Restrict ALLOWED_ORIGINS to trusted domains
5. **Rate Limiting**: Implement rate limiting on auth endpoints
6. **Email Validation**: Verify SMTP credentials properly
7. **Audit Logs**: Regularly review audit logs for suspicious activity
8. **Password Policy**: Enforce strong password policies

## Troubleshooting

### Email Not Sending
- Check SMTP_SERVER and SMTP_PORT
- Verify SENDER_EMAIL and SENDER_PASSWORD
- For Gmail: Use app-specific passwords (not regular password)
- Check firewall/port 587 is accessible

### Token Validation Fails
- Verify SECRET_KEY is consistent
- Check token expiry time
- Ensure ALGORITHM is correct (HS256)

### Account Locked
- User will be automatically unlocked after 15 minutes
- Can be manually unlocked by admin

## License
ISC
