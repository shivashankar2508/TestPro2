from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User, RoleEnum, UserStatusEnum, PasswordHistory, RefreshToken, AuditLog
from app.schemas.auth import (
    UserRegister, UserLogin, UserResponse, TokenResponse, 
    VerifyEmail, PasswordReset, PasswordResetConfirm, UserChangePassword
)
from app.utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    generate_verification_token, generate_reset_token, is_account_locked,
    calculate_lockout_until, is_password_strong, verify_token_type,
    decode_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.utils.email_service import EmailService
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ============ Utilities ============
def record_audit_log(
    db: Session,
    user_id: int = None,
    action: str = "",
    resource_type: str = None,
    resource_id: int = None,
    details: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Record an audit log entry"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_log)
    db.commit()

# ============ Registration ============
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Requirements:
    - Unique email and username
    - Password strength validation
    - Email verification required
    - Account status: PENDING_VERIFICATION
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        
        # Validate password strength
        is_strong, errors = is_password_strong(user_data.password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=errors[0]
            )
        
        # Create verification token
        verification_token = generate_verification_token()
        verification_expiry = datetime.utcnow() + timedelta(hours=24)
        
        # In development mode, auto-verify users
        is_dev_mode = settings.ENV == "development"
        
        # Create new user
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
            verification_token=None if is_dev_mode else verification_token,
            verification_token_expiry=None if is_dev_mode else verification_expiry,
            is_verified=is_dev_mode,  # Auto-verify in development
            is_active=is_dev_mode,  # Auto-activate in development
            verified_at=datetime.utcnow() if is_dev_mode else None,
            status=UserStatusEnum.ACTIVE.value if is_dev_mode else UserStatusEnum.PENDING_VERIFICATION.value,
            role=user_data.role.value if hasattr(user_data.role, 'value') else user_data.role or "tester"
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send verification email only in production
        if not is_dev_mode:
            email_sent = EmailService.send_verification_email(user_data.email, verification_token)
        
        # Record audit log
        record_audit_log(
            db,
            action="user_registration",
            details=f"User registered: {user_data.email} (auto-verified: {is_dev_mode})"
        )
        
        return new_user
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

# ============ Email Verification ============
@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    verify_data: VerifyEmail,
    db: Session = Depends(get_db)
):
    """
    Verify user email with token
    
    Token expires in 24 hours
    """
    user = db.query(User).filter(
        User.verification_token == verify_data.token
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Check if token expired
    if user.verification_token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )
    
    # Verify user
    user.is_verified = True
    user.is_active = True
    user.status = UserStatusEnum.ACTIVE.value
    user.verification_token = None
    user.verification_token_expiry = None
    user.verified_at = datetime.utcnow()
    
    db.add(user)
    db.commit()
    
    # Record audit log
    record_audit_log(
        db,
        user_id=user.id,
        action="email_verified"
    )
    
    return {"message": "Email verified successfully"}

# ============ Login ============
@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User login with email and password
    
    Features:
    - JWT-based authentication
    - Account lockout after 5 failed attempts
    - Remember me functionality (extended session)
    - Refresh token support
    """
    # Find user
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if email verified (skip in development mode)
    if not user.is_verified and settings.ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Check your inbox for verification link."
        )
    
    # Check if account locked
    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account locked due to multiple failed login attempts. Try again later."
        )
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = calculate_lockout_until()
            user.status = UserStatusEnum.LOCKED.value
            db.add(user)
            db.commit()
            
            # Send lockout email
            EmailService.send_account_locked_email(user.email, 15)
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account locked due to multiple failed login attempts"
            )
        else:
            db.add(user)
            db.commit()
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.status = UserStatusEnum.ACTIVE.value
    user.last_login = datetime.utcnow()
    
    # Create tokens
    access_token_expires = timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 24 if login_data.remember_me else ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires
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
    
    db.add(user)
    db.add(refresh_token_obj)
    db.commit()
    
    # Record audit log
    record_audit_log(
        db,
        user_id=user.id,
        action="user_login"
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_token_expires.total_seconds())
    )

# ============ Password Reset ============
@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset flow
    
    Sends email with reset link
    Link expires in 1 hour
    """
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if not user:
        # Don't reveal if email exists (security best practice)
        return {"message": "If email exists, reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    
    user.verification_token = reset_token
    user.verification_token_expiry = reset_token_expiry
    
    db.add(user)
    db.commit()
    
    # Send reset email
    EmailService.send_password_reset_email(user.email, reset_token)
    
    # Record audit log
    record_audit_log(
        db,
        action="password_reset_requested",
        details=f"Password reset requested for: {reset_data.email}"
    )
    
    return {"message": "If email exists, reset link has been sent"}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password with token
    
    Token expires in 1 hour
    Password strength validation required
    """
    user = db.query(User).filter(
        User.verification_token == reset_data.token
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Check if token expired
    if user.verification_token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Validate password strength
    is_strong, errors = is_password_strong(reset_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors[0]
        )
    
    # Check password history (cannot reuse last 5 passwords)
    recent_passwords = db.query(PasswordHistory).filter(
        PasswordHistory.user_id == user.id
    ).order_by(PasswordHistory.created_at.desc()).limit(5).all()
    
    new_hash = hash_password(reset_data.new_password)
    for pwd_history in recent_passwords:
        if verify_password(reset_data.new_password, pwd_history.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reuse one of your last 5 passwords"
            )
    
    # Update password
    user.hashed_password = new_hash
    user.verification_token = None
    user.verification_token_expiry = None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.status = UserStatusEnum.ACTIVE.value
    
    # Record password history
    password_history = PasswordHistory(
        user_id=user.id,
        hashed_password=new_hash
    )
    
    db.add(user)
    db.add(password_history)
    db.commit()
    
    # Record audit log
    record_audit_log(
        db,
        user_id=user.id,
        action="password_reset"
    )
    
    return {"message": "Password reset successfully"}

# ============ Change Password ============
@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    pwd_data: UserChangePassword,
    current_user = None,
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user
    
    Requires current password verification
    Cannot reuse last 5 passwords
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = db.query(User).filter(User.id == current_user.id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(pwd_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    is_strong, errors = is_password_strong(pwd_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors[0]
        )
    
    # Check password history
    recent_passwords = db.query(PasswordHistory).filter(
        PasswordHistory.user_id == user.id
    ).order_by(PasswordHistory.created_at.desc()).limit(5).all()
    
    for pwd_history in recent_passwords:
        if verify_password(pwd_data.new_password, pwd_history.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reuse one of your last 5 passwords"
            )
    
    # Update password
    new_hash = hash_password(pwd_data.new_password)
    user.hashed_password = new_hash
    
    # Record password history
    password_history = PasswordHistory(
        user_id=user.id,
        hashed_password=new_hash
    )
    
    db.add(user)
    db.add(password_history)
    db.commit()
    
    # Record audit log
    record_audit_log(
        db,
        user_id=user.id,
        action="password_changed"
    )
    
    return {"message": "Password changed successfully"}

# ============ Refresh Token ============
@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    refresh_data: dict,  # {"refresh_token": "..."}
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Seamless token refresh
    """
    refresh_token = refresh_data.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )
    
    # Verify token
    payload = decode_token(refresh_token)
    if not payload or not verify_token_type(payload, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if token is revoked
    token_obj = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.revoked == False
    ).first()
    
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked"
        )
    
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    new_access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

# ============ Logout ============
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user = None,
    db: Session = Depends(get_db)
):
    """Logout user (revoke refresh tokens)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Revoke all refresh tokens for user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    
    db.commit()
    
    # Record audit log
    record_audit_log(
        db,
        user_id=current_user.id,
        action="user_logout"
    )
    
    return {"message": "Logged out successfully"}

# ============ Logout All Devices ============
@router.post("/logout-all-devices", status_code=status.HTTP_200_OK)
async def logout_all_devices(
    current_user = None,
    db: Session = Depends(get_db)
):
    """Logout from all devices (revoke all refresh tokens)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Revoke all refresh tokens
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id
    ).update({"revoked": True})
    
    db.commit()
    
    # Record audit log
    record_audit_log(
        db,
        user_id=current_user.id,
        action="logout_all_devices"
    )
    
    return {"message": "Logged out from all devices"}
