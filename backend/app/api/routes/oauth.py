from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User, RoleEnum, UserStatusEnum, OAuthProvider, RefreshToken
from app.schemas.auth import OAuthResponse
from app.utils.oauth import (
    GoogleOAuth, GitHubOAuth, OAuthStateManager, OAuthUserData
)
from app.utils.security import create_access_token, create_refresh_token, hash_password
from app.utils.email_service import EmailService
from app.utils.auth_middleware import get_current_user
import uuid

router = APIRouter(prefix="/api/auth/oauth", tags=["OAuth"])

# ============ OAuth Authorization URLs ============

@router.get("/google/authorize")
async def google_authorize(redirect_uri: str = "http://localhost:3000/auth/callback"):
    """Get Google authorization URL"""
    try:
        auth_url, state = GoogleOAuth.get_authorization_url(redirect_uri)
        return {
            "authorization_url": auth_url,
            "state": state,
            "provider": "google"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Google authorization URL"
        )

@router.get("/github/authorize")
async def github_authorize(redirect_uri: str = "http://localhost:3000/auth/callback"):
    """Get GitHub authorization URL"""
    try:
        auth_url, state = GitHubOAuth.get_authorization_url(redirect_uri)
        return {
            "authorization_url": auth_url,
            "state": state,
            "provider": "github"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate GitHub authorization URL"
        )

# ============ OAuth Callbacks ============

@router.post("/google/callback")
async def google_callback(
    code: str,
    state: str,
    redirect_uri: str = "http://localhost:3000/auth/callback",
    db: Session = Depends(get_db),
    request: Request = None
):
    """Handle Google OAuth callback"""
    
    # Validate state
    if not OAuthStateManager.validate_state(state, "google"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token"
        )
    
    try:
        # Exchange code for token
        token_data = await GoogleOAuth.exchange_code_for_token(code, redirect_uri)
        
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=token_data.get("error_description", "Failed to exchange code")
            )
        
        access_token = token_data.get("access_token")
        
        # Get user info
        google_user = await GoogleOAuth.get_user_info(access_token)
        user_data = OAuthUserData.from_google(google_user)
        
        # Cleanup state
        OAuthStateManager.cleanup_state(state)
        
        # Process or create user
        return await process_oauth_user(db, user_data, request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Google authentication"
        )

@router.post("/github/callback")
async def github_callback(
    code: str,
    state: str,
    redirect_uri: str = "http://localhost:3000/auth/callback",
    db: Session = Depends(get_db),
    request: Request = None
):
    """Handle GitHub OAuth callback"""
    
    # Validate state
    if not OAuthStateManager.validate_state(state, "github"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token"
        )
    
    try:
        # Exchange code for token
        token_data = await GitHubOAuth.exchange_code_for_token(code, redirect_uri)
        
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=token_data.get("error_description", "Failed to exchange code")
            )
        
        access_token = token_data.get("access_token")
        
        # Get user info
        github_user = await GitHubOAuth.get_user_info(access_token)
        user_data = OAuthUserData.from_github(github_user)
        
        # Cleanup state
        OAuthStateManager.cleanup_state(state)
        
        # Process or create user
        return await process_oauth_user(db, user_data, request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process GitHub authentication"
        )

# ============ Link OAuth Account ============

@router.post("/link")
async def link_oauth_account(
    provider: str,
    provider_id: str,
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Link OAuth account to existing user"""
    
    if provider not in ["google", "github"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider"
        )
    
    # Check if provider account already linked to another user
    existing_link = db.query(OAuthProvider).filter(
        OAuthProvider.provider == provider,
        OAuthProvider.provider_id == provider_id
    ).first()
    
    if existing_link and existing_link.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This {provider} account is already linked to another user"
        )
    
    # Create or update OAuth link
    oauth_provider = db.query(OAuthProvider).filter(
        OAuthProvider.user_id == current_user.id,
        OAuthProvider.provider == provider
    ).first()
    
    if oauth_provider:
        oauth_provider.provider_id = provider_id
        oauth_provider.email = email
        oauth_provider.updated_at = datetime.utcnow()
    else:
        oauth_provider = OAuthProvider(
            user_id=current_user.id,
            provider=provider,
            provider_id=provider_id,
            email=email
        )
        db.add(oauth_provider)
    
    db.commit()
    
    return {
        "message": f"{provider.capitalize()} account linked successfully",
        "provider": provider
    }

@router.post("/unlink")
async def unlink_oauth_account(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Unlink OAuth account from user"""
    
    if provider not in ["google", "github"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider"
        )
    
    oauth_provider = db.query(OAuthProvider).filter(
        OAuthProvider.user_id == current_user.id,
        OAuthProvider.provider == provider
    ).first()
    
    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account linked to your profile"
        )
    
    db.delete(oauth_provider)
    db.commit()
    
    return {
        "message": f"{provider.capitalize()} account unlinked successfully",
        "provider": provider
    }

@router.get("/linked-accounts")
async def get_linked_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all OAuth accounts linked to user"""
    
    oauth_providers = db.query(OAuthProvider).filter(
        OAuthProvider.user_id == current_user.id
    ).all()
    
    return {
        "linked_accounts": [
            {
                "provider": op.provider,
                "email": op.email,
                "linked_at": op.created_at.isoformat()
            }
            for op in oauth_providers
        ]
    }

# ============ Helper Functions ============

async def process_oauth_user(db: Session, user_data: dict, request: Request = None) -> OAuthResponse:
    """Process OAuth user - create or link account"""
    
    provider = user_data["provider"]
    provider_id = user_data["provider_id"]
    email = user_data["email"]
    name = user_data["name"]
    
    # Check if OAuth provider is already linked
    oauth_provider = db.query(OAuthProvider).filter(
        OAuthProvider.provider == provider,
        OAuthProvider.provider_id == provider_id
    ).first()
    
    if oauth_provider:
        # User already exists - return tokens
        user = oauth_provider.user
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
    else:
        # Check if user exists by email
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Account exists but not linked to this OAuth provider
            # Link the account
            oauth_provider = OAuthProvider(
                user_id=user.id,
                provider=provider,
                provider_id=provider_id,
                email=email
            )
            db.add(oauth_provider)
            db.commit()
        else:
            # Create new user
            username = email.split("@")[0] + str(uuid.uuid4())[:8]
            
            user = User(
                email=email,
                username=username,
                full_name=name or email,
                hashed_password="",  # OAuth users don't have passwords
                is_active=True,
                is_verified=True,
                verified_at=datetime.utcnow(),
                status=UserStatusEnum.ACTIVE.value,
                role=RoleEnum.TESTER.value  # Default role
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Link OAuth provider
            oauth_provider = OAuthProvider(
                user_id=user.id,
                provider=provider,
                provider_id=provider_id,
                email=email
            )
            db.add(oauth_provider)
            db.commit()
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    # Store refresh token
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.add(refresh_token_obj)
    db.commit()
    
    return OAuthResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        access_token=access_token,
        refresh_token=refresh_token
    )
