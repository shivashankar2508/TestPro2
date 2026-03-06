# TestTrack Pro - Quick Start (Production)

## 5-Minute Production Setup

### 1. Clone and Setup

```bash
git clone <repo-url> testtrack-pro
cd testtrack-pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

### 2. Configure Environment

```bash
# Backend configuration
cd backend
cp .env.example .env

# IMPORTANT: Edit .env with production values
nano .env

# Required changes:
# - ENV=production
# - DATABASE_URL=postgresql://...
# - SECRET_KEY=<generate-new-key>
# - ALLOWED_ORIGINS=https://yourdomain.com
```

### 3. Setup Database

```bash
# Create PostgreSQL database
createdb testtrack_prod
createuser testtrack

# Run migrations
cd backend
python -m alembic upgrade head

# Verify
psql -d testtrack_prod -c "SELECT count(*) FROM users;"
```

### 4. Start Services

```bash
# Terminal 1: Backend
cd backend
gunicorn -w 4 -b 0.0.0.0:8001 app.main:app

# Terminal 2: Frontend
cd frontend
npm run build
npx serve -s dist -l 3000
```

### 5. Verify

```bash
# Check endpoints
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@testtrack.com","password":"Admin@123"}'

# Expected: 200 with { "access_token": "...", "refresh_token": "..." }

# Check frontend
curl http://localhost:3000/
# Expected: 200 with landing page HTML
```

### 6. Setup SSL (Recommended)

```bash
# Using Let's Encrypt
certbot certonly --standalone -d yourdomain.com

# Configure Nginx to serve with SSL
# See PRODUCTION_READY.md for full Nginx config
```

---

## Admin Credentials

**Default Admin Account:**
- **Email:** admin@testtrack.com
- **Password:** Admin@123

⚠️ **CHANGE ON FIRST LOGIN** - This is a development credential!

---

## Deployment Checklist

```
SECURITY
 [ ] Changed SECRET_KEY (32+ char random string)
 [ ] Set ENV=production
 [ ] Database has strong password
 [ ] ALLOWED_ORIGINS configured for your domain
 [ ] SSL/TLS certificate installed
 [ ] Firewall restricts unnecessary ports
 [ ] Database backups automated

CONFIGURATION
 [ ] .env file configured with production values
 [ ] SMTP credentials for email enabled
 [ ] FRONTEND_URL points to your domain
 [ ] LOG_LEVEL set appropriately
 [ ] Database connection pool sized for load

PERFORMANCE
 [ ] Gunicorn workers = 4-8x CPU cores
 [ ] Database pool size = 20-50
 [ ] Static assets cached
 [ ] CDN or cdn configured (optional)

MONITORING
 [ ] Health check endpoint accessible
 [ ] Logs configured and rotated
 [ ] Error monitoring enabled
 [ ] Performance metrics collected
 [ ] Uptime monitoring configured

TESTING
 [ ] Login flow tested end-to-end
 [ ] API authentication working
 [ ] Database queries load tested
 [ ] Frontend assets loading correctly
 [ ] SSL certificate valid
```

---

## Essential Commands

```bash
# View logs
tail -f /var/log/testtrack/error.log

# Check service status
systemctl status testtrack-backend

# View database size
psql -c "SELECT pg_size_pretty(pg_database_size('testtrack_prod'));"

# Create admin user
cd backend && python -c "from app.models.admin import create_admin; create_admin()"

# Test API
curl -I http://localhost:8001/api/health

# Generate new SECRET_KEY
python -c "import os; print('SECRET_KEY=' + os.urandom(24).hex())"
```

---

## Next Steps

1. **Monitor**: Set up application performance monitoring (APM)
2. **Backup**: Test restore procedures
3. **Users**: Create additional admin/developer/tester users
4. **Features**: Configure advanced settings in `/api/system/config`
5. **Documentation**: Review API docs at `/docs` (dev mode only)

---

**Deployment Date:** ________________  
**Environment:** [ ] Development [ ] Staging [ ] Production  
**Verified By:** ________________  
