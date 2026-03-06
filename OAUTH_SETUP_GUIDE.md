# Google & GitHub OAuth Setup Guide

## 🎯 Overview
Google and GitHub OAuth login is already integrated into TestTrack Pro. This guide shows you how to enable it.

---

## 📋 Prerequisites
- Google/GitHub accounts
- Backend running on http://localhost:8001
- Frontend running on http://localhost:3000

---

## **PART 1: Google OAuth Setup**

### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project:
   - Click "Select a Project" → "NEW PROJECT"
   - Name: "TestTrack Pro"
   - Click "CREATE"

3. Enable Google+ API:
   - In the Search bar, type "Google+ API"
   - Click on it and press "ENABLE"

4. Create OAuth 2.0 Credentials:
   - Go to **Credentials** (left sidebar)
   - Click **+ CREATE CREDENTIALS** → **OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Name: "TestTrack Pro Web"

5. Add Authorized Redirect URIs:
   - Add: `http://localhost:3000/auth/oauth-callback`
   - Add: `http://localhost:3000/dashboard` (optional, for live)
   - If deploying: Add your production domain

6. **Save the credentials:**
   - Copy **Client ID** and **Client Secret**
   - Keep these safe!

### Step 2: Update .env File

Create or update `.env` file in the backend directory:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
```

---

## **PART 2: GitHub OAuth Setup**

### Step 1: Create GitHub OAuth Application

1. Go to **GitHub Settings** → **Developer settings** → **OAuth Apps**
   - Link: https://github.com/settings/developers

2. Click **New OAuth App**

3. Fill in the form:
   - **Application name**: TestTrack Pro
   - **Homepage URL**: http://localhost:3000
   - **Authorization callback URL**: http://localhost:3000/auth/oauth-callback
   - **Description**: Test tracking and management application

4. **Save the credentials:**
   - Copy **Client ID** and **Client Secret**
   - Keep these safe!

### Step 2: Update .env File

Add to `.env` file:

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
```

---

## **PART 3: Complete .env Example**

Your complete `.env` file should look like:

```bash
# Database
DATABASE_URL=sqlite:///./testtrack.db

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS & URLs
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8001
FRONTEND_URL=http://localhost:3000

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here

# Environment
ENV=development
LOG_LEVEL=INFO
```

---

## **PART 4: Restart Services**

After updating `.env`:

### Restart Backend:
```powershell
# Terminal 1
cd C:\Users\HP\Desktop\Me\testtrack-pro\backend
$env:PYTHONPATH="$pwd"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Frontend already running? No restart needed.

---

## **PART 5: Test OAuth Login**

### Option A: Via Login Page

1. Go to http://localhost:3000/auth/login.html
2. Click **"Google"** or **"GitHub"** button
3. You'll be redirected to Google/GitHub login
4. Approve permissions
5. Automatically redirected back to dashboard

### Option B: Direct API Test

```powershell
# Get Google authorization URL
curl "http://localhost:8001/api/auth/oauth/google/authorize?redirect_uri=http://localhost:3000/auth/oauth-callback"

# Get GitHub authorization URL
curl "http://localhost:8001/api/auth/oauth/github/authorize?redirect_uri=http://localhost:3000/auth/oauth-callback"
```

---

## **PART 6: How It Works (Architecture)**

### Flow Diagram:
```
1. User clicks "Google" or "GitHub" button on login page
   ↓
2. Frontend calls: GET /api/auth/oauth/{provider}/authorize
   ↓
3. Backend returns authorization URL + state token (CSRF protection)
   ↓
4. Frontend redirects user to Google/GitHub login
   ↓
5. User approves permissions
   ↓
6. Google/GitHub redirects to: /auth/oauth-callback?code=...&state=...
   ↓
7. Frontend calls: POST /api/auth/oauth/{provider}/callback
   ↓
8. Backend exchanges code for access token
   ↓
9. Backend fetches user info (email, name, avatar)
   ↓
10. Backend finds or creates user account
    ↓
11. Backend returns JWT tokens
    ↓
12. Frontend stores tokens in localStorage
    ↓
13. User redirected to dashboard ✅
```

---

## **PART 7: Frontend Components**

### Login Page (`/auth/login.html`)
- OAuth buttons already integrated
- Automatic redirect to oauth-callback

### OAuth Callback Handler (`/auth/oauth-callback.html`)
- Processes OAuth response
- Exchanges code for tokens
- Redirects to dashboard
- Shows error message if failed

### JavaScript Files:
- **oauth.js** - OAuth logic
- **auth.js** - Login/authentication
- **api.js** - API communication

---

## **PART 8: Backend Routes**

### Authorization URLs:
```
GET  /api/auth/oauth/google/authorize
GET  /api/auth/oauth/github/authorize
```

### Callbacks:
```
POST /api/auth/oauth/google/callback
POST /api/auth/oauth/github/callback
```

### Link OAuth Account:
```
POST /api/auth/oauth/link
```

---

## **PART 9: Troubleshooting**

### ❌ "Invalid OAuth credentials"
- ✅ Check Client ID and Secret are correct
- ✅ Verify they're in .env file
- ✅ Restart backend after updating .env

### ❌ "Redirect URI mismatch"
- ✅ Ensure callback URL matches exactly:
  - Google/GitHub settings: `http://localhost:3000/auth/oauth-callback`
  - .env: `FRONTEND_URL=http://localhost:3000`

### ❌ "State token invalid"
- ✅ Clean browser cache and cookies
- ✅ Ensure clocks are synchronized
- ✅ Try in incognito/private mode

### ❌ "User info not retrieved"
- ✅ Check network tab in Developer Tools
- ✅ Verify API endpoint in browser console
- ✅ Check backend logs for errors

### ❌ "Still stuck on login page after authentication"
- ✅ Check browser console for JavaScript errors
- ✅ Check network requests in Developer Tools
- ✅ Verify tokens are being stored in localStorage

---

## **PART 10: Production Deployment**

### Before deploying:

1. **Update callback URLs:**
   - Google: `https://yourdomain.com/auth/oauth-callback`
   - GitHub: `https://yourdomain.com/auth/oauth-callback`

2. **Update .env:**
   ```bash
   FRONTEND_URL=https://yourdomain.com
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

3. **Security checklist:**
   - ✅ Use strong SECRET_KEY (32+ chars)
   - ✅ Keep Client IDs and Secrets secure
   - ✅ Use HTTPS only
   - ✅ Set ENV=production
   - ✅ Hide API docs (docs_url=None)

---

## **PART 11: Features**

### Supported Features:
- ✅ Google & GitHub login
- ✅ Auto-create user account
- ✅ Link OAuth accounts to existing accounts
- ✅ CSRF protection (state tokens)
- ✅ Secure token exchange
- ✅ User profile auto-population

### Coming Soon:
- Multi-account linking
- OAuth account unlinking
- Provider-specific settings

---

## **Quick Test Checklist**

- [ ] Google Client ID and Secret obtained
- [ ] GitHub Client ID and Secret obtained
- [ ] .env file updated with credentials
- [ ] Backend restarted
- [ ] Frontend loaded (http://localhost:3000)
- [ ] Login page has OAuth buttons visible
- [ ] Can click "Google" button without errors
- [ ] Can click "GitHub" button without errors
- [ ] Redirected to provider's login page
- [ ] After approval, returns to dashboard
- [ ] User account created automatically
- [ ] Can logout and login again

---

## **Support**

If you encounter issues:
1. Check the browser console (F12)
2. Check backend logs for errors
3. Verify .env file is correct
4. Clear browser cache and cookies
5. Try in incognito mode

---

## **Security Notes**

✅ **What's protected:**
- State tokens prevent CSRF attacks
- Secrets never exposed to frontend
- Tokens stored securely
- HTTPS recommended for production
- Access tokens refreshable

⚠️ **Best practices:**
- Never commit .env to git
- Rotate secrets regularly
- Use HTTPS in production
- Monitor access logs
- Limit API scopes

---

**That's it! Google and GitHub login is ready to use!** 🚀
