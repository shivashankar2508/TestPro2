# OAuth Integration Guide - TestTrack Pro

## Overview

TestTrack Pro supports OAuth authentication through **Google** and **GitHub**. Users can:

1. **Sign up/Login with OAuth** - Direct account creation via OAuth providers
2. **Link OAuth accounts** - Connect OAuth providers to existing accounts
3. **Unlink OAuth accounts** - Remove OAuth provider links
4. **Account persistence** - Seamless switching between OAuth and password auth

## Architecture

### Frontend Flow

```
User clicks OAuth button
    ↓
Frontend requests authorization URL → Backend
    ↓
Backend generates state token + returns auth URL
    ↓
Frontend redirects to OAuth provider (Google/GitHub)
    ↓
User authorizes
    ↓
OAuth provider redirects to callback → Frontend
    ↓
Frontend posts code + state to backend
    ↓
Backend validates state, exchanges code for token
    ↓
Backend fetches user info, creates/links account
    ↓
Frontend stores tokens, redirects to dashboard
```

### Backend Components

**Modules:**
- `backend/app/utils/oauth.py` - Core OAuth logic
  - `GoogleOAuth` - Google-specific implementation
  - `GitHubOAuth` - GitHub-specific implementation
  - `OAuthStateManager` - CSRF protection via state tokens
  - `OAuthUserData` - User data extraction from providers

- `backend/app/utils/oauth_security.py` - Security features
  - `OAuthTokenEncryption` - Token encryption/decryption
  - `OAuthSecurityValidator` - URI/state/PKCE validation
  - `OAuthRateLimiter` - Rate limiting for callback attempts

- `backend/app/api/routes/oauth.py` - API endpoints
  - Authorization URL generation
  - OAuth callbacks (Google, GitHub)
  - Account linking/unlinking
  - Linked accounts retrieval

## Setup Instructions

### 1. Google OAuth Setup

**Create Google OAuth App:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project → "TestTrack Pro"
3. Enable "Google+ API"
4. Create "OAuth 2.0 Client ID" (Web application)
5. Add authorized redirect URIs:
   - `http://localhost:3000/auth/oauth-callback` (development)
   - `https://yourdomain.com/auth/oauth-callback` (production)

**Add to `.env`:**
```env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```

### 2. GitHub OAuth Setup

**Create GitHub OAuth App:**
1. Go to [GitHub Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
2. Create "New OAuth App"
3. Application name: "TestTrack Pro"
4. Homepage URL: `http://localhost:3000` (or your domain)
5. Authorization callback URL: `http://localhost:3000/auth/oauth-callback`

**Add to `.env`:**
```env
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### 3. Frontend URL Configuration

Update `.env.example`:
```env
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8000/api
```

## API Endpoints

### Get Authorization URL

**Google:**
```bash
GET /api/auth/oauth/google/authorize?redirect_uri=http://localhost:3000/auth/oauth-callback

Response:
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_token",
  "provider": "google"
}
```

**GitHub:**
```bash
GET /api/auth/oauth/github/authorize?redirect_uri=http://localhost:3000/auth/oauth-callback

Response:
{
  "authorization_url": "https://github.com/login/oauth/authorize?...",
  "state": "random_state_token",
  "provider": "github"
}
```

### OAuth Callback

**Google:**
```bash
POST /api/auth/oauth/google/callback
Content-Type: application/json

{
  "code": "oauth_authorization_code",
  "state": "state_token_from_authorize",
  "redirect_uri": "http://localhost:3000/auth/oauth-callback"
}

Response:
{
  "id": 1,
  "email": "user@gmail.com",
  "username": "user123",
  "full_name": "John Doe",
  "role": "tester",
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "bearer"
}
```

**GitHub:**
```bash
POST /api/auth/oauth/github/callback
Content-Type: application/json

{
  "code": "oauth_authorization_code",
  "state": "state_token_from_authorize",
  "redirect_uri": "http://localhost:3000/auth/oauth-callback"
}

Response: (Same as Google)
```

### Link OAuth Account

**Authenticated users can link OAuth providers:**
```bash
POST /api/auth/oauth/link
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "provider": "google",          # or "github"
  "provider_id": "google_12345",
  "email": "user@gmail.com"
}

Response:
{
  "message": "Google account linked successfully",
  "provider": "google"
}
```

### Unlink OAuth Account

```bash
POST /api/auth/oauth/unlink
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "provider": "google"           # or "github"
}

Response:
{
  "message": "Google account unlinked successfully",
  "provider": "google"
}
```

### Get Linked Accounts

```bash
GET /api/auth/oauth/linked-accounts
Authorization: Bearer {access_token}

Response:
{
  "linked_accounts": [
    {
      "provider": "google",
      "email": "user@gmail.com",
      "linked_at": "2026-03-02T10:30:00"
    },
    {
      "provider": "github",
      "email": "user@github.com",
      "linked_at": "2026-03-02T10:35:00"
    }
  ]
}
```

## Frontend Usage

### Initiating OAuth Login

```javascript
// Trigger authorization URL request
await initiateGoogleOAuth();  // or initiateGitHubOAuth()

// This will:
// 1. Request authorization URL from backend
// 2. Create state token
// 3. Redirect user to OAuth provider
```

### OAuth Callback Handling

**automatic on `/auth/oauth-callback`:**
```javascript
// Automatically called when OAuth callback returns
handleOAuthCallback();

// This will:
// 1. Extract code + state from URL
// 2. Send to backend callback endpoint
// 3. Receive JWT tokens
// 4. Store tokens in localStorage
// 5. Redirect to dashboard
```

### Linking Accounts

```javascript
// User is already logged in
await linkOAuthAccount('google');  // or 'github'

// This will:
// 1. Request user authorization on OAuth provider
// 2. Exchange code for tokens
// 3. Link provider to existing account
```

### Unlinking Accounts

```javascript
// User is already logged in
await unlinkOAuthAccount('google');  // or 'github'

// This will:
// 1. Remove OAuth provider link
// 2. User can still login with password
```

## Security Measures

### 1. State Token Protection (CSRF)
- Every OAuth flow starts with state token generation
- State is validated before processing callback
- State expires after 10 minutes
- Prevents unauthorized OAuth exploits

### 2. Token Encryption
- OAuth tokens can be encrypted at rest
- Uses Fernet symmetric encryption
- Key stored in environment variables

### 3. Redirect URI Validation
- Only whitelisted redirect URIs are accepted
- Prevents open redirect vulnerabilities
- Validates both authorization and callback redirects

### 4. Rate Limiting
- OAuth callbacks are rate-limited per user
- Max 10 attempts per 5 minutes
- Prevents brute force attacks

### 5. Account Linking Safety
- OAuth provider ID is globally unique
- Prevents duplicate account linking
- Error if already linked to another user

## Database Schema

### OAuthProvider Table

```sql
CREATE TABLE oauth_providers (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL FOREIGN KEY,
  provider VARCHAR(50) NOT NULL,        -- 'google' or 'github'
  provider_id VARCHAR(255) NOT NULL,    -- OAuth provider's user ID
  email VARCHAR(255),                   -- OAuth provider's email
  access_token TEXT,                    -- OAuth access token (encrypted)
  refresh_token TEXT,                   -- OAuth refresh token (encrypted)
  token_expiry DATETIME,                -- Token expiration time
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(provider, provider_id),        -- One account per provider
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

## Testing

Run OAuth tests:
```bash
pytest backend/tests/test_oauth.py -v
```

**Test Coverage:**
- Authorization URL generation (Google/GitHub)
- Callback processing
- State validation
- Account linking/unlinking
- Error handling (invalid state, duplicate provider)
- Security validation (redirect URI, PKCE)

## Troubleshooting

### Issue: "Invalid OAuth credentials"
**Solution:** Verify `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` in `.env`

### Issue: "Redirect URI mismatch"
**Solution:** Ensure the callback URL in .env matches exactly with OAuth app settings (including protocol and port)

### Issue: "Invalid or expired state token"
**Solution:** State tokens expire after 10 minutes. Check browser clock sync with server.

### Issue: "Account already linked"
**Solution:** That OAuth provider is linked to another account. Unlink from other account first or use different email.

## Production Deployment

### Security Checklist
- [ ] Use HTTPS only (not HTTP)
- [ ] Update OAuth redirect URIs to production domains
- [ ] Generate strong encryption key for token storage
- [ ] Enable rate limiting configuration
- [ ] Monitor audit logs for failed OAuth attempts
- [ ] Regular security updates for httpx library
- [ ] Implement OAuth token refresh logic
- [ ] Set up monitoring/alerting for OAuth failures

### HTTPS Configuration

```env
# Production .env
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com
GOOGLE_CLIENT_ID=production_client_id
GOOGLE_CLIENT_SECRET=production_client_secret
GITHUB_CLIENT_ID=production_client_id
GITHUB_CLIENT_SECRET=production_client_secret
ENCRYPTION_KEY=your_generated_key_here
```

## Future Enhancements

1. **OAuth Token Refresh** - Auto-refresh expired OAuth tokens
2. **PKCE Flow** - Enhanced security for mobile apps
3. **Multiple OAuth Providers** - Add LinkedIn, Microsoft, Apple
4. **Profile Sync** - Keep account data in sync with providers
5. **Social Features** - Share test results on social media
