from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth import AuthService
from app.services.api_key import ApiKeyService
from app.services.email import EmailService
from app.services.audit_service import AuditService
from app.schemas.auth import (
    Token, LoginRequest, RegisterRequest, 
    PasswordResetRequest, PasswordResetConfirm, EmailVerificationRequest
)
from app.schemas.user import UserResponse
from app.schemas.api_key import ApiKeyResponse

router = APIRouter()

def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if hasattr(request, "client") and request.client:
        return request.client.host
    return "unknown"

@router.post("/register", response_model=dict)
async def register(
    user_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user with comprehensive logging"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        # Register user
        user = AuthService.register_user(db, user_data)
        
        # Create default API key
        api_key = ApiKeyService.create_api_key(
            db, 
            user.id, 
            type("ApiKeyCreate", (), {"name": "Default API Key"})()
        )
        
        # Create access token
        access_token = AuthService.create_access_token(data={"sub": user.id})
        
        # Log successful registration
        AuditService.log_authentication_event(
            db,
            event_type="register_success",
            user_id=str(user.id),
            user_email=user.email,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "registration_method": "email",
                "user_role": user.role.value,
                "subscription_plan": "free",
                "default_api_key_created": True
            }
        )
        
        # Log API key creation
        AuditService.log_api_key_event(
            db,
            event_type="api_key_created",
            user_id=str(user.id),
            api_key_id=str(api_key.id),
            api_key_name="Default API Key",
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "created_during_registration": True,
                "auto_generated": True
            }
        )
        
        # Send welcome email
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        EmailService.send_welcome_email(user.email, user_name)
        
        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user),
            "api_key": ApiKeyResponse.from_orm(api_key)
        }
        
    except ValueError as e:
        # Log failed registration
        AuditService.log_authentication_event(
            db,
            event_type="register_failure",
            attempted_email=user_data.email,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "error_reason": str(e),
                "registration_method": "email"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login(
    user_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """User login with comprehensive logging"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, 'request_id', None)
    
    user = AuthService.authenticate_user(db, user_data.email, user_data.password)
    
    if not user:
        # Log failed login
        AuditService.log_authentication_event(
            db,
            event_type="login_failure",
            attempted_email=user_data.email,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "failure_reason": "invalid_credentials",
                "login_method": "email_password"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = AuthService.create_access_token(data={"sub": user.id})
    
    # Log successful login
    AuditService.log_authentication_event(
        db,
        event_type="login_success",
        user_id=str(user.id),
        user_email=user.email,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        additional_data={
            "login_method": "email_password",
            "user_role": user.role.value,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "is_verified": user.is_verified
        }
    )
    
    # Update last login time
    user.last_login = db.func.now()
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token login with logging"""
    client_ip = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("user-agent", "") if request else ""
    request_id = getattr(request.state, 'request_id', None) if request else None
    
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        # Log failed OAuth login
        AuditService.log_authentication_event(
            db,
            event_type="oauth_login_failure",
            attempted_email=form_data.username,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "failure_reason": "invalid_credentials",
                "login_method": "oauth2_password"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = AuthService.create_access_token(data={"sub": user.id})
    
    # Log successful OAuth login
    AuditService.log_authentication_event(
        db,
        event_type="oauth_login_success",
        user_id=str(user.id),
        user_email=user.email,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        additional_data={
            "login_method": "oauth2_password",
            "user_role": user.role.value
        }
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get current user information with activity logging"""
    if request:
        client_ip = get_client_ip(request)
        request_id = getattr(request.state, 'request_id', None)
        
        # Log profile access
        AuditService.log_authentication_event(
            db,
            event_type="profile_access",
            user_id=str(current_user.id),
            user_email=current_user.email,
            client_ip=client_ip,
            request_id=request_id,
            additional_data={
                "access_type": "profile_view",
                "endpoint": "/auth/me"
            }
        )
    
    return current_user

@router.post("/forgot-password")
async def forgot_password(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request password reset with logging"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, 'request_id', None)
    
    user = AuthService.get_user_by_email(db, request_data.email)
    
    # Log password reset request (regardless of email existence for security)
    AuditService.log_authentication_event(
        db,
        event_type="password_reset_request",
        user_id=str(user.id) if user else None,
        user_email=user.email if user else None,
        attempted_email=request_data.email,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        additional_data={
            "email_exists": user is not None,
            "reset_method": "email"
        }
    )
    
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = AuthService.create_access_token(
        data={"sub": user.id, "type": "password_reset"}
    )
    
    # Send reset email
    EmailService.send_password_reset_email(user.email, reset_token)
    
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(
    request_data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db)
):
    """Reset password using token with logging"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, 'request_id', None)
    
    payload = AuthService.verify_token(request_data.token)
    if not payload or payload.get("type") != "password_reset":
        # Log invalid reset attempt
        AuditService.log_authentication_event(
            db,
            event_type="password_reset_failure",
            attempted_email="unknown",
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "failure_reason": "invalid_token",
                "token_provided": bool(request_data.token)
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user_id = payload.get("sub")
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = AuthService.hash_password(request_data.new_password)
    db.commit()
    
    # Log successful password reset
    AuditService.log_authentication_event(
        db,
        event_type="password_reset_success",
        user_id=str(user.id),
        user_email=user.email,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        additional_data={
            "reset_method": "email_token",
            "password_changed": True
        }
    )
    
    return {"message": "Password reset successfully"}

@router.post("/verify-email")
async def verify_email(
    request_data: EmailVerificationRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify email address with logging"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    request_id = getattr(request.state, 'request_id', None)
    
    payload = AuthService.verify_token(request_data.token)
    if not payload or payload.get("type") != "email_verification":
        # Log invalid verification attempt
        AuditService.log_authentication_event(
            db,
            event_type="email_verification_failure",
            attempted_email="unknown",
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "failure_reason": "invalid_token"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user_id = payload.get("sub")
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify email
    user.is_verified = True
    db.commit()
    
    # Log successful email verification
    AuditService.log_authentication_event(
        db,
        event_type="email_verification_success",
        user_id=str(user.id),
        user_email=user.email,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        additional_data={
            "verification_method": "email_token",
            "account_verified": True
        }
    )
    
    return {"message": "Email verified successfully"}

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Refresh access token with logging"""
    if request:
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        request_id = getattr(request.state, 'request_id', None)
        
        # Log token refresh
        AuditService.log_authentication_event(
            db,
            event_type="token_refresh",
            user_id=str(current_user.id),
            user_email=current_user.email,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            additional_data={
                "refresh_method": "bearer_token",
                "user_role": current_user.role.value
            }
        )
    
    access_token = AuthService.create_access_token(data={"sub": current_user.id})
    return {"access_token": access_token, "token_type": "bearer"}