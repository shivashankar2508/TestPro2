from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
import traceback
import logging
from app.exceptions import TestTrackException

# Setup logging
logger = logging.getLogger(__name__)

# ============ Error Response Models ============

async def test_track_exception_handler(request: Request, exc: TestTrackException):
    """Handle TestTrack custom exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_code": exc.error_code,
            "message": exc.message,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "error_code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

# ============ Register Exception Handlers ============

def register_exception_handlers(app: FastAPI):
    """Register all exception handlers with the app"""
    app.add_exception_handler(TestTrackException, test_track_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
