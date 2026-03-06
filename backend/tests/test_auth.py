import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database import Base, get_db

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ============ Test Registration ============
def test_user_registration_success():
    """Test successful user registration"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "john.tester@company.com",
            "username": "johntester",
            "full_name": "John Tester",
            "password": "SecurePass@123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "john.tester@company.com"
    assert data["username"] == "johntester"
    assert data["role"] == "tester"

def test_user_registration_weak_password():
    """Test registration with weak password"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "weak@company.com",
            "username": "weakuser",
            "full_name": "Weak User",
            "password": "weak"
        }
    )
    assert response.status_code == 400
    assert "Password must be at least 8 characters" in response.json()["detail"]

def test_user_registration_duplicate_email():
    """Test registration with duplicate email"""
    # First registration
    client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@company.com",
            "username": "user1",
            "full_name": "User One",
            "password": "SecurePass@123"
        }
    )
    
    # Second registration with same email
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@company.com",
            "username": "user2",
            "full_name": "User Two",
            "password": "SecurePass@123"
        }
    )
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]

# ============ Test Login ============
def test_user_login_unverified_email():
    """Test login with unverified email"""
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "email": "unverified@company.com",
            "username": "unverified",
            "full_name": "Unverified User",
            "password": "SecurePass@123"
        }
    )
    
    # Attempt login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "unverified@company.com",
            "password": "SecurePass@123",
            "remember_me": False
        }
    )
    assert response.status_code == 403
    assert "Email not verified" in response.json()["detail"]

def test_user_login_invalid_credentials():
    """Test login with invalid password"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@company.com",
            "password": "WrongPassword@123",
            "remember_me": False
        }
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

# ============ Test Password Strength ============
def test_password_no_uppercase():
    """Test password without uppercase letter"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "noupper@company.com",
            "username": "noupper",
            "full_name": "No Upper User",
            "password": "securepass@123"
        }
    )
    assert response.status_code == 400
    assert "uppercase" in response.json()["detail"]

def test_password_no_number():
    """Test password without number"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "nonum@company.com",
            "username": "nonum",
            "full_name": "No Num User",
            "password": "SecurePass@"
        }
    )
    assert response.status_code == 400
    assert "number" in response.json()["detail"]

def test_password_no_special_character():
    """Test password without special character"""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "noadmin@company.com",
            "username": "nospecial",
            "full_name": "No Special User",
            "password": "SecurePass123"
        }
    )
    assert response.status_code == 400
    assert "special character" in response.json()["detail"]

# ============ Health Check ============
def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "TestTrack Pro API"

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
