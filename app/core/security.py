"""
Security Middleware for RepoDiscoverAI
Provides rate limiting, CORS, security headers, and authentication
"""

import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from collections import defaultdict

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings


# ============================================
# Rate Limiting
# ============================================

limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    "default": f"{settings.rate_limit_per_minute}/minute",
    "api_search": "30/minute",
    "api_trending": "60/minute",
    "api_collections": "100/minute",
    "auth_login": "5/minute",
    "auth_register": "3/minute",
}


# ============================================
# Security Headers Middleware
# ============================================

class SecurityHeadersMiddleware:
    """Add security headers to all responses"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                # Security headers
                headers.append((b"x-frame-options", b"SAMEORIGIN"))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-xss-protection", b"1; mode=block"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                headers.append((
                    b"content-security-policy",
                    b"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'self';"
                ))
                headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                headers.append((b"cache-control", b"no-store, no-cache, must-revalidate"))
                headers.append((b"pragma", b"no-cache"))
                
                message["headers"] = headers
            
            return await send(message)
        
        return await self.app(scope, receive, send_wrapper)


# ============================================
# API Key Authentication
# ============================================

class APIKeyManager:
    """Manage API keys for authentication"""
    
    def __init__(self):
        self.keys: Dict[str, Dict] = {}
        self.user_keys: Dict[int, Set[str]] = defaultdict(set)
    
    def generate_key(self, user_id: int, name: str, permissions: Dict = None, expires_days: int = None) -> str:
        """Generate a new API key"""
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        self.keys[key_hash] = {
            "user_id": user_id,
            "name": name,
            "permissions": permissions or {"read": True, "write": False},
            "rate_limit": 1000,
            "expires_at": expires_at,
            "last_used_at": None,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        self.user_keys[user_id].add(key_hash)
        
        return key
    
    async def validate_key(self, key: str) -> Optional[Dict]:
        """Validate an API key and return user info if valid"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        if key_hash not in self.keys:
            return None
        
        key_info = self.keys[key_hash]
        
        # Check if key is active
        if not key_info["is_active"]:
            return None
        
        # Check if key is expired
        if key_info["expires_at"] and datetime.utcnow() > key_info["expires_at"]:
            key_info["is_active"] = False
            return None
        
        # Update last used
        key_info["last_used_at"] = datetime.utcnow()
        
        return key_info
    
    def revoke_key(self, key: str) -> bool:
        """Revoke an API key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        if key_hash in self.keys:
            key_info = self.keys[key_hash]
            user_id = key_info["user_id"]
            self.keys[key_hash]["is_active"] = False
            self.user_keys[user_id].discard(key_hash)
            return True
        
        return False
    
    def get_user_keys(self, user_id: int) -> list:
        """Get all API keys for a user"""
        keys = []
        for key_hash in self.user_keys.get(user_id, set()):
            if key_hash in self.keys:
                key_info = self.keys[key_hash].copy()
                # Don't expose sensitive info
                key_info.pop("key_hash", None)
                keys.append(key_info)
        return keys


# Global API key manager
api_key_manager = APIKeyManager()


# ============================================
# Authentication Dependency
# ============================================

security = HTTPBearer(auto_error=False)


async def get_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    request: Request = None
) -> Optional[Dict]:
    """
    Dependency to validate API key from Authorization header.
    Returns None if no key provided (for public endpoints).
    Raises HTTPException if invalid key provided.
    """
    if credentials is None:
        return None
    
    key = credentials.credentials
    key_info = await api_key_manager.validate_key(key)
    
    if key_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return key_info


async def require_api_key(
    key_info: Optional[Dict] = None
) -> Dict:
    """Dependency to require valid API key"""
    if key_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return key_info


async def require_write_permission(
    key_info: Dict = None
) -> Dict:
    """Dependency to require write permission"""
    if key_info is None or not key_info.get("permissions", {}).get("write", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permission required",
        )
    return key_info


# ============================================
# Request Logging Middleware
# ============================================

class RequestLoggingMiddleware:
    """Log all requests for auditing and debugging"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.request_count = 0
        self.error_count = 0
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        start_time = time.time()
        self.request_count += 1
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration = time.time() - start_time
                
                if status_code >= 400:
                    self.error_count += 1
                
                # Log request (in production, use proper logging)
                print(f"[{datetime.utcnow().isoformat()}] "
                      f"{scope['method']} {scope['path']} - "
                      f"{status_code} - {duration:.3f}s")
            
            return await send(message)
        
        return await self.app(scope, receive, send_wrapper)


# ============================================
# Setup Function
# ============================================

def setup_security(app: FastAPI):
    """Configure all security middleware for the application"""
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    
    # Rate Limiting Middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    print("✅ Security middleware configured")
