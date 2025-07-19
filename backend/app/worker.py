"""
Celery Worker Configuration for Skycaster Weather API System
Handles background tasks for usage reporting, billing, and queue events
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from celery import Celery
from celery.signals import task_success, task_failure, task_prerun, task_postrun
from app.core.config import settings
from app.core.database import get_db

# Configure logging
logger = logging.getLogger(__name__)

# Create Celery app instance
celery_app = Celery(
    "skycaster-worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker"]
)

# Celery configuration
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Structured logging for queue events
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start events"""
    logger.info(
        "Task starting",
        extra={
            "type": "task_event",
            "task": task.name if task else sender.name,
            "status": "started",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "queue": "redis_main",
            "args": str(args)[:200] if args else None,  # Truncate long args
            "kwargs": str(kwargs)[:200] if kwargs else None
        }
    )

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Log successful task completion"""
    logger.info(
        "Task completed successfully",
        extra={
            "type": "task_event",
            "task": sender.name,
            "status": "completed",
            "task_id": sender.request.id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "queue": "redis_main",
            "result": str(result)[:200] if result else None  # Truncate long results
        }
    )

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Log failed tasks"""
    logger.error(
        "Task failed",
        extra={
            "type": "task_event",
            "task": sender.name,
            "status": "failed",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "queue": "redis_main",
            "error": str(exception) if exception else None,
            "traceback": str(traceback)[:500] if traceback else None  # Truncate long tracebacks
        }
    )

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion regardless of success/failure"""
    logger.info(
        "Task finished",
        extra={
            "type": "task_event",
            "task": task.name if task else sender.name,
            "status": "finished",
            "task_id": task_id,
            "state": state,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "queue": "redis_main"
        }
    )

# Background tasks
@celery_app.task(bind=True, name="send_usage_report")
def send_usage_report(self, user_id: int, period: str = "monthly"):
    """
    Generate and send usage reports to users
    """
    try:
        logger.info(
            "Processing usage report",
            extra={
                "type": "task_event",
                "task": "send_usage_report",
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "user_id": user_id,
                "period": period,
                "queue": "redis_main"
            }
        )
        
        # Mock implementation for now - would integrate with email service
        # In production, this would:
        # 1. Query usage_logs for the user and period
        # 2. Generate report summary
        # 3. Send email via email service
        
        report_data = {
            "user_id": user_id,
            "period": period,
            "generated_at": datetime.utcnow().isoformat(),
            "total_requests": 1250,  # Mock data
            "total_cost": 15.75,     # Mock data
            "status": "sent"
        }
        
        return report_data
        
    except Exception as exc:
        logger.error(f"Usage report failed for user {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@celery_app.task(bind=True, name="process_billing_cycle")
def process_billing_cycle(self, billing_period: str):
    """
    Process billing for all users at end of billing cycle
    """
    try:
        logger.info(
            "Processing billing cycle",
            extra={
                "type": "task_event",
                "task": "process_billing_cycle",
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "billing_period": billing_period,
                "queue": "redis_main"
            }
        )
        
        # Mock implementation for now
        # In production, this would:
        # 1. Query all active subscriptions
        # 2. Calculate usage charges
        # 3. Generate invoices
        # 4. Process payments via Stripe
        # 5. Send billing notifications
        
        billing_summary = {
            "billing_period": billing_period,
            "processed_at": datetime.utcnow().isoformat(),
            "total_users": 145,      # Mock data
            "total_revenue": 2847.50, # Mock data
            "failed_payments": 3     # Mock data
        }
        
        return billing_summary
        
    except Exception as exc:
        logger.error(f"Billing cycle processing failed: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=2)

@celery_app.task(bind=True, name="cleanup_expired_api_keys")
def cleanup_expired_api_keys(self):
    """
    Clean up expired API keys and related data
    """
    try:
        logger.info(
            "Cleaning up expired API keys",
            extra={
                "type": "task_event",
                "task": "cleanup_expired_api_keys",
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "queue": "redis_main"
            }
        )
        
        # Mock implementation for now
        # In production, this would:
        # 1. Query for expired API keys
        # 2. Deactivate them in database
        # 3. Clean up related cache entries
        # 4. Log security events
        
        cleanup_summary = {
            "processed_at": datetime.utcnow().isoformat(),
            "expired_keys_found": 12,   # Mock data
            "keys_deactivated": 12,     # Mock data
            "cache_entries_cleared": 48  # Mock data
        }
        
        return cleanup_summary
        
    except Exception as exc:
        logger.error(f"API key cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=120, max_retries=3)

@celery_app.task(bind=True, name="monitor_queue_health")
def monitor_queue_health(self):
    """
    Monitor Redis queue backlog and system health
    """
    try:
        import redis
        
        # Connect to Redis to check queue health
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        
        # Get queue statistics
        active_tasks = celery_app.control.inspect().active()
        scheduled_tasks = celery_app.control.inspect().scheduled()
        
        # Redis memory usage
        redis_info = r.info()
        memory_usage = redis_info.get('used_memory_human', 'Unknown')
        
        queue_stats = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "redis_memory_usage": memory_usage,
            "active_tasks_count": len(active_tasks) if active_tasks else 0,
            "scheduled_tasks_count": len(scheduled_tasks) if scheduled_tasks else 0,
            "redis_connected_clients": redis_info.get('connected_clients', 0)
        }
        
        logger.info(
            "Queue health check completed",
            extra={
                "type": "task_event",
                "task": "monitor_queue_health",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "queue": "redis_main",
                **queue_stats
            }
        )
        
        return queue_stats
        
    except Exception as exc:
        logger.error(f"Queue health monitoring failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=2)

# Periodic tasks configuration (for Celery Beat)
celery_app.conf.beat_schedule = {
    'cleanup-expired-keys': {
        'task': 'cleanup_expired_api_keys',
        'schedule': 3600.0,  # Every hour
    },
    'monitor-queue-health': {
        'task': 'monitor_queue_health',
        'schedule': 300.0,   # Every 5 minutes
    },
    'process-monthly-billing': {
        'task': 'process_billing_cycle',
        'schedule': 86400.0, # Daily check for billing
        'kwargs': {'billing_period': 'monthly'}
    },
}

# Make tasks available for import
__all__ = [
    'celery_app',
    'send_usage_report',
    'process_billing_cycle',
    'cleanup_expired_api_keys',
    'monitor_queue_health'
]