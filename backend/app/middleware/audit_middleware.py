"""
Advanced Audit Logging Middleware for comprehensive request/response tracking
"""
import time
import json
import uuid
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.models.audit_log import AuditLog, SecurityEvent, UserActivity, PerformanceMetric
from app.core.dependencies import get_current_user_optional, get_api_key_optional
from app.core.config import settings


logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive audit logging middleware that captures all HTTP requests/responses
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health", 
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/favicon.ico"
        ]
        
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Extract request data
        request_data = await self._extract_request_data(request)
        
        # Process request
        response = None
        error = None
        try:
            response = await call_next(request)
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Extract response data
            response_data = await self._extract_response_data(response)
            
            # Log the audit entry
            await self._log_audit_entry(
                request, response, request_data, response_data, 
                request_id, processing_time
            )
            
            return response
            
        except Exception as e:
            error = e
            processing_time = (time.time() - start_time) * 1000
            
            # Log error
            await self._log_error_entry(request, request_data, request_id, processing_time, error)
            raise
    
    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract comprehensive request data"""
        try:
            # Read body (for POST/PUT/PATCH requests)
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        body = body_bytes.decode('utf-8')
                        # Parse JSON if possible (for size calculation)
                        if request.headers.get("content-type", "").startswith("application/json"):
                            json.loads(body)  # Validate JSON
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        body = f"<binary data: {len(body_bytes)} bytes>"
            
            # Extract headers (filter sensitive ones)
            headers = dict(request.headers)
            self._sanitize_headers(headers)
            
            # Extract query parameters
            params = dict(request.query_params) if request.query_params else None
            
            # Get client information
            client_ip = self._get_client_ip(request)
            user_agent = headers.get("user-agent", "")
            referer = headers.get("referer", "")
            
            return {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "headers": headers,
                "body": body,
                "params": params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "referer": referer,
                "request_size": len(body.encode('utf-8')) if body else 0
            }
            
        except Exception as e:
            logger.error(f"Error extracting request data: {e}")
            return {"error": f"Failed to extract request data: {str(e)}"}
    
    async def _extract_response_data(self, response: Response) -> Dict[str, Any]:
        """Extract response data"""
        try:
            # Extract headers
            headers = dict(response.headers)
            
            # Try to get response body (if possible)
            response_body = None
            response_size = 0
            
            if hasattr(response, 'body') and response.body:
                try:
                    if isinstance(response.body, bytes):
                        response_size = len(response.body)
                        # Only log text responses, not binary
                        if response.headers.get("content-type", "").startswith(("application/json", "text/")):
                            response_body = response.body.decode('utf-8')
                            # Truncate large responses
                            if len(response_body) > 10000:
                                response_body = response_body[:10000] + "... [truncated]"
                except (UnicodeDecodeError, AttributeError):
                    response_body = f"<binary response: {response_size} bytes>"
            
            return {
                "status_code": response.status_code,
                "headers": headers,
                "body": response_body,
                "size": response_size
            }
            
        except Exception as e:
            logger.error(f"Error extracting response data: {e}")
            return {"status_code": getattr(response, 'status_code', 500), "error": str(e)}
    
    async def _log_audit_entry(self, request: Request, response: Response, 
                             request_data: Dict, response_data: Dict,
                             request_id: str, processing_time: float):
        """Log comprehensive audit entry to database"""
        try:
            # Get database session
            db = next(get_db())
            
            # Extract user context
            user_context = await self._get_user_context(request, db)
            
            # Determine activity type
            activity_type = self._determine_activity_type(request.url.path, request.method)
            
            # Create audit log entry
            audit_log = AuditLog(
                request_id=request_id,
                method=request_data["method"],
                endpoint=request_data["path"],
                full_url=request_data["url"],
                
                # User context
                user_id=user_context.get("user_id"),
                user_email=user_context.get("user_email"),
                api_key_id=user_context.get("api_key_id"),
                session_id=user_context.get("session_id"),
                
                # Request details
                request_headers=request_data["headers"],
                request_body=self._sanitize_request_body(request_data.get("body")),
                request_params=request_data.get("params"),
                request_size=request_data.get("request_size", 0),
                
                # Response details
                response_status_code=response_data["status_code"],
                response_headers=response_data.get("headers"),
                response_body=self._sanitize_response_body(response_data.get("body")),
                response_size=response_data.get("size", 0),
                
                # Performance
                processing_time_ms=processing_time,
                
                # Network
                client_ip=request_data["client_ip"],
                user_agent=request_data["user_agent"],
                referer=request_data.get("referer"),
                
                # Authentication
                auth_method=user_context.get("auth_method"),
                auth_success=user_context.get("auth_success", True),
                
                # Classification
                activity_type=activity_type,
                log_level="INFO" if response_data["status_code"] < 400 else "ERROR",
                
                # Metadata
                extra_metadata={
                    "request_id": request_id,
                    "processing_time_ms": processing_time,
                    "success": response_data["status_code"] < 400
                },
                tags=self._generate_tags(request.url.path, request.method, response_data["status_code"])
            )
            
            db.add(audit_log)
            
            # Log user activity if user is authenticated
            if user_context.get("user_id"):
                await self._log_user_activity(
                    db, user_context["user_id"], request_data, response_data, 
                    request_id, processing_time, activity_type
                )
            
            # Log performance metrics
            await self._log_performance_metrics(
                db, request_data, response_data, request_id, processing_time
            )
            
            # Log security events if needed
            await self._check_and_log_security_events(
                db, request, response, request_data, response_data, user_context
            )
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error logging audit entry: {e}")
            if db:
                db.rollback()
                db.close()
    
    async def _log_error_entry(self, request: Request, request_data: Dict,
                             request_id: str, processing_time: float, error: Exception):
        """Log error entries"""
        try:
            db = next(get_db())
            
            # Create error audit log
            audit_log = AuditLog(
                request_id=request_id,
                method=request_data["method"],
                endpoint=request_data["path"],
                full_url=request_data["url"],
                request_headers=request_data["headers"],
                request_body=self._sanitize_request_body(request_data.get("body")),
                request_params=request_data.get("params"),
                response_status_code=500,
                processing_time_ms=processing_time,
                client_ip=request_data["client_ip"],
                user_agent=request_data["user_agent"],
                log_level="ERROR",
                activity_type="system_error",
                extra_metadata={
                    "error": str(error),
                    "error_type": type(error).__name__
                }
            )
            
            db.add(audit_log)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error logging error entry: {e}")
    
    async def _get_user_context(self, request: Request, db: Session) -> Dict[str, Any]:
        """Extract user context from request"""
        context = {}
        
        try:
            # Try to get current user from JWT token
            try:
                user = await get_current_user_optional(request, db)
                if user:
                    context["user_id"] = user.id
                    context["user_email"] = user.email
                    context["auth_method"] = "jwt"
                    context["auth_success"] = True
            except:
                pass
            
            # Try to get API key user
            try:
                api_key = await get_api_key_optional(request, db)
                if api_key:
                    context["api_key_id"] = api_key.id
                    context["user_id"] = api_key.user_id
                    context["auth_method"] = "api_key"
                    context["auth_success"] = True
            except:
                pass
            
            # Generate session ID from request if not authenticated
            if not context.get("user_id"):
                session_id = self._generate_session_id(request)
                context["session_id"] = session_id
                context["auth_method"] = "none"
                context["auth_success"] = False
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
        
        return context
    
    async def _log_user_activity(self, db: Session, user_id: str, request_data: Dict,
                               response_data: Dict, request_id: str, processing_time: float,
                               activity_type: str):
        """Log user-specific activity"""
        try:
            activity = UserActivity(
                user_id=user_id,
                request_id=request_id,
                activity_type=activity_type,
                activity_name=f"{request_data['method']} {request_data['path']}",
                activity_description=f"API call to {request_data['path']}",
                endpoint=request_data["path"],
                duration_ms=processing_time,
                success=response_data["status_code"] < 400,
                activity_data={
                    "method": request_data["method"],
                    "status_code": response_data["status_code"],
                    "processing_time_ms": processing_time
                }
            )
            
            db.add(activity)
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
    
    async def _log_performance_metrics(self, db: Session, request_data: Dict,
                                     response_data: Dict, request_id: str, processing_time: float):
        """Log performance metrics"""
        try:
            # API response time metric
            metric = PerformanceMetric(
                metric_type="api_response_time",
                metric_name=f"{request_data['method']} {request_data['path']}",
                value=processing_time,
                unit="ms",
                endpoint=request_data["path"],
                request_id=request_id,
                metadata={
                    "method": request_data["method"],
                    "status_code": response_data["status_code"]
                },
                tags=[
                    request_data["method"].lower(),
                    f"status_{response_data['status_code']}",
                    "api_response_time"
                ]
            )
            
            db.add(metric)
            
        except Exception as e:
            logger.error(f"Error logging performance metrics: {e}")
    
    async def _check_and_log_security_events(self, db: Session, request: Request,
                                           response: Response, request_data: Dict,
                                           response_data: Dict, user_context: Dict):
        """Check for and log security events"""
        try:
            # Failed authentication
            if response_data["status_code"] in [401, 403]:
                security_event = SecurityEvent(
                    event_type="authentication_failure",
                    severity="MEDIUM",
                    user_id=user_context.get("user_id"),
                    user_email=user_context.get("user_email"),
                    request_id=user_context.get("request_id"),
                    client_ip=request_data["client_ip"],
                    user_agent=request_data["user_agent"],
                    endpoint=request_data["path"],
                    description=f"Authentication failed for {request_data['path']}",
                    details={
                        "status_code": response_data["status_code"],
                        "method": request_data["method"],
                        "auth_method": user_context.get("auth_method")
                    }
                )
                
                db.add(security_event)
            
            # Rate limiting
            if response_data["status_code"] == 429:
                security_event = SecurityEvent(
                    event_type="rate_limit_exceeded",
                    severity="LOW",
                    user_id=user_context.get("user_id"),
                    client_ip=request_data["client_ip"],
                    endpoint=request_data["path"],
                    description="Rate limit exceeded",
                    action_taken="request_blocked",
                    automatic_response=True
                )
                
                db.add(security_event)
                
        except Exception as e:
            logger.error(f"Error logging security events: {e}")
    
    def _sanitize_headers(self, headers: Dict) -> Dict:
        """Remove sensitive headers"""
        sensitive_headers = [
            "authorization", "x-api-key", "cookie", "x-auth-token",
            "x-forwarded-for", "x-real-ip"
        ]
        
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"
        
        return headers
    
    def _sanitize_request_body(self, body: Optional[str]) -> Optional[str]:
        """Sanitize sensitive data from request body"""
        if not body:
            return body
        
        try:
            # Try to parse as JSON and remove sensitive fields
            data = json.loads(body)
            sensitive_fields = ["password", "token", "secret", "key", "auth"]
            
            def sanitize_dict(obj):
                if isinstance(obj, dict):
                    for key in list(obj.keys()):
                        if any(field in key.lower() for field in sensitive_fields):
                            obj[key] = "[REDACTED]"
                        elif isinstance(obj[key], dict):
                            sanitize_dict(obj[key])
                        elif isinstance(obj[key], list):
                            for item in obj[key]:
                                if isinstance(item, dict):
                                    sanitize_dict(item)
            
            sanitize_dict(data)
            return json.dumps(data)
            
        except json.JSONDecodeError:
            # If not JSON, just return truncated version
            return body[:1000] + "..." if len(body) > 1000 else body
    
    def _sanitize_response_body(self, body: Optional[str]) -> Optional[str]:
        """Sanitize sensitive data from response body"""
        if not body:
            return body
        
        try:
            # Try to parse as JSON and remove sensitive fields
            data = json.loads(body)
            sensitive_fields = ["access_token", "refresh_token", "password", "secret", "key"]
            
            def sanitize_dict(obj):
                if isinstance(obj, dict):
                    for key in list(obj.keys()):
                        if any(field in key.lower() for field in sensitive_fields):
                            obj[key] = "[REDACTED]"
                        elif isinstance(obj[key], dict):
                            sanitize_dict(obj[key])
                        elif isinstance(obj[key], list):
                            for item in obj[key]:
                                if isinstance(item, dict):
                                    sanitize_dict(item)
            
            sanitize_dict(data)
            return json.dumps(data)
            
        except json.JSONDecodeError:
            return body[:1000] + "..." if len(body) > 1000 else body
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _determine_activity_type(self, path: str, method: str) -> str:
        """Determine activity type based on endpoint"""
        if "/auth/" in path:
            return "authentication"
        elif "/weather/" in path:
            return "weather_api"
        elif "/api-keys/" in path:
            return "api_key_management"
        elif "/billing/" in path:
            return "billing"
        elif "/usage/" in path:
            return "usage_analytics"
        elif "/admin/" in path:
            return "admin"
        elif "/support/" in path:
            return "support"
        else:
            return "api_call"
    
    def _generate_tags(self, path: str, method: str, status_code: int) -> list:
        """Generate tags for categorization"""
        tags = [
            method.lower(),
            f"status_{status_code}",
            "success" if status_code < 400 else "error"
        ]
        
        # Add endpoint-specific tags
        if "/auth/" in path:
            tags.append("authentication")
        elif "/weather/" in path:
            tags.append("weather_api")
        elif "/admin/" in path:
            tags.append("admin")
        
        return tags
    
    def _generate_session_id(self, request: Request) -> str:
        """Generate session ID for unauthenticated requests"""
        # Use a combination of IP and User-Agent for session identification
        ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        return f"session_{hash(f'{ip}_{user_agent}')}"[:16]