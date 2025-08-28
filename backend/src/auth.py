"""
Authentication and security middleware for the Dashly API.
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Simple API key authentication for MVP
security = HTTPBearer(auto_error=False)

class SecurityConfig:
    """Security configuration for authentication."""
    
    # Require API key to be set explicitly - no default for security
    API_KEY = os.getenv("DASHLY_API_KEY")
    REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    
    @classmethod
    def validate_config(cls):
        """Validate security configuration on startup."""
        if cls.REQUIRE_AUTH and not cls.API_KEY:
            raise ValueError(
                "DASHLY_API_KEY environment variable must be set when authentication is required. "
                "Set REQUIRE_AUTH=false only for development/testing."
            )
        
        if cls.API_KEY and len(cls.API_KEY) < 16:
            raise ValueError("API key must be at least 16 characters long for security")
        
        # Warn about insecure configurations
        if not cls.REQUIRE_AUTH:
            logger.warning("⚠️  Authentication is DISABLED - this should only be used for development!")
        
        if cls.API_KEY and cls.API_KEY in ["dashly-demo-key-2024", "demo", "test", "dev"]:
            raise ValueError("Default or weak API key detected. Please use a secure, randomly generated key.")

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """
    Verify API key for authentication.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        bool: True if authenticated
        
    Raises:
        HTTPException: If authentication fails and is required
    """
    # For MVP demo mode, authentication is optional
    if not SecurityConfig.REQUIRE_AUTH:
        return True
    
    if not credentials:
        logger.warning("Missing authentication credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != SecurityConfig.API_KEY:
        # Log security event without exposing key content
        logger.warning("Invalid API key authentication attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add comprehensive security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Enhanced Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=()"
        )
        
        # For HTTPS in production
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        return response