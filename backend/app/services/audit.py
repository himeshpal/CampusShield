from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    action: str,
    *,
    user: User | None = None,
    actor: str | None = None,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add an audit entry to the session. The caller commits with its own change."""
    entry = AuditLog(
        user_id=user.id if user else None,
        actor=actor or (user.email if user else "system"),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
