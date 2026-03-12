from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
import os
from pathlib import Path
from app.config import settings
from app.api.routes import auth, oauth, users, test_cases, test_suites, projects, system, backups, permissions, debug, bugs
from app.database import Base, engine
from app.models.user import User  # Import models to ensure they're registered
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

# Create FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-ready API for TestTrack Pro",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENV == "development" else None,
    redoc_url="/redoc" if settings.ENV == "development" else None,
    openapi_url="/openapi.json" if settings.ENV == "development" else None
)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.testtrack.com"]
)

# Create all database tables on startup
@app.on_event("startup")
def startup_event():
    """Create database tables on application startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Database tables created/verified")
    except Exception as e:
        logger.error(f"[ERROR] Failed to create database tables: {str(e)}")
        raise

# Configure CORS
cors_origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Number", "X-Page-Size"],
    max_age=600
)

# Include routers
app.include_router(auth.router)
app.include_router(debug.router)
app.include_router(oauth.router)
app.include_router(users.router)
app.include_router(test_cases.router)
app.include_router(test_suites.router)
app.include_router(projects.router)
app.include_router(system.router)
app.include_router(backups.router)
app.include_router(permissions.router)
app.include_router(bugs.router)

# Mount static files from frontend
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "public"
logger.info(f"[STATIC] frontend_dir={frontend_dir}, exists={frontend_dir.exists()}")
if frontend_dir.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi import HTTPException as _HTTPException

    styles_dir = frontend_dir / "styles"
    js_dir = frontend_dir / "js"
    auth_dir = frontend_dir / "auth"
    logger.info(f"[STATIC] styles_dir exists={styles_dir.exists()}, js_dir exists={js_dir.exists()}")

    # Mount the full public dir under /static (fallback)
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    # Explicit handlers for /styles/* and /js/* — more reliable than StaticFiles mount on Windows
    @app.get("/styles/{filepath:path}")
    async def serve_styles(filepath: str):
        file_path = styles_dir / filepath
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        raise _HTTPException(status_code=404)

    @app.get("/js/{filepath:path}")
    async def serve_js(filepath: str):
        file_path = js_dir / filepath
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        raise _HTTPException(status_code=404)

    # Mount auth directory for auth pages
    if auth_dir.exists():
        @app.get("/auth/{filename}")
        async def auth_files(filename: str):
            file_path = auth_dir / filename
            if file_path.exists() and file_path.suffix in [".html", ".css", ".js"]:
                return FileResponse(str(file_path))
            return {"error": "File not found"}
    
    # Serve HTML files with clean URLs
    @app.get("/")
    async def home():
        return FileResponse(str(frontend_dir / "landing.html"))
    
    @app.get("/login")
    async def login_page():
        return FileResponse(str(auth_dir / "login.html"))
    
    @app.get("/register")
    async def register_page():
        return FileResponse(str(auth_dir / "register.html"))
    
    @app.get("/dashboard")
    async def dashboard_page():
        return FileResponse(str(frontend_dir / "dashboard.html"))

    @app.get("/suite-management")
    async def suite_management_page():
        return FileResponse(str(frontend_dir / "suite-management.html"))

    @app.get("/suite-management.html")
    async def suite_management_page_html():
        return FileResponse(str(frontend_dir / "suite-management.html"))
    
    @app.get("/admin")
    async def admin_page():
        return FileResponse(str(frontend_dir / "admin.html"))
    
    @app.get("/index.html")
    async def index():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        # Return empty icon response to prevent noisy 404s in browser console.
        return Response(status_code=204)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TestTrack Pro API",
        "version": settings.APP_VERSION,
        "environment": settings.ENV
    }

@app.get("/api/debug-routes")
async def debug_routes():
    routes_info = []
    for route in app.routes:
        route_info = {"type": type(route).__name__}
        if hasattr(route, "path"):
            route_info["path"] = route.path
        elif hasattr(route, "url_path"):
            route_info["path"] = str(route.url_path)
        routes_info.append(route_info)
    return {"routes": routes_info}

@app.get("/api")
async def root():
    return {
        "message": "Welcome to TestTrack Pro API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENV == "development"
    )
