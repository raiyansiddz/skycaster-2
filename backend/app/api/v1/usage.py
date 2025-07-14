from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.services.usage_log import UsageLogService
from app.schemas.usage_log import UsageLogResponse

router = APIRouter()

@router.get("/", response_model=List[UsageLogResponse])
async def get_user_usage_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get usage logs for current user"""
    if limit > 1000:
        limit = 1000
    
    usage_logs = UsageLogService.get_user_usage_logs(db, current_user.id, skip, limit)
    return usage_logs

@router.get("/stats", response_model=dict)
async def get_usage_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get usage statistics for current user"""
    if days > 365:
        days = 365
    
    stats = UsageLogService.get_usage_stats(db, current_user.id, days)
    return stats

@router.get("/analytics", response_model=dict)
async def get_usage_analytics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get detailed usage analytics"""
    # Get stats for different time periods
    today_stats = UsageLogService.get_usage_stats(db, current_user.id, 1)
    week_stats = UsageLogService.get_usage_stats(db, current_user.id, 7)
    month_stats = UsageLogService.get_usage_stats(db, current_user.id, 30)
    all_time_stats = UsageLogService.get_usage_stats(db, current_user.id, 365)
    
    return {
        "today": today_stats,
        "this_week": week_stats,
        "this_month": month_stats,
        "all_time": all_time_stats
    }

@router.get("/endpoints", response_model=dict)
async def get_endpoint_usage(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get usage statistics by endpoint"""
    stats = UsageLogService.get_usage_stats(db, current_user.id, 30)
    return {
        "endpoint_usage": stats.get("endpoint_usage", []),
        "period": "Last 30 days"
    }

@router.get("/locations", response_model=dict)
async def get_location_usage(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get usage statistics by location"""
    stats = UsageLogService.get_usage_stats(db, current_user.id, 30)
    return {
        "location_usage": stats.get("top_locations", []),
        "period": "Last 30 days"
    }

@router.get("/export")
async def export_usage_data(
    days: int = 30,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Export usage data"""
    if days > 365:
        days = 365
    
    if format not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'json' or 'csv'"
        )
    
    usage_logs = UsageLogService.get_user_usage_logs(db, current_user.id, 0, 10000)
    
    if format == "json":
        return {
            "data": [log.dict() for log in usage_logs],
            "total_records": len(usage_logs),
            "period_days": days
        }
    else:
        # CSV format would be implemented here
        return {
            "message": "CSV export feature coming soon",
            "data": usage_logs
        }