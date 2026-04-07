import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from ..core.security import security_manager, audit_logger
from ..core.monitoring import performance_monitor

logger = structlog.get_logger()

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for request validation and protection"""
    
    def __init__(self, app, config: dict = None):
        super().__init__(app)
        self.config = config or {}
        self.max_request_size = self.config.get("max_request_size", 10 * 1024 * 1024)  # 10MB
        self.rate_limit_enabled = self.config.get("rate_limit_enabled", True)
        self.ip_whitelist_enabled = self.config.get("ip_whitelist_enabled", False)
        self.request_timeout = self.config.get("request_timeout", 30)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security checks"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip
        
        try:
            # Security checks
            await self._perform_security_checks(request)
            
            # Process request
            response = await call_next(request)
            
            # Security headers
            await self._add_security_headers(response)
            
            # Log successful request
            duration_ms = (time.time() - start_time) * 1000
            await self._log_request(request, response, duration_ms, True)
            
            # Record metrics
            performance_monitor.record_request_metric(
                request.url.path,
                request.method,
                response.status_code,
                duration_ms
            )
            
            return response
            
        except HTTPException as e:
            # Log HTTP exception
            duration_ms = (time.time() - start_time) * 1000
            await self._log_request(request, None, duration_ms, False, str(e.detail))
            
            # Record metrics
            performance_monitor.record_request_metric(
                request.url.path,
                request.method,
                e.status_code,
                duration_ms
            )
            
            raise
            
        except Exception as e:
            # Log unexpected exception
            duration_ms = (time.time() - start_time) * 1000
            await self._log_request(request, None, duration_ms, False, str(e))
            
            # Record metrics
            performance_monitor.record_request_metric(
                request.url.path,
                request.method,
                500,
                duration_ms
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def _perform_security_checks(self, request: Request):
        """Perform security checks on request"""
        # IP validation
        if not security_manager.is_ip_allowed(request.state.client_ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address not allowed"
            )
        
        # Rate limiting
        if self.rate_limit_enabled:
            if not security_manager.check_rate_limit(request.state.client_ip, request.url.path):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
        
        # Request size validation
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Header validation
        if not security_manager.validate_request_headers(request):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request headers"
            )
        
        # Check for suspicious patterns
        await self._check_suspicious_patterns(request)
    
    async def _check_suspicious_patterns(self, request: Request):
        """Check for suspicious request patterns"""
        # Check User-Agent
        user_agent = request.headers.get("user-agent", "")
        suspicious_agents = [
            "sqlmap", "nikto", "nmap", "masscan", "zap", "burp"
        ]
        
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            logger.warning(f"Suspicious User-Agent detected: {user_agent}")
        
        # Check URL patterns
        url_path = request.url.path.lower()
        suspicious_paths = [
            "/admin", "/wp-admin", "/phpmyadmin", "/.env",
            "/config", "/backup", "/test", "/debug"
        ]
        
        if any(path in url_path for path in suspicious_paths):
            logger.warning(f"Suspicious URL path accessed: {url_path}")
        
        # Check for common attack patterns
        if request.query_params:
            query_string = str(request.query_params).lower()
            attack_patterns = [
                "union select", "drop table", "insert into",
                "javascript:", "vbscript:", "data:",
                "<script", "</script>", "onerror=", "onload="
            ]
            
            if any(pattern in query_string for pattern in attack_patterns):
                logger.warning(f"Suspicious query parameters detected: {query_string}")
    
    async def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Request-ID": getattr(response, "request_id", "")
        }
        
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _log_request(
        self,
        request: Request,
        response: Response = None,
        duration_ms: float = 0,
        success: bool = True,
        error_message: str = None
    ):
        """Log request details"""
        log_data = {
            "request_id": getattr(request.state, "request_id", "unknown"),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": getattr(request.state, "client_ip", "unknown"),
            "user_agent": request.headers.get("user-agent", ""),
            "duration_ms": duration_ms,
            "success": success
        }
        
        if response:
            log_data["status_code"] = response.status_code
        
        if error_message:
            log_data["error"] = error_message
        
        if success:
            logger.info("Request processed", **log_data)
        else:
            logger.warning("Request failed", **log_data)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for API endpoints"""
    
    def __init__(self, app, public_paths: list = None):
        super().__init__(app)
        self.public_paths = public_paths or [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/api/v1/chatops/slack/events",
            "/api/v1/chatops/teams/events"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication"""
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Check for API key authentication
        api_key = request.headers.get("x-api-key")
        if api_key:
            # Validate API key
            # This would integrate with your API key validation
            if await self._validate_api_key(api_key):
                request.state.auth_type = "api_key"
                request.state.user_id = "api_user"
                return await call_next(request)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
        
        # Check for JWT token
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            try:
                payload = security_manager.verify_token(token)
                request.state.auth_type = "jwt"
                request.state.user_id = payload.get("sub")
                request.state.username = payload.get("username")
                request.state.roles = payload.get("roles", [])
                return await call_next(request)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        
        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public"""
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False
    
    async def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        # This would integrate with your database or API key service
        # For now, simple validation
        valid_keys = ["test-api-key", "prod-api-key"]
        return api_key in valid_keys

class AuditMiddleware(BaseHTTPMiddleware):
    """Audit middleware for logging security events"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with audit logging"""
        start_time = time.time()
        
        # Get user info from request state
        user_id = getattr(request.state, "user_id", "anonymous")
        username = getattr(request.state, "username", "anonymous")
        client_ip = getattr(request.state, "client_ip", "unknown")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log successful API access
            if self._should_audit_endpoint(request.url.path):
                duration_ms = (time.time() - start_time) * 1000
                audit_logger.log_api_access(
                    user_id=user_id,
                    username=username,
                    ip_address=client_ip,
                    endpoint=request.url.path,
                    method=request.method,
                    success=response.status_code < 400
                )
            
            return response
            
        except Exception as e:
            # Log failed API access
            if self._should_audit_endpoint(request.url.path):
                duration_ms = (time.time() - start_time) * 1000
                audit_logger.log_api_access(
                    user_id=user_id,
                    username=username,
                    ip_address=client_ip,
                    endpoint=request.url.path,
                    method=request.method,
                    success=False,
                    error_message=str(e)
                )
            raise
    
    def _should_audit_endpoint(self, path: str) -> bool:
        """Check if endpoint should be audited"""
        # Audit all API endpoints except health checks
        return path.startswith("/api/") and not path.endswith("/health")

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Performance monitoring middleware"""
    
    def __init__(self, app, slow_request_threshold_ms: float = 1000):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring"""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log slow requests
        if duration_ms > self.slow_request_threshold_ms:
            logger.warning(
                "Slow request detected",
                path=request.url.path,
                method=request.method,
                duration_ms=duration_ms,
                client_ip=getattr(request.state, "client_ip", "unknown")
            )
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response

class CompressionMiddleware(BaseHTTPMiddleware):
    """Compression middleware for response compression"""
    
    def __init__(self, app, min_size: int = 1024):
        super().__init__(app)
        self.min_size = min_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with compression"""
        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Compress response if it's large enough and not already compressed
        if (
            hasattr(response, "body") and
            len(response.body) > self.min_size and
            "content-encoding" not in response.headers
        ):
            # This would implement actual compression
            # For now, just add the header
            response.headers["Content-Encoding"] = "gzip"
        
        return response
