from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import AuditLog
from app.schemas.audit import AuditPage

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=AuditPage)
def list_audit_log(
    _: CurrentUser,
    db: DbSession,
    action: str | None = Query(default=None, description="Prefix filter, e.g. 'auth.'"),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditPage:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action.startswith(action))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).offset(offset)
    )
    return AuditPage(items=list(items), total=total)
