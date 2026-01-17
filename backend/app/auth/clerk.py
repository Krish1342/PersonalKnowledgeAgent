"""
Clerk JWT verification middleware for FastAPI.
"""

from typing import Optional, Callable
from functools import wraps
import httpx
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel

from app.config import settings


class ClerkUser(BaseModel):
    """Authenticated Clerk user."""
    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None


class ClerkAuth:
    """Clerk authentication handler for FastAPI."""
    
    def __init__(self):
        self._jwks_client: Optional[PyJWKClient] = None
        self._clerk_publishable_key = getattr(settings, 'CLERK_PUBLISHABLE_KEY', None)
        self._clerk_secret_key = getattr(settings, 'CLERK_SECRET_KEY', None)
    
    @property
    def is_enabled(self) -> bool:
        """Check if Clerk is configured."""
        return bool(self._clerk_secret_key and self._clerk_publishable_key)
    
    def _get_jwks_client(self) -> PyJWKClient:
        """Get JWKS client for token verification."""
        if self._jwks_client is None:
            # Clerk's JWKS endpoint
            jwks_url = f"https://{self._get_clerk_domain()}/.well-known/jwks.json"
            self._jwks_client = PyJWKClient(jwks_url)
        return self._jwks_client
    
    def _get_clerk_domain(self) -> str:
        """Extract Clerk domain from publishable key."""
        # Publishable key format: pk_test_<domain>
        if self._clerk_publishable_key:
            parts = self._clerk_publishable_key.split('_')
            if len(parts) >= 3:
                return parts[2]
        return "clerk.accounts.dev"
    
    async def verify_token(self, token: str) -> Optional[ClerkUser]:
        """Verify Clerk JWT token and return user info."""
        if not self.is_enabled:
            return None
        
        try:
            # Get signing key
            jwks_client = self._get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._clerk_publishable_key,
            )
            
            return ClerkUser(
                user_id=payload.get("sub", ""),
                email=payload.get("email"),
                username=payload.get("username"),
                first_name=payload.get("first_name"),
                last_name=payload.get("last_name"),
                image_url=payload.get("image_url"),
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    async def get_user_from_request(self, request: Request) -> Optional[ClerkUser]:
        """Extract and verify user from request."""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        return await self.verify_token(token)


# Singleton
_clerk_auth: Optional[ClerkAuth] = None


def get_clerk_auth() -> ClerkAuth:
    """Get singleton ClerkAuth instance."""
    global _clerk_auth
    if _clerk_auth is None:
        _clerk_auth = ClerkAuth()
    return _clerk_auth


# FastAPI dependencies
security = HTTPBearer(auto_error=False)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[ClerkUser]:
    """
    Dependency that optionally extracts user from token.
    Returns None if no token or Clerk not configured.
    """
    clerk = get_clerk_auth()
    
    if not clerk.is_enabled:
        return None
    
    if not credentials:
        return None
    
    return await clerk.verify_token(credentials.credentials)


async def get_required_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> ClerkUser:
    """
    Dependency that requires authenticated user.
    Raises 401 if not authenticated.
    """
    clerk = get_clerk_auth()
    
    if not clerk.is_enabled:
        # Return anonymous user when Clerk is not configured
        return ClerkUser(user_id="anonymous")
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = await clerk.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    return user


def get_user_id(user: Optional[ClerkUser]) -> Optional[str]:
    """Extract user ID from ClerkUser, handling anonymous users."""
    if user is None:
        return None
    if user.user_id == "anonymous":
        return None
    return user.user_id
