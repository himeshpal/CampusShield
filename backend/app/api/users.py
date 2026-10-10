from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession, client_ip
from app.core.security import hash_password
from app.models import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: AdminUser, request: Request, db: DbSession) -> User:
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")
    user = User(
        email=email,
        full_name=body.full_name,
        role=body.role,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        "user.created",
        user=admin,
        entity_type="user",
        entity_id=user.id,
        details={"email": email, "role": body.role},
        ip_address=client_ip(request),
    )
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, body: UserUpdate, admin: AdminUser, request: Request, db: DbSession
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    changes = body.model_dump(exclude_unset=True)
    locks_self_out = changes.get("is_active") is False or changes.get("role") == "auditor"
    if user.id == admin.id and locks_self_out:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot demote or disable yourself")
    for field, value in changes.items():
        setattr(user, field, value)
    audit.record(
        db,
        "user.updated",
        user=admin,
        entity_type="user",
        entity_id=user.id,
        details=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: AdminUser, request: Request, db: DbSession) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete yourself")
    email = user.email
    db.delete(user)
    try:
        db.flush()
    except IntegrityError:
        # referenced by scans/checklist entries etc.: keep the history, disable instead
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This user has recorded activity. Disable them instead."
        ) from None
    audit.record(
        db,
        "user.deleted",
        user=admin,
        entity_type="user",
        entity_id=user_id,
        details={"email": email},
        ip_address=client_ip(request),
    )
    db.commit()
