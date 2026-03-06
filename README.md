# TestTrack Pro

A production-ready application for test tracking and monitoring with a modern tech stack.

## 🏗️ Architecture

**Frontend**: HTML/CSS/JavaScript with Webpack
**Backend**: FastAPI with PostgreSQL
**Dashboard**: Streamlit for analytics
**Database**: PostgreSQL (production-ready)
**Containerization**: Docker & Docker Compose

## 📋 Prerequisites

- Docker & Docker Compose (for containerized setup)
- Python 3.9+ (for local backend/dashboard)
- Node.js 18+ (for local frontend)
- PostgreSQL 12+ (for local database)

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Start all services
make run-all

# Or manually:
docker-compose up --build
```

Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501

### Option 2: Local Setup

```bash
# Install dependencies
make install

# Setup environment
make setup

# Terminal 1: Backend
make run-backend

# Terminal 2: Frontend
make run-frontend

# Terminal 3: Dashboard
make run-dashboard
```

## 📁 Project Structure

```
testtrack-pro/
├── frontend/           # Web frontend (HTML/CSS/JS + Webpack)
├── backend/            # FastAPI backend with PostgreSQL
├── dashboard/          # Streamlit analytics dashboard
├── docker/             # Docker configurations
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── tests/              # Integration tests
├── docker-compose.yml  # Docker Compose configuration
├── Makefile            # Build automation
└── README.md           # This file
```

## 🛠️ Available Commands

```bash
make help              # Show all available commands
make setup             # Initial setup
make install           # Install dependencies
make run-all           # Run all services with Docker
make stop              # Stop Docker services
make clean             # Clean build artifacts
make test              # Run tests
make lint              # Run linters
```

## 📊 API Documentation

Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest

# Run with coverage
pytest --cov=app
```

## 📦 Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `API_URL` - Backend API URL
- `ENV` - Environment (development/production)

## 🔒 Security

- Use strong database passwords in production
- Set `ENV=production` for production deployments
- Configure CORS properly with `ALLOWED_ORIGINS`
- Use HTTPS in production

## 📝 License

ISC

## 🔐 Authentication & OAuth

TestTrack Pro supports multiple authentication methods:

- **Email/Password** - Traditional login
- **Google OAuth** - Sign in with Google account
- **GitHub OAuth** - Sign in with GitHub account

To enable OAuth: See [OAUTH_QUICKSTART.md](OAUTH_QUICKSTART.md) or run `python setup_oauth.py`

For detailed setup: [OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md)

## 🤝 Contributing

Contributions are welcome! Please follow the project's coding standards.

## 📞 Support

For issues and questions, please open an issue on GitHub.
