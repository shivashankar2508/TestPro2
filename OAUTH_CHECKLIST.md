# 📋 OAuth Setup Checklist - TestTrack Pro

## Pre-Setup
- [ ] Backend is running on http://localhost:8001
- [ ] Frontend is running on http://localhost:3000
- [ ] You have admin access to your Google account
- [ ] You have an active GitHub account

---

## Google OAuth Setup

### Create Google Credentials
- [ ] Go to https://console.cloud.google.com/
- [ ] Clicked "Select a Project" → "NEW PROJECT"
- [ ] Named it "TestTrack Pro"
- [ ] Created the project
- [ ] Searched for "Google+ API"
- [ ] Enabled Google+ API
- [ ] Went to Credentials section
- [ ] Clicked "+ CREATE CREDENTIALS"
- [ ] Selected "OAuth 2.0 Client ID"
- [ ] Selected "Web application"
- [ ] Named it "TestTrack Pro Web"
- [ ] Added Redirect URI: `http://localhost:3000/auth/oauth-callback`
- [ ] Copied **Client ID**: `_________________________` (save this)
- [ ] Copied **Client Secret**: `_________________________` (save this)

---

## GitHub OAuth Setup

### Create GitHub Credentials
- [ ] Went to https://github.com/settings/developers
- [ ] Clicked "OAuth Apps"
- [ ] Clicked "New OAuth App"
- [ ] Filled in:
  - [ ] Application name: "TestTrack Pro"
  - [ ] Homepage URL: "http://localhost:3000"
  - [ ] Authorization callback URL: "http://localhost:3000/auth/oauth-callback"
- [ ] Copied **Client ID**: `_________________________` (save this)
- [ ] Copied **Client Secret**: `_________________________` (save this)

---

## Environment Configuration

### Create .env File
- [ ] Navigated to `C:\Users\HP\Desktop\Me\testtrack-pro\backend`
- [ ] Created or opened `.env` file
- [ ] Added Google credentials:
  ```
  GOOGLE_CLIENT_ID=your_value_here
  GOOGLE_CLIENT_SECRET=your_value_here
  ```
- [ ] Added GitHub credentials:
  ```
  GITHUB_CLIENT_ID=your_value_here
  GITHUB_CLIENT_SECRET=your_value_here
  ```
- [ ] Saved the file

### Verify Other Environment Variables
- [ ] `DATABASE_URL` is set and valid
- [ ] `SECRET_KEY` is set (at least 32 chars for production)
- [ ] `FRONTEND_URL=http://localhost:3000`
- [ ] `ALLOWED_ORIGINS` includes `http://localhost:3000`

---

## Backend Configuration

### Restart Backend
- [ ] Stopped the backend server (Ctrl+C)
- [ ] Navigated to `C:\Users\HP\Desktop\Me\testtrack-pro\backend`
- [ ] Set PYTHONPATH: `$env:PYTHONPATH="$pwd"`
- [ ] Started backend: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
- [ ] Verified startup message: "Uvicorn running on http://0.0.0.0:8001"
- [ ] Verified no errors in console

### Verify OAuth Endpoints
- [ ] Tested GET /api/auth/oauth/google/authorize
- [ ] Tested GET /api/auth/oauth/github/authorize
- [ ] Both return authorization URLs

---

## Frontend Verification

### Check OAuth Buttons
- [ ] Went to http://localhost:3000/auth/login.html
- [ ] Saw "Google" button in OAuth section
- [ ] Saw "GitHub" button in OAuth section
- [ ] Buttons are clickable

### Browser Console
- [ ] Opened Developer Tools (F12)
- [ ] Went to Console tab
- [ ] No red errors about missing oauth.js
- [ ] No warnings about OAuth

---

## Testing

### Test Google OAuth
- [ ] Clicked "Google" button on login page
- [ ] Was redirected to Google login
- [ ] Logged in with Google account
- [ ] Approved permissions
- [ ] Was redirected back to /auth/oauth-callback
- [ ] Saw "Processing authentication..." message
- [ ] Was redirected to dashboard
- [ ] Successfully logged in with Google account

### Test GitHub OAuth
- [ ] Clicked "Logout" button
- [ ] Went back to http://localhost:3000/auth/login.html
- [ ] Clicked "GitHub" button
- [ ] Was redirected to GitHub login
- [ ] Logged in with GitHub account
- [ ] Authorized the application
- [ ] Was redirected back to /auth/oauth-callback
- [ ] Saw "Processing authentication..." message
- [ ] Was redirected to dashboard
- [ ] Successfully logged in with GitHub account

### Test Account Linking
- [ ] Logged out of TestTrack Pro
- [ ] Logged in with Google
- [ ] Verified user account was created
- [ ] Logged out
- [ ] Logged in with GitHub
- [ ] Verified it's a different account (or linked depending on implementation)

---

## Production Ready (Optional)

If deploying to production:
- [ ] Updated Google OAuth redirect URI to production domain
- [ ] Updated GitHub OAuth callback URL to production domain
- [ ] Updated .env `FRONTEND_URL` to production domain
- [ ] Updated .env `ALLOWED_ORIGINS` to production domain
- [ ] Set `ENV=production`
- [ ] Used strong `SECRET_KEY` (32+ random characters)
- [ ] Checked all credentials are correct for production

---

## Troubleshooting

If you encounter issues:
- [ ] Checked browser console (F12) for JavaScript errors
- [ ] Checked backend terminal for Python errors
- [ ] Verified redirect URIs match exactly in Google/GitHub settings
- [ ] Cleared browser cache (Ctrl+Shift+Delete)
- [ ] Hard refreshed page (Ctrl+F5)
- [ ] Restarted backend server
- [ ] Checked .env file for typos
- [ ] Verified localhost:3000 and localhost:8001 are accessible
- [ ] Tested in incognito/private mode

---

## Final Verification

- [ ] Email/password login still works
- [ ] Google OAuth login works
- [ ] GitHub OAuth login works
- [ ] All dashboard features work
- [ ] No error messages in browser console
- [ ] No error messages in backend logs
- [ ] Ready for production deployment

---

## Helpful Links

| Resource | URL |
|----------|-----|
| Quick Start | `OAUTH_QUICKSTART.md` |
| Full Guide | `OAUTH_SETUP_GUIDE.md` |
| Implementation | `OAUTH_COMPLETE.md` |
| Browser Guide | http://localhost:3000/oauth-setup.html |
| Login Page | http://localhost:3000/auth/login.html |
| Dashboard | http://localhost:3000/dashboard |
| API Docs | http://localhost:8001/docs |

---

## Notes Section

Use this space to note anything important:

```
Date completed: _____________________

Google Client ID: _____________________

GitHub Client ID: _____________________

Any issues encountered: _____________________

Notes: _____________________
```

---

## ✅ Completion Status

- [ ] All checkboxes completed?
- [ ] OAuth testing successful?
- [ ] Ready for production?

**If all checks are complete: You're all set! OAuth is ready to use!** 🎉

---

**Questions?** Check:
1. OAUTH_QUICKSTART.md - Quick reference
2. OAUTH_SETUP_GUIDE.md - Detailed guide
3. Browser console (F12) - For errors
4. Backend logs - For Python errors
5. http://localhost:3000/oauth-setup.html - Interactive guide

Good luck! 🚀
