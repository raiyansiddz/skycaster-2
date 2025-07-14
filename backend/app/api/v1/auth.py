from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth import AuthService
from app.services.api_key import ApiKeyService
from app.services.email import EmailService
from app.schemas.auth import (
    Token, LoginRequest, RegisterRequest, 
    PasswordResetRequest, PasswordResetConfirm, EmailVerificationRequest
)
from app.schemas.user import UserResponse
from app.schemas.api_key import ApiKeyResponse

router = APIRouter()

@router.post("/register", response_model=dict)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user"""
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login(
    user_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """User login"""
    user = AuthService.authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = AuthService.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token login"""
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = AuthService.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    user = AuthService.get_user_by_email(db, request.email)
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
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password using token"""
    payload = AuthService.verify_token(request.token)
    if not payload or payload.get("type") != "password_reset":
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
    user.hashed_password = AuthService.hash_password(request.new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify email address"""
    payload = AuthService.verify_token(request.token)
    if not payload or payload.get("type") != "email_verification":
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
    
    return {"message": "Email verified successfully"}

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user = Depends(get_current_user)
):
    """Refresh access token"""
    access_token = AuthService.create_access_token(data={"sub": current_user.id})
    return {"access_token": access_token, "token_type": "bearer"}