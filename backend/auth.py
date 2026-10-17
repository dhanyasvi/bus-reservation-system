"""Authentication and Role-Based Access Control (RBAC)."""
import time
import base64
import hmac
import hashlib
import json
import secrets
from typing import Optional
from fastapi import Header, HTTPException, Depends
import config

JWT_SECRET = getattr(config, "JWT_SECRET", "super-secret-jwt-key-for-bus-reservation-2026")

def create_jwt_token(payload: dict, expires_in_seconds: int = 86400) -> str:
    """Create a self-contained HMAC-SHA256 signed JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    
    body = payload.copy()
    body["exp"] = int(time.time()) + expires_in_seconds
    body["iat"] = int(time.time())
    body_b64 = base64.urlsafe_b64encode(json.dumps(body).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        JWT_SECRET.encode(),
        f"{header_b64}.{body_b64}".encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{body_b64}.{sig_b64}"

def verify_jwt_token(token: str) -> dict:
    """Verify and decode an HMAC-SHA256 JWT token."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(401, "Invalid token structure")
    
    header_b64, body_b64, sig_b64 = parts
    # Check signature
    expected_sig = hmac.new(
        JWT_SECRET.encode(),
        f"{header_b64}.{body_b64}".encode(),
        hashlib.sha256
    ).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
    
    if not secrets.compare_digest(sig_b64, expected_sig_b64):
        raise HTTPException(401, "Invalid token signature")
    
    # Decode body
    padded_body = body_b64 + "=" * ((4 - len(body_b64) % 4) % 4)
    try:
        body = json.loads(base64.urlsafe_b64decode(padded_body.encode()).decode())
    except Exception:
        raise HTTPException(401, "Corrupted token payload")
    
    if body.get("exp", 0) < time.time():
        raise HTTPException(401, "Token has expired")
    
    return body

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract authenticated passenger or admin from Authorization header."""
    if not authorization:
        # Allow guest access with default guest credentials
        return {"sub": "guest", "role": "GUEST", "name": "Guest Passenger"}
    
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        return verify_jwt_token(token)
    
    raise HTTPException(401, "Invalid authorization format. Use: Bearer <token>")

def require_admin(
    x_admin_key: Optional[str] = Header(default=""),
    authorization: Optional[str] = Header(None)
) -> dict:
    """Enforce administrator privileges via X-Admin-Key or Admin Bearer Token."""
    # 1. Check X-Admin-Key
    if config.ADMIN_API_KEY and x_admin_key and secrets.compare_digest(x_admin_key, config.ADMIN_API_KEY):
        return {"role": "ADMIN", "auth_method": "x_admin_key"}
    
    # 2. Check Admin Bearer token
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            payload = verify_jwt_token(parts[1])
            if payload.get("role") == "ADMIN":
                return payload
    
    raise HTTPException(401, "Administrator access required. Provide valid X-Admin-Key or Admin token.")
