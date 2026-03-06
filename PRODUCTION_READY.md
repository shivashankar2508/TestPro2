# TestTrack Pro - Production Ready Deployment Guide

**Last Updated:** March 6, 2026  
**Status:** ✓ Production Ready Recommendations (Local Development Verified)  
**Version:** 1.0.0

---

## Executive Summary

TestTrack Pro has been enhanced with production-grade security, error handling, and best practices. The application is ready for:
- **Local Development**: Fully functional with hot reload
- **Staging/Production Deployment**: Follow the guide below
- **Docker Containerization**: Configurations ready

### System Status
| Component | Status | Port | Health |
|-----------|--------|------|--------|
| Backend (FastAPI) | ✓ Running | 8001 | Healthy |
| Frontend (Webpack) | ✓ Running | 3000 | Healthy |
| Database (PostgreSQL) | ✓ Configured | - | Ready |
| Security Headers | ✓ Enabled | - | Configured |
| HTTPS/TLS | ⚠ Recommended | - | For Production |
| API Documentation | ✓ Available | /docs | Dev Only |

---

## What's Been Improved

### Security Enhancements

#### 1. Security Headers Added
```
✓ X-Content-Type-Options: nosniff
✓ X-Frame-Options: DENY
✓ X-XSS-Protection: 1; mode=block
✓ Strict-Transport-Security: max-age=31536000
✓ Content-Security-Policy: Configured
✓ Referrer-Policy: strict-origin-when-cross-origin
```

#### 2. Request Validation  
- All endpoints validate input using Pydantic schemas
- Bcrypt with 12 rounds for password hashing
- JWT tokens with 15-minute access token expiration
- Refresh token rotation (7-day expiration)

#### 3. Access Control
- Role-based access control (RBAC): admin, developer, tester
- Middleware protection on sensitive routes
- Environment-based API documentation visibility

#### 4. CORS Configuration  
- Whitelisted origins configured
- Credentials handling properly set
- Preflight requests handled correctly

### Code Quality Improvements

#### 1. Removed Debug Code
- ✓ Removed all `console.log` statements from frontend
- ✓ Removed debug print statements from backend
- ✓ Production-grade logging configuration added

#### 2. Configuration Management
- ✓ Environment variables properly validated
- ✓ Production warnings for weak secrets
- ✓ Database pool sizing configured
- ✓ Log levels configurable per environment

#### 3. Frontend Build Optimization
- ✓ Content hash in output filenames
- ✓ Code splitting for vendor/common chunks
- ✓ Terser minification with console.log removal
- ✓ Source maps disabled in production

---

## Deployment Instructions

### Prerequisites

```bash
# System Requirements
- Python 3.10+
- Node.js 16+
- PostgreSQL 12+
- 2GB RAM minimum
- 10GB disk space

# Verify installations
python --version  # 3.10+
node --version    # v16+
psql --version    # PostgreSQL 12+
```

### 1. Environment Setup

#### Backend Environment (`backend/.env`)

```bash
# Copy template and edit
cp backend/.env backend/.env.production

# Edit with production values:
cat backend/.env.production
```

**Critical Production Settings:**

```env
# Environment Mode
ENV=production                    # NOT development!
LOG_LEVEL=INFO                   # Use WARNING in strict production

# Database (Use PostgreSQL, NOT SQLite!)
DATABASE_URL=postgresql://user:password@host:5432/testtrack_prod
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600

# Security - MUST CHANGE
SECRET_KEY=<generate-32-char-random-string>
# Generate with: python -c "import os; print(os.urandom(24).hex())"

# CORS - Set to your domain
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Email (Production)
SMTP_SERVER=<your-smtp-server>
SMTP_PORT=587
SENDER_EMAIL=<production-email>
SENDER_PASSWORD=<app-password>

# Frontend URL
FRONTEND_URL=https://yourdomain.com
```

#### Frontend Environment (```frontend/.env`)

```env
REACT_APP_API_URL=https://api.yourdomain.com
NODE_ENV=production
```

### 2. Database Setup

```bash
# Connect to PostgreSQL
psql --host=prod-db-host --user=postgres

# Create database and user
CREATE DATABASE testtrack_prod;
CREATE USER testtrack WITH ENCRYPTED PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE testtrack_prod TO testtrack;

# Exit psql
\q

# Run migrations
cd backend
python -m alembic upgrade head
```

### 3. Backend Deployment

#### Option A: Using Gunicorn (Recommended for Production)

```bash
cd backend

# Install production ASGI server
pip install gunicorn

# Start with Gunicorn
gunicorn -w 4 \
  -b 0.0.0.0:8001 \
  --access-logfile - \
  --error-logfile - \
  --timeout 300 \
  --keep-alive 5 \
  app.main:app
```

**Configuration for High Traffic:**

```bash
gunicorn -w 8 \             # 2x CPU cores
  -b 0.0.0.0:8001 \
  --worker-class uvicorn.workers.UvicornWorker \
  --max-requests 10000 \
  --max-requests-jitter 1000 \
  --timeout 120 \
  --keep-alive 10 \
  --access-logfile /var/log/testtrack/access.log \
  --error-logfile /var/log/testtrack/error.log \
  app.main:app
```

#### Option B: Using Systemd Service

Create `/etc/systemd/system/testtrack-backend.service`:

```ini
[Unit]
Description=TestTrack Pro Backend
After=network.target postgresql.service

[Service]
Type=notify
User=testtrack
WorkingDirectory=/opt/testtrack/backend

ExecStart=/opt/testtrack/venv/bin/gunicorn \
  -w 4 \
  -b 0.0.0.0:8001 \
  --worker-class uvicorn.workers.UvicornWorker \
  app.main:app

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable testtrack-backend.service
sudo systemctl start testtrack-backend.service
sudo systemctl status testtrack-backend.service
```

### 4. Frontend Deployment

#### Build for Production

```bash
cd frontend

# Install dependencies
npm install

# Build optimized bundle
NODE_ENV=production npm run build

# Output in: frontend/dist/
```

#### Option A: Nginx Reverse Proxy

Create `/etc/nginx/sites-available/testtrack`:

```nginx
upstream backend {
    server 127.0.0.1:8001;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Max upload size
    client_max_body_size 100M;

    # API proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Frontend static files
    location / {
        root /var/www/testtrack/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    #  Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        root /var/www/testtrack/frontend/dist;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/testtrack /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Option B: Docker Deployment (Included)

See `docker-compose.yml` for quickstart:

```bash
# Edit .env.production for your settings
cp .env backend/.env.production

# Build and run
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale api=3
```

### 5. SSL/TLS Setup

#### Using Let's Encrypt (Free)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d yourdomain.com -d api.yourdomain.com

# Auto-renew (automatic with Let's Encrypt)
sudo systemctl enable certbot.timer
```

#### Manual Certificate

Place certificates in `/etc/testtrack/certs/`:
- `server.crt` - Certificate
- `server.key` - Private key

---

## Monitoring & Logging

### Backend Logs

```bash
# View real-time logs
tail -f /var/log/testtrack/access.log

# Search for errors
grep ERROR /var/log/testtrack/error.log

# Monitor with journalctl (if using systemd)
journalctl -u testtrack-backend.service -f
```

### Health Check

```bash
# API health with auth
curl -X POST http://localhost:8001/api/system/health-check \
  -H "Authorization: Bearer <token>"

# Response should be 200:
{
  "status": "healthy",
  "database": "connected",
  "checks": {
    "database": "ok",
    "storage": "ok",
    "configuration": "ok"
  }
}
```

### Performance Metrics

```bash
# Monitor with htop
htop

# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Database size
psql -c "SELECT pg_size_pretty(pg_database_size('testtrack_prod'));"
```

---

## Database Backups

### Automated Backup Script

Create `/opt/testtrack/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/testtrack"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="testtrack_prod"

# Create backup
pg_dump $DB_NAME | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/backup_$DATE.sql.gz" s3://your-bucket/backups/
```

### Restore from Backup

```bash
# Decompress and restore
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | psql testtrack_prod
```

### Backup Schedule (Cron)

```bash
# Add to crontab -e
0 2 * * */3 /opt/testtrack/backup.sh  # Every 3 days at 2 AM
```

---

## Security Checklist

- [ ] ✓ SECRET_KEY changed to 32+ character random string
- [ ] ✓ Database user has password set
- [ ] ✓ Database accessible only from app server (firewall rules)
- [ ] ✓ SSL/TLS certificate installed
- [ ] ✓ ALLOWED_ORIGINS set to your domain(s) only
- [ ] ✓ Email credentials use app-specific passwords (not main password)
- [ ] ✓ Firewall blocks unnecessary ports (only 80, 443, 22)
- [ ] ✓ Regular backups configured and tested
- [ ] ✓ Log rotation configured
- [ ] ✓ Fail2ban installed for brute-force protection
- [ ] ✓ SSH key-based authentication enabled
- [ ] ✓ API rate limiting tested
- [ ] ✓ HTTPS redirect enforced
- [ ] ✓ Security headers verified in browser

---

## Troubleshooting

### Backend Won't Start

```bash
# Check Python environment
python --version

# Verify dependencies
pip check

# Test database connection
python -c "from app.database import engine; engine.connect()"

# Check port availability
lsof -i :8001

# Clear cache
find . -type d -name __pycache__ -exec rm -r {} +
```

### Performance Issues

```bash
# Increase database pool size
DB_POOL_SIZE=50 gunicorn ...

# Increase worker processes
gunicorn -w 16 ...  # 4x CPU cores for I/O bound

# Check slow queries
tail -f /var/log/postgresql/postgresql.log | grep "duration"
```

### Memory Leaks

```bash
# Monitor with memory profiler
pip install memory-profiler
python -m memory_profiler app.py

# Restart service if needed
sudo systemctl restart testtrack-backend.service
```

---

## Performance Recommendations

| Metric | Development | Production |
|--------|-------------|-----------|
| Workers | 1 | 4-8x CPU cores |
| Connection Pool | 5 | 20-50 |
| Max Connections | 10 | 100+ |
| Cache TTL | 0 | 3600s |
| Log Level | DEBUG  | INFO/WARNING |
| Timeout | 60s | 300s (tunable) |
| Rate Limit | None | 100 req/min |

---

## Upcoming Enhancements

- [ ] Redis caching layer
- [ ] CDN for static assets
- [ ] Kubernetes deployment
- [ ] Advanced analytics dashboard
- [ ] Real-time test execution updates
- [ ] OAuth2 GitHub/Google integration
- [ ] Two-factor authentication
- [ ] Audit log export
- [ ] Performance profiling
- [ ] Load testing tools

---

## Support & Issues

For issues or questions:
- Check logs: `/var/log/testtrack/`
- Database health: `psql -d testtrack_prod -c "SELECT 1"`
- API status: `curl http://localhost:8001/api/health`
- Documentation: `/docs` (dev mode only)

---

## Version History

- **1.0.0** (March 6, 2026)
  - Initial production-ready release
  - Security headers configured
  - Environment validation added
  - Debug code removed
  - Frontend optimization completed
  - Documentation completed
