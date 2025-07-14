from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.services.api_key import ApiKeyService
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate

router = APIRouter()

@router.post("/", response_model=ApiKeyResponse)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create a new API key"""
    api_key = ApiKeyService.create_api_key(db, current_user.id, api_key_data)
    return api_key

@router.get("/", response_model=List[ApiKeyResponse])
async def get_user_api_keys(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get all API keys for current user"""
    api_keys = ApiKeyService.get_user_api_keys(db, current_user.id)
    return api_keys

@router.get("/{api_key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get specific API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    return api_key

@router.put("/{api_key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    api_key_id: str,
    api_key_update: ApiKeyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    updated_api_key = ApiKeyService.update_api_key(db, api_key_id, api_key_update)
    return updated_api_key

@router.delete("/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Delete API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    success = ApiKeyService.delete_api_key(db, api_key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )
    
    return {"message": "API key deleted successfully"}

@router.post("/{api_key_id}/regenerate", response_model=ApiKeyResponse)
async def regenerate_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Regenerate API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    regenerated_api_key = ApiKeyService.regenerate_api_key(db, api_key_id)
    return regenerated_api_key

@router.get("/{api_key_id}/usage", response_model=dict)
async def get_api_key_usage(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get usage statistics for API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    usage_stats = ApiKeyService.get_api_key_usage_stats(db, api_key_id)
    return usage_stats

@router.post("/{api_key_id}/activate")
async def activate_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Activate API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    activated_api_key = ApiKeyService.activate_api_key(db, api_key_id)
    return {"message": "API key activated successfully"}

@router.post("/{api_key_id}/deactivate")
async def deactivate_api_key(
    api_key_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Deactivate API key"""
    api_key = ApiKeyService.get_api_key(db, api_key_id)
    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    deactivated_api_key = ApiKeyService.deactivate_api_key(db, api_key_id)
    return {"message": "API key deactivated successfully"}