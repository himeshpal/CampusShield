import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]


def client_ip(request: Request) -> str | None:
    # Requests arrive through the Next.js proxy, which sets X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_user(request: Request, db: DbSession) -> User:
    user = user_from_token(db, session_token(request))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


def session_token(request: Request) -> str | None:
    token = request.cookies.get(get_settings().session_cookie)
    auth_header = request.headers.get("authorization", "")
    if not token and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    return token


def user_from_token(db: Session, token: str | None) -> User | None:
    """The active user a token belongs to, or None (invalid, expired, revoked, disabled)."""
    payload = decode_access_token(token) if token else None
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active or payload.get("ver", 0) != user.token_version:
        return None
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_service_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Machine-to-machine auth for n8n (scheduled scans, delivery callbacks)."""
    if not x_api_key or not secrets.compare_digest(x_api_key, get_settings().service_api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid service key")
