# 🔐 Google & GitHub OAuth Quick Start

Google and GitHub OAuth login is **already built-in** to TestTrack Pro! Follow these simple steps to enable it.

---

## ⚡ Quick Start (5 minutes)

### **Option 1: Automated Setup (RECOMMENDED)**

```powershell
cd C:\Users\HP\Desktop\Me\testtrack-pro
python setup_oauth.py
```

The script will guide you through the entire process! ✨

---

### **Option 2: Manual Setup**

#### **Step 1: Get Google Credentials**
- Go to: https://console.cloud.google.com/
- Create new project: "TestTrack Pro"
- Enable "Google+ API"
- Create OAuth 2.0 Client ID (Web application)
- Add Redirect URI: `http://localhost:3000/auth/oauth-callback`
- Save Client ID and Secret

#### **Step 2: Get GitHub Credentials**
- Go to: https://github.com/settings/developers
- Click "OAuth Apps" → "New OAuth App"
- Fill in form:
  - Name: **TestTrack Pro**
  - Homepage: **http://localhost:3000**
  - Callback: **http://localhost:3000/auth/oauth-callback**
- Save Client ID and Secret

#### **Step 3: Update .env**

Create `backend/.env` file with:
```bash
GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
```

#### **Step 4: Restart Backend**
```powershell
cd C:\Users\HP\Desktop\Me\testtrack-pro\backend
$env:PYTHONPATH="$pwd"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 🚀 Test It

1. Open http://localhost:3000/auth/login.html
2. Click **"Google"** or **"GitHub"** button
3. Login with your account
4. Automatically redirected to dashboard ✅

---

## 🎯 What Works

✅ Google OAuth login  
✅ GitHub OAuth login  
✅ Auto-create account on first login  
✅ Auto-link OAuth to existing accounts  
✅ CSRF protection  
✅ Secure token handling  

---

## ⚠️ Common Issues

| Problem | Solution |
|---------|----------|
| "Redirect URI mismatch" | Ensure callback URL matches exactly in Google/GitHub settings |
| OAuth buttons don't appear | Clear browser cache, restart backend |
| "Invalid credentials" | Verify Client ID/Secret in .env file |
| Stuck on login page | Check browser console (F12) for errors |

---

## 📚 Full Documentation

See **OAUTH_SETUP_GUIDE.md** for detailed information.

---

## 🔍 API Endpoints

```
GET  /api/auth/oauth/google/authorize
GET  /api/auth/oauth/github/authorize
POST /api/auth/oauth/google/callback
POST /api/auth/oauth/github/callback
```

---

That's it! OAuth is now enabled! 🎉

For detailed setup: See [OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md)
