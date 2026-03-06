from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token, verify_token_type
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    logger.info(f"[get_current_user] Starting - credentials_type={type(credentials)}")
    
    if not credentials:
        logger.error("[get_current_user] No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No credentials provided",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    logger.info(f"[get_current_user] Token length: {len(token) if token else 0}")
    
    # Decode token
    payload = decode_token(token)
    logger.info(f"[get_current_user] Token decoded successfully, payload_keys: {list(payload.keys()) if payload else 'None'}")
    
    if not payload:
        logger.error("[get_current_user] Token decode failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token type
    is_valid_type = verify_token_type(payload, "access")
    logger.info(f"[get_current_user] Token type verify: {is_valid_type}, token_type={payload.get('type')}")
    
    if not is_valid_type:
        logger.error(f"[get_current_user] Invalid token type: {payload.get('type')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user
    user_id = payload.get("sub")
    logger.info(f"[get_current_user] User ID from token: {user_id}")
    
    if not user_id:
        logger.error("[get_current_user] No user ID in token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user_id = int(user_id)
    except ValueError:
        logger.error(f"[get_current_user] Invalid user ID format: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    logger.info(f"[get_current_user] Database query result: user_found={user is not None}, is_active={user.is_active if user else 'N/A'}")
    
    if not user or not user.is_active:
        logger.error(f"[get_current_user] User not found or inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.info(f"[get_current_user] SUCCESS: User {user.email} authenticated")
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security) if False else None,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    """
    if not credentials:
        return None
    
    return await get_current_user(credentials, db)

def require_role(*roles):
    """
    Dependency to require specific roles
    
    Usage:
    @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(current_user: User = Depends(get_current_user)):
        # Role is now a string (not Enum), compare directly
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return check_role

# Role-specific dependencies
def require_tester(current_user: User = Depends(get_current_user)):
    """Require tester role"""
    # Role is now a string (not Enum), compare directly
    if current_user.role not in ["tester", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only testers can access this resource"
        )
    return current_user

def require_developer(current_user: User = Depends(get_current_user)):
    """Require developer role"""
    # Role is now a string (not Enum), compare directly
    if current_user.role not in ["developer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can access this resource"
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role"""
    # Role is now a string (not Enum), compare directly
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access this resource"
        )
    return current_user
