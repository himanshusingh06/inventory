from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import User


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "super_admin": {"*"},
    "store_manager": {
        "catalog:read",
        "catalog:write",
        "inventory:read",
        "inventory:write",
        "billing:read",
        "billing:write",
        "payments:read",
        "payments:write",
        "reports:read",
    },
    "inventory_manager": {"catalog:read", "inventory:read", "inventory:write", "reports:read"},
    "cashier": {"catalog:read", "inventory:read", "billing:read", "billing:write", "payments:read", "payments:write"},
    "accountant": {"billing:read", "payments:read", "payments:write", "reports:read"},
    "viewer": {"catalog:read", "inventory:read", "billing:read", "payments:read", "reports:read"},
}


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{settings.app_secret_key}:{password}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def create_token(user: User) -> str:
    payload = f"{user.id}:{int(datetime.utcnow().timestamp())}"
    signature = hmac.new(settings.app_secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def _decode_token(token: str) -> int:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, issued_at, signature = decoded.split(":", 2)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
    payload = f"{user_id}:{issued_at}"
    expected = hmac.new(settings.app_secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return int(user_id)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    user = db.get(User, _decode_token(authorization.split(" ", 1)[1]))
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="User is inactive or missing")
    return user


def require_permission(permission: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        allowed = ROLE_PERMISSIONS.get(user.role, set())
        if "*" not in allowed and permission not in allowed:
            raise HTTPException(status_code=403, detail="You do not have access to this action")
        return user

    return dependency
