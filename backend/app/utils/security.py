from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import os
import secrets
import string

load_dotenv()

# ============ Password Hashing ============
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

# ============ JWT Configuration ============
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# ============ JWT Token Functions ============
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_token_expiry_time(token: str) -> Optional[datetime]:
    """Get the expiry time from a token"""
    payload = decode_token(token)
    if payload and "exp" in payload:
        return datetime.utcfromtimestamp(payload["exp"])
    return None

# ============ Token Verification Functions ============
def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """Verify that token is of expected type"""
    return payload.get("type") == expected_type

def generate_verification_token() -> str:
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)

def generate_reset_token() -> str:
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)

# ============ Password Management ============
def is_password_strong(password: str) -> tuple[bool, list]:
    """
    Validate password strength
    Returns: (is_valid, errors)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors

# ============ Account Lockout ============
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def is_account_locked(user) -> bool:
    """Check if account is locked due to failed login attempts"""
    if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        if user.locked_until and datetime.utcnow() < user.locked_until:
            return True
    return False

def get_lockout_remaining_time(user) -> Optional[int]:
    """Get remaining lockout time in seconds"""
    if user.locked_until and datetime.utcnow() < user.locked_until:
        remaining = (user.locked_until - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))
    return None

def calculate_lockout_until() -> datetime:
    """Calculate lockout expiry time"""
    return datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

# ============ Random String Generation ============
def generate_random_username(base: str = "user") -> str:
    """Generate a random username"""
    random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return f"{base}_{random_suffix}"
