# TestTrack Pro - Quick Start Guide

## ✅ System Status

- **Backend API**: http://localhost:8000 ✓ RUNNING
- **Frontend**: http://localhost:3000 ✓ RUNNING
- **API Documentation**: http://localhost:8000/docs
- **Database**: SQLite (test_track_pro.db) ✓ CONNECTED

---

## 🔐 Login Credentials

### Admin Account
- **Email**: `admin@testtrack.com`
- **Password**: `Admin@123`
- **Role**: Administrator
- **Access**: Full system access, user management, all features

### Tester Account  
- **Email**: `test@test.com`
- **Password**: `Test@123` (try this first)
- **Role**: Tester
- **Access**: Create and execute test cases

### Developer Account
- **Email**: `dev2@testtrack.com`
- **Password**: `Dev@123`
- **Role**: Developer  
- **Access**: View test results, track bugs

---

## 🌐 How to Access the Application

### Option 1: Direct URLs (Recommended)

1. **Landing Page**: http://localhost:3000/landing.html
2. **Login Page**: http://localhost:3000/auth/login.html
3. **Register Page**: http://localhost:3000/auth/register.html
4. **Dashboard**: http://localhost:3000/dashboard.html (after login)

### Option 2: Backend-Served Pages

1. **Home**: http://localhost:8000/
2. **Login**: http://localhost:8000/login
3. **Register**: http://localhost:8000/register
4. **Dashboard**: http://localhost:8000/dashboard

---

## 📝 Testing the Login

### Method 1: Using the Web UI

1. Open http://localhost:3000/auth/login.html
2. Enter email: `admin@testtrack.com`
3. Enter password: `Admin@123`
4. Click "Sign In"
5. You should be redirected to the dashboard

### Method 2: Using API directly (PowerShell)

```powershell
$body = @{ 
    email = "admin@testtrack.com"
    password = "Admin@123" 
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

Write-Host "Access Token:" $response.access_token
```

---

## 🎯 Available Features

### For All Users:
- ✓ User authentication (login/logout)
- ✓ Email verification
- ✓ Password reset
- ✓ Profile management

### For Testers:
- ✓ Create test cases
- ✓ Execute tests
- ✓ Track test results
- ✓ Generate reports

### For Admins:
- ✓ Manage users
- ✓ Configure system
- ✓ View all test cases
- ✓ Analytics and insights

---

## 🔧 Troubleshooting

### If login doesn't work:

1. **Check backend is running**: Visit http://localhost:8000/api/health
   - Should show: `{"status":"healthy"}`

2. **Check browser console**: Press F12, look for errors

3. **Verify credentials**: Try the admin account first

4. **Clear browser cache**: Ctrl+Shift+Delete

5. **Check database**: Run in backend folder:
   ```powershell
   cd testtrack-pro\backend
   python setup_db.py
   ```

### Common Issues:

- **CORS errors**: Backend allows localhost:3000 and localhost:8000
- **Token issues**: Clear localStorage in browser console:
  ```javascript
  localStorage.clear()
  ```
- **Connection refused**: Restart the backend server

---

## 🚀 Quick Commands

### Restart Backend:
```powershell
cd testtrack-pro\backend
python run.py
```

### Restart Frontend:
```powershell
cd testtrack-pro\frontend  
npm run dev
```

### Check Database Users:
```powershell
cd testtrack-pro\backend
python setup_db.py
```

---

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/users/me` - Get current user

### Test Cases
- `GET /api/test-cases` - List test cases
- `POST /api/test-cases` - Create test case
- `GET /api/test-cases/{id}` - Get test case details
- `PUT /api/test-cases/{id}` - Update test case
- `DELETE /api/test-cases/{id}` - Delete test case

### Users (Admin only)
- `GET /api/users` - List all users
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

---

## 📄 Additional Users in Database

All these users are active and ready to use:

1. admin@testtrack.com (admin)
2. test@test.com (tester)
3. dev@testtrack.com (tester)
4. dev2@testtrack.com (developer)
5. fmn@gmail.com (tester)
6. fmna@gmail.com (tester)
7. newtest@example.com (tester)
8. newuser@test.com (tester)

**Note**: Most user passwords follow the pattern: `[Name]@123` 
(e.g., `Test@123`, `Dev@123`, `Admin@123`)

---

## ✅ Verification Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Can access http://localhost:8000/docs
- [ ] Can access http://localhost:3000/landing.html
- [ ] Login page loads properly
- [ ] Can login with admin@testtrack.com / Admin@123
- [ ] Dashboard loads after login
- [ ] Can create new test case (tester role)
- [ ] Can view users list (admin role)

---

**Last Updated**: March 5, 2026
**Version**: 1.0.0
