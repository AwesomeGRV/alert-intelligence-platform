from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
import bcrypt
import secrets
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import ipaddress
from dataclasses import dataclass

from ..core.database import get_db
from ..core.config import settings

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

@dataclass
class User:
    id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    is_active: bool = True
    last_login: Optional[datetime] = None

@dataclass
class SecurityContext:
    user: User
    session_id: str
    ip_address: str
    user_agent: str
    permissions: List[str]

class SecurityManager:
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 15
        self.failed_attempts = {}  # In production, use Redis
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") not in ["access", "refresh"]:
                raise jwt.InvalidTokenError("Invalid token type")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def check_rate_limit(self, ip_address: str, endpoint: str) -> bool:
        """Check rate limiting for IP and endpoint"""
        # In production, use Redis for distributed rate limiting
        # This is a simplified implementation
        return True
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed"""
        try:
            # Check against allowed IP ranges
            if hasattr(settings, 'ALLOWED_IP_RANGES'):
                for ip_range in settings.ALLOWED_IP_RANGES:
                    if ipaddress.ip_address(ip_address) in ipaddress.ip_network(ip_range):
                        return True
                return False
            
            # Check against blocked IPs
            if hasattr(settings, 'BLOCKED_IPS'):
                if ip_address in settings.BLOCKED_IPS:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"IP validation error: {str(e)}")
            return True  # Allow on error
    
    def check_login_attempts(self, ip_address: str, username: str) -> bool:
        """Check if user/IP is locked out due to failed attempts"""
        key = f"{ip_address}:{username}"
        
        if key in self.failed_attempts:
            attempts, last_attempt = self.failed_attempts[key]
            
            # Check if lockout period has passed
            if datetime.utcnow() - last_attempt > timedelta(minutes=self.lockout_duration_minutes):
                del self.failed_attempts[key]
                return True
            
            return attempts < self.max_login_attempts
        
        return True
    
    def record_failed_attempt(self, ip_address: str, username: str):
        """Record failed login attempt"""
        key = f"{ip_address}:{username}"
        
        if key in self.failed_attempts:
            attempts, _ = self.failed_attempts[key]
            self.failed_attempts[key] = (attempts + 1, datetime.utcnow())
        else:
            self.failed_attempts[key] = (1, datetime.utcnow())
    
    def clear_failed_attempts(self, ip_address: str, username: str):
        """Clear failed login attempts on successful login"""
        key = f"{ip_address}:{username}"
        if key in self.failed_attempts:
            del self.failed_attempts[key]
    
    def generate_api_key(self) -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return self.hash_password(api_key)
    
    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """Verify API key"""
        return self.verify_password(api_key, hashed_key)

class RBACManager:
    def __init__(self):
        self.permissions = {
            "admin": [
                "alerts:read", "alerts:write", "alerts:delete",
                "incidents:read", "incidents:write", "incidents:delete",
                "dashboard:read", "dashboard:configure",
                "users:read", "users:write", "users:delete",
                "system:configure", "system:monitor"
            ],
            "operator": [
                "alerts:read", "alerts:write",
                "incidents:read", "incidents:write",
                "dashboard:read", "dashboard:configure",
                "system:monitor"
            ],
            "viewer": [
                "alerts:read",
                "incidents:read",
                "dashboard:read"
            ],
            "api_user": [
                "alerts:write",
                "incidents:read"
            ]
        }
    
    def has_permission(self, user_roles: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        for role in user_roles:
            if required_permission in self.permissions.get(role, []):
                return True
        return False
    
    def get_user_permissions(self, user_roles: List[str]) -> List[str]:
        """Get all permissions for user roles"""
        permissions = set()
        for role in user_roles:
            permissions.update(self.permissions.get(role, []))
        return list(permissions)

class AuditLogger:
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    def log_event(
        self,
        event_type: str,
        user_id: str,
        username: str,
        ip_address: str,
        resource: str,
        action: str,
        details: Dict[str, Any] = None,
        success: bool = True
    ):
        """Log security event"""
        log_data = {
            "event_type": event_type,
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "resource": resource,
            "action": action,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        
        if success:
            self.logger.info("Security event", **log_data)
        else:
            self.logger.warning("Security event failed", **log_data)
    
    def log_login_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool,
        failure_reason: str = None
    ):
        """Log login attempt"""
        self.log_event(
            event_type="login_attempt",
            user_id="",
            username=username,
            ip_address=ip_address,
            resource="auth",
            action="login",
            details={"failure_reason": failure_reason} if not success else None,
            success=success
        )
    
    def log_api_access(
        self,
        user_id: str,
        username: str,
        ip_address: str,
        endpoint: str,
        method: str,
        success: bool,
        error_message: str = None
    ):
        """Log API access"""
        self.log_event(
            event_type="api_access",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            resource=endpoint,
            action=method,
            details={"error_message": error_message} if not success else None,
            success=success
        )

# Global instances
security_manager = SecurityManager()
rbac_manager = RBACManager()
audit_logger = AuditLogger()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    try:
        payload = security_manager.verify_token(credentials.credentials)
        
        # In production, fetch user from database
        # For now, create mock user
        user = User(
            id=payload.get("sub", "unknown"),
            username=payload.get("username", "unknown"),
            email=payload.get("email", "unknown@example.com"),
            roles=payload.get("roles", ["viewer"]),
            permissions=rbac_manager.get_user_permissions(payload.get("roles", ["viewer"])),
            is_active=payload.get("is_active", True),
            last_login=datetime.fromisoformat(payload.get("last_login", datetime.utcnow().isoformat()))
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_security_context(
    user: User = Depends(get_current_user),
    request = None
) -> SecurityContext:
    """Get security context for request"""
    # Get request details
    ip_address = request.client.host if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
    session_id = request.headers.get("x-session-id", "unknown") if request else "unknown"
    
    return SecurityContext(
        user=user,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        permissions=user.permissions
    )

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_dependency(security_context: SecurityContext = Depends(get_security_context)):
        if not rbac_manager.has_permission(security_context.user.roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return security_context
    
    return permission_dependency

def require_role(role: str):
    """Decorator to require specific role"""
    def role_dependency(security_context: SecurityContext = Depends(get_security_context)):
        if role not in security_context.user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {role}"
            )
        return security_context
    
    return role_dependency

# API Key authentication
async def authenticate_api_key(api_key: str, db: AsyncSession) -> Optional[User]:
    """Authenticate using API key"""
    try:
        # In production, fetch from database
        # For now, mock authentication
        if api_key == "test-api-key":
            return User(
                id="api-user-1",
                username="api-user",
                email="api@example.com",
                roles=["api_user"],
                permissions=rbac_manager.get_user_permissions(["api_user"])
            )
        
        return None
        
    except Exception as e:
        logger.error(f"API key authentication error: {str(e)}")
        return None

# Security middleware functions
def validate_request_headers(request) -> bool:
    """Validate request headers for security"""
    # Check for required headers
    required_headers = ["user-agent"]
    
    for header in required_headers:
        if header not in request.headers:
            return False
    
    # Check for suspicious headers
    suspicious_headers = ["x-forwarded-for", "x-real-ip"]
    for header in suspicious_headers:
        if header in request.headers:
            # Validate header format
            value = request.headers[header]
            if not isinstance(value, str) or len(value) > 256:
                return False
    
    return True

def sanitize_input(data: Any) -> Any:
    """Sanitize input data to prevent injection"""
    if isinstance(data, str):
        # Remove potential XSS and SQL injection patterns
        import re
        data = re.sub(r'[<>"\']', '', data)
        data = re.sub(r'(javascript:|data:|vbscript:)', '', data, flags=re.IGNORECASE)
        return data
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data
