from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.services.user import UserService
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user = Depends(get_current_active_user)
):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update current user profile"""
    updated_user = UserService.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user

@router.get("/me/usage", response_model=dict)
async def get_current_user_usage(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get current user usage statistics"""
    usage_stats = UserService.get_user_usage_stats(db, current_user.id)
    return usage_stats

@router.get("/me/subscription", response_model=dict)
async def get_current_user_subscription(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get current user subscription information"""
    user_with_subscription = UserService.get_user_with_subscription(db, current_user.id)
    return user_with_subscription

@router.post("/me/deactivate")
async def deactivate_current_user(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Deactivate current user account"""
    deactivated_user = UserService.deactivate_user(db, current_user.id)
    return {"message": "Account deactivated successfully"}