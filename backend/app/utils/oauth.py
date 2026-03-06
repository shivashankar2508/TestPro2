import httpx
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import os
from app.utils.security import create_access_token, create_refresh_token

load_dotenv()

# ============ OAuth Configuration ============

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ============ OAuth State Management ============

class OAuthStateManager:
    """Manage OAuth state tokens to prevent CSRF attacks"""
    
    _states: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_state(cls, provider: str, redirect_uri: str) -> str:
        """Generate and store a state token"""
        state = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(minutes=10)
        
        cls._states[state] = {
            "provider": provider,
            "redirect_uri": redirect_uri,
            "created_at": datetime.utcnow(),
            "expires_at": expiry
        }
        
        # Cleanup old states
        cls._cleanup_expired_states()
        
        return state
    
    @classmethod
    def validate_state(cls, state: str, provider: str) -> bool:
        """Validate a state token"""
        if state not in cls._states:
            return False
        
        state_data = cls._states[state]
        
        if state_data["provider"] != provider:
            return False
        
        if datetime.utcnow() > state_data["expires_at"]:
            del cls._states[state]
            return False
        
        return True
    
    @classmethod
    def get_redirect_uri(cls, state: str) -> Optional[str]:
        """Get the redirect URI for a state token"""
        if state in cls._states:
            return cls._states[state]["redirect_uri"]
        return None
    
    @classmethod
    def cleanup_state(cls, state: str):
        """Remove a state token after use"""
        if state in cls._states:
            del cls._states[state]
    
    @classmethod
    def _cleanup_expired_states(cls):
        """Remove expired state tokens"""
        now = datetime.utcnow()
        expired = [s for s, d in cls._states.items() if now > d["expires_at"]]
        for state in expired:
            del cls._states[state]

# ============ Google OAuth ============

class GoogleOAuth:
    """Google OAuth Provider"""
    
    @staticmethod
    def get_authorization_url(redirect_uri: str) -> tuple[str, str]:
        """Generate Google authorization URL"""
        state = OAuthStateManager.create_state("google", redirect_uri)
        
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email profile openid",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{GOOGLE_AUTHORIZE_URL}?{query_string}"
        
        return auth_url, state
    
    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            return response.json()
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from Google"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()

# ============ GitHub OAuth ============

class GitHubOAuth:
    """GitHub OAuth Provider"""
    
    @staticmethod
    def get_authorization_url(redirect_uri: str) -> tuple[str, str]:
        """Generate GitHub authorization URL"""
        state = OAuthStateManager.create_state("github", redirect_uri)
        
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
            "allow_signup": "true"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{GITHUB_AUTHORIZE_URL}?{query_string}"
        
        return auth_url, state
    
    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                headers={"Accept": "application/json"}
            )
            return response.json()
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from GitHub"""
        async with httpx.AsyncClient() as client:
            # Get user profile
            response = await client.get(
                GITHUB_USERINFO_URL,
                headers={"Authorization": f"token {access_token}"}
            )
            user_data = response.json()
            
            # Get email (if needed)
            if not user_data.get("email"):
                response = await client.get(
                    f"{GITHUB_USERINFO_URL}/emails",
                    headers={"Authorization": f"token {access_token}"}
                )
                emails = response.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                if primary_email:
                    user_data["email"] = primary_email["email"]
            
            return user_data

# ============ OAuth User Data Extraction ============

class OAuthUserData:
    """Extract user data from OAuth providers"""
    
    @staticmethod
    def from_google(google_user: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user data from Google"""
        return {
            "provider": "google",
            "provider_id": google_user.get("id"),
            "email": google_user.get("email"),
            "name": google_user.get("name"),
            "avatar_url": google_user.get("picture")
        }
    
    @staticmethod
    def from_github(github_user: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user data from GitHub"""
        return {
            "provider": "github",
            "provider_id": str(github_user.get("id")),
            "email": github_user.get("email"),
            "name": github_user.get("name") or github_user.get("login"),
            "avatar_url": github_user.get("avatar_url")
        }
