from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

# ============ Role Enums ============
class RoleEnum(str, Enum):
    TESTER = "tester"
    DEVELOPER = "developer"
    ADMIN = "admin"

# ============ User Schemas ============
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=255)

class UserRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=255)
    role: Optional[RoleEnum] = RoleEnum.TESTER
    
    @validator('password')
    def validate_password_strength(cls, v):
        """
        Validate password strength:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        - At least 1 special character
        """
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least 1 uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least 1 lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least 1 number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least 1 special character')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class UserChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=255)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least 1 uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least 1 lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least 1 number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least 1 special character')
        return v

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=255)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least 1 uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least 1 lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least 1 number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least 1 special character')
        return v

class UserResponse(UserBase):
    id: int
    role: RoleEnum
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserDetailResponse(UserResponse):
    is_active: bool
    status: str
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

# ============ Token Schemas ============
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # in seconds

class TokenRefresh(BaseModel):
    refresh_token: str

class VerifyEmail(BaseModel):
    token: str

# ============ OAuth Schemas ============
class GoogleOAuthCallback(BaseModel):
    code: str
    redirect_uri: str

class GitHubOAuthCallback(BaseModel):
    code: str
    redirect_uri: str

class OAuthResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: RoleEnum
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    
    class Config:
        from_attributes = True

# ============ Error Response ============
class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationErrorResponse(BaseModel):
    detail: list
    error_code: str = "VALIDATION_ERROR"
