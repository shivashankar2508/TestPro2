# TestTrack Pro - Backend API

Production-ready FastAPI backend with PostgreSQL database.

## Getting Started

### Prerequisites
- Python 3.9+
- PostgreSQL 12+

### Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Setup

```bash
# Copy .env file
cp .env.example .env

# Update .env with your database credentials
```

### Running

```bash
# Development
python app/main.py

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
pytest
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
