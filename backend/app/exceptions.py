from fastapi import HTTPException, status
from typing import Optional

# ============ Custom Exceptions ============

class TestTrackException(Exception):
    """Base exception for TestTrack Pro"""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

# ============ Authentication Exceptions ============

class AuthenticationError(TestTrackException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR", status.HTTP_401_UNAUTHORIZED)

class InvalidCredentialsError(TestTrackException):
    """Invalid email or password"""
    def __init__(self):
        super().__init__("Invalid email or password", "INVALID_CREDENTIALS", status.HTTP_401_UNAUTHORIZED)

class EmailNotVerifiedError(TestTrackException):
    """Email not verified"""
    def __init__(self):
        super().__init__(
            "Email not verified. Check your inbox for verification link.",
            "EMAIL_NOT_VERIFIED",
            status.HTTP_403_FORBIDDEN
        )

class AccountLockedError(TestTrackException):
    """Account locked due to failed attempts"""
    def __init__(self, remaining_minutes: int = 15):
        super().__init__(
            f"Account locked. Try again in {remaining_minutes} minutes.",
            "ACCOUNT_LOCKED",
            status.HTTP_429_TOO_MANY_REQUESTS
        )

class TokenExpiredError(TestTrackException):
    """Token has expired"""
    def __init__(self):
        super().__init__("Token has expired", "TOKEN_EXPIRED", status.HTTP_401_UNAUTHORIZED)

class InvalidTokenError(TestTrackException):
    """Invalid token"""
    def __init__(self):
        super().__init__("Invalid token", "INVALID_TOKEN", status.HTTP_401_UNAUTHORIZED)

# ============ User Exceptions ============

class UserNotFoundError(TestTrackException):
    """User not found"""
    def __init__(self):
        super().__init__("User not found", "USER_NOT_FOUND", status.HTTP_404_NOT_FOUND)

class UserAlreadyExistsError(TestTrackException):
    """User already exists"""
    def __init__(self, field: str = "email"):
        super().__init__(f"User with this {field} already exists", "USER_EXISTS", status.HTTP_409_CONFLICT)

class InvalidPasswordError(TestTrackException):
    """Invalid password"""
    def __init__(self, message: str = "Password does not meet requirements"):
        super().__init__(message, "INVALID_PASSWORD", status.HTTP_400_BAD_REQUEST)

class PasswordReuseError(TestTrackException):
    """Password reuse not allowed"""
    def __init__(self):
        super().__init__(
            "Cannot reuse one of your last 5 passwords",
            "PASSWORD_REUSE",
            status.HTTP_400_BAD_REQUEST
        )

# ============ Validation Exceptions ============

class ValidationError(TestTrackException):
    """Validation failed"""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "VALIDATION_ERROR", status.HTTP_400_BAD_REQUEST)

class InvalidEmailError(TestTrackException):
    """Invalid email format"""
    def __init__(self):
        super().__init__("Invalid email format", "INVALID_EMAIL", status.HTTP_400_BAD_REQUEST)

class InvalidUsernameError(TestTrackException):
    """Invalid username format"""
    def __init__(self):
        super().__init__(
            "Username must be 3-50 characters, alphanumeric and underscores only",
            "INVALID_USERNAME",
            status.HTTP_400_BAD_REQUEST
        )

# ============ Permission Exceptions ============

class PermissionDeniedError(TestTrackException):
    """Permission denied"""
    def __init__(self, message: str = "You don't have permission to access this resource"):
        super().__init__(message, "PERMISSION_DENIED", status.HTTP_403_FORBIDDEN)

class RoleRequiredError(TestTrackException):
    """Specific role required"""
    def __init__(self, role: str):
        super().__init__(
            f"This resource requires {role} role",
            "ROLE_REQUIRED",
            status.HTTP_403_FORBIDDEN
        )

# ============ Resource Exceptions ============

class ResourceNotFoundError(TestTrackException):
    """Resource not found"""
    def __init__(self, resource_type: str = "Resource"):
        super().__init__(f"{resource_type} not found", "RESOURCE_NOT_FOUND", status.HTTP_404_NOT_FOUND)

class ResourceAlreadyExistsError(TestTrackException):
    """Resource already exists"""
    def __init__(self, resource_type: str = "Resource"):
        super().__init__(
            f"{resource_type} already exists",
            "RESOURCE_EXISTS",
            status.HTTP_409_CONFLICT
        )

# ============ Business Logic Exceptions ============

class InvalidStatusTransitionError(TestTrackException):
    """Invalid status transition"""
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition from {current_status} to {target_status}",
            "INVALID_STATUS",
            status.HTTP_400_BAD_REQUEST
        )

class InvalidOperationError(TestTrackException):
    """Invalid operation"""
    def __init__(self, message: str = "This operation is not allowed"):
        super().__init__(message, "INVALID_OPERATION", status.HTTP_400_BAD_REQUEST)

class CannotDeleteError(TestTrackException):
    """Cannot delete resource"""
    def __init__(self, message: str = "Cannot delete this resource"):
        super().__init__(message, "CANNOT_DELETE", status.HTTP_400_BAD_REQUEST)

# ============ Email Exceptions ============

class EmailSendError(TestTrackException):
    """Failed to send email"""
    def __init__(self):
        super().__init__(
            "Failed to send email. Please try again later.",
            "EMAIL_SEND_FAILED",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ============ Rate Limiting Exceptions ============

class RateLimitExceededError(TestTrackException):
    """Rate limit exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Try again in {retry_after} seconds.",
            "RATE_LIMIT_EXCEEDED",
            status.HTTP_429_TOO_MANY_REQUESTS
        )

# ============ Database Exceptions ============

class DatabaseError(TestTrackException):
    """Database operation failed"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, "DATABASE_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============ Server Exceptions ============

class InternalServerError(TestTrackException):
    """Internal server error"""
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(message, "INTERNAL_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============ Helper Function ============

def raise_http_exception(exc: TestTrackException):
    """Convert TestTrackException to HTTPException"""
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "error_code": exc.error_code,
            "message": exc.message
        }
    )
