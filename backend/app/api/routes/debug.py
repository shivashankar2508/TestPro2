from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["Debug"])

@router.get("/echo")
async def debug_echo(request: Request):
    """Super simple endpoint - just returns what it received"""
    headers_dict = dict(request.headers)
    
    auth = headers_dict.get("authorization", "MISSING")
    logger.info(f"[ECHO] Authorization header received: {auth[:50]}..." if auth != "MISSING" else f"[ECHO] Authorization header: {auth}")
    
    return {
        "success": True,
        "timestamp": str(__import__('datetime').datetime.now()),
        "method": request.method,
        "path": request.url.path,
        "authorization": auth,
        "has_bearer": auth.startswith("Bearer ") if auth != "MISSING" else False,
        "all_headers": headers_dict
    }

@router.post("/echo")
async def debug_echo_post(request: Request):
    """Echo for POST requests"""
    headers_dict = dict(request.headers)
    auth = headers_dict.get("authorization", "MISSING")
    logger.info(f"[ECHO-POST] Authorization header: {auth[:50] if auth != 'MISSING' else auth}...")
    
    return {
        "success": True,
        "timestamp": str(__import__('datetime').datetime.now()),
        "method": request.method,
        "authorization": auth,
        "all_headers": headers_dict
    }

@router.get("/request-info")
async def debug_request_info(request: Request):
    """Log and return details about the incoming request"""
    headers_dict = dict(request.headers)
    
    debug_info = {
        "method": request.method,
        "url": str(request.url),
        "client": request.client,
        "headers": {
            "authorization": headers_dict.get("authorization", "MISSING"),
            "origin": headers_dict.get("origin", "MISSING"),
            "content-type": headers_dict.get("content-type", "MISSING"),
            "user-agent": headers_dict.get("user-agent", "MISSING")
        }
    }
    
    logger.info(f"[DEBUG] Request info: {debug_info}")
    return debug_info

@router.get("/users-me-test")
async def test_users_me(request: Request, db: Session = Depends(get_db)):
    """Test endpoint that mimics /users/me but with more logging"""
    # Check Authorization header
    auth_header = request.headers.get("authorization")
    logger.info(f"[TEST] /users/me-test - Authorization header: {auth_header}")
    
    if not auth_header:
        logger.error("[TEST] /users/me-test - NO Authorization header found!")
        return {
            "error": "NO Authorization header",
            "received_headers": dict(request.headers)
        }
    
    if not auth_header.startswith("Bearer "):
        logger.error(f"[TEST] /users/me-test - Invalid Bearer format: {auth_header[:50]}")
        return {
            "error": "Invalid Bearer format",
            "auth_header": auth_header[:50] + "..."
        }
    
    token = auth_header.split(" ")[1]
    logger.info(f"[TEST] /users/me-test - Token length: {len(token)}")
    
    # Now try to authenticate
    from app.utils.auth_middleware import get_current_user
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    try:
        current_user = await get_current_user(credentials, db)
        logger.info(f"[TEST] /users/me-test -SUCCESS: User {current_user.email}")
        return {
            "success": True,
            "user": {
                "email": current_user.email,
                "id": current_user.id,
                "role": current_user.role
            }
        }
    except Exception as e:
        logger.error(f"[TEST] /users/me-test - ERROR: {str(e)}")
        return {
            "error": str(e),
            "token_length": len(token)
        }
