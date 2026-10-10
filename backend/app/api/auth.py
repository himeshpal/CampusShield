from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models import AuditLog, User
from app.models.base import as_utc, utcnow
from app.schemas.auth import LoginRequest, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _recent_failures(db: DbSession, email: str, user: User | None) -> int:
    """Failed logins for this email inside the lockout window, since the last success."""
    settings = get_settings()
    since = utcnow() - timedelta(minutes=settings.login_lockout_minutes)
    if user and user.last_login_at and as_utc(user.last_login_at) > since:
        since = as_utc(user.last_login_at)
    return db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "auth.login_failed",
            AuditLog.actor == email,
            AuditLog.created_at > since,
        )
    )


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> User:
    settings = get_settings()
    email = body.email.strip().lower()
    ip = client_ip(request)
    user = db.scalar(select(User).where(User.email == email))

    if _recent_failures(db, email, user) >= settings.login_max_failures:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {settings.login_lockout_minutes} minutes.",
        )

    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        audit.record(db, "auth.login_failed", actor=email, ip_address=ip)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    user.last_login_at = utcnow()
    audit.record(db, "auth.login", user=user, entity_type="user", entity_id=user.id, ip_address=ip)
    db.commit()

    response.set_cookie(
        settings.session_cookie,
        create_access_token(user.id, user.role),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser, request: Request, response: Response, db: DbSession) -> None:
    audit.record(db, "auth.logout", user=user, ip_address=client_ip(request))
    db.commit()
    response.delete_cookie(get_settings().session_cookie, path="/")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
