import pytest
from backend.app.utils.security import (
    hash_password, verify_password, is_password_strong,
    create_access_token, create_refresh_token, decode_token,
    verify_token_type, generate_verification_token
)

# ============ Password Hashing Tests ============
def test_password_hashing():
    """Test password hashing and verification"""
    password = "SecurePass@123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPass@123", hashed)

# ============ Password Strength Tests ============
def test_password_strength_valid():
    """Test valid password strength"""
    password = "SecurePass@123"
    is_strong, errors = is_password_strong(password)
    
    assert is_strong
    assert len(errors) == 0

def test_password_strength_too_short():
    """Test password too short"""
    password = "Short@1"
    is_strong, errors = is_password_strong(password)
    
    assert not is_strong
    assert len(errors) > 0
    assert any("8 characters" in error for error in errors)

def test_password_strength_no_uppercase():
    """Test password without uppercase"""
    password = "securepass@123"
    is_strong, errors = is_password_strong(password)
    
    assert not is_strong
    assert any("uppercase" in error for error in errors)

def test_password_strength_no_lowercase():
    """Test password without lowercase"""
    password = "SECUREPASS@123"
    is_strong, errors = is_password_strong(password)
    
    assert not is_strong
    assert any("lowercase" in error for error in errors)

def test_password_strength_no_number():
    """Test password without number"""
    password = "SecurePass@"
    is_strong, errors = is_password_strong(password)
    
    assert not is_strong
    assert any("number" in error for error in errors)

def test_password_strength_no_special_char():
    """Test password without special character"""
    password = "SecurePass123"
    is_strong, errors = is_password_strong(password)
    
    assert not is_strong
    assert any("special character" in error for error in errors)

# ============ JWT Token Tests ============
def test_create_access_token():
    """Test access token creation"""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)
    
    assert token is not None
    payload = decode_token(token)
    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"

def test_create_refresh_token():
    """Test refresh token creation"""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_refresh_token(data)
    
    assert token is not None
    payload = decode_token(token)
    assert payload["sub"] == "123"
    assert payload["type"] == "refresh"

def test_decode_invalid_token():
    """Test decoding invalid token"""
    token = "invalid.token.here"
    payload = decode_token(token)
    
    assert payload is None

def test_verify_token_type():
    """Test token type verification"""
    access_token = create_access_token({"sub": "123"})
    refresh_token = create_refresh_token({"sub": "123"})
    
    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)
    
    assert verify_token_type(access_payload, "access")
    assert not verify_token_type(access_payload, "refresh")
    assert verify_token_type(refresh_payload, "refresh")
    assert not verify_token_type(refresh_payload, "access")

# ============ Token Generation Tests ============
def test_verification_token_generation():
    """Test verification token generation"""
    token1 = generate_verification_token()
    token2 = generate_verification_token()
    
    assert token1 is not None
    assert token2 is not None
    assert token1 != token2
    assert len(token1) > 20
