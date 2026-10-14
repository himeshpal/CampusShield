"""Change alerts: review, acknowledge, resolve, and the notification settings."""

from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.models import Alert, Asset, User
from app.models.base import utcnow
from app.schemas.alert import (
    AlertAsset,
    AlertKind,
    AlertOut,
    AlertPage,
    AlertStatus,
    AlertSummary,
    NotificationSettings,
    NotificationSettingsUpdate,
    ResolveBody,
    Severity,
    TestResult,
)
from app.services import audit
from app.services.alerts import notify as notifier
from app.services.alerts.detect import SEVERITIES, UNRESOLVED

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _out(db: Session, alerts: list[Alert]) -> list[AlertOut]:
    asset_ids = {a.asset_id for a in alerts if a.asset_id}
    user_ids = {u for a in alerts for u in (a.acknowledged_by_id, a.resolved_by_id) if u}
    assets = (
        {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(asset_ids)))}
        if asset_ids
        else {}
    )
    names = (
        {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    out = []
    for a in alerts:
        asset = assets.get(a.asset_id)
        out.append(
            AlertOut(
                id=a.id,
                kind=a.kind,
                severity=a.severity,
                title=a.title,
                message=a.message,
                status=a.status,
                asset=AlertAsset(
                    id=asset.id, asset_tag=asset.asset_tag, name=asset.name, status=asset.status
                )
                if asset
                else None,
                scan_id=a.scan_id,
                payload=a.payload or {},
                delivery=a.delivery or {},
                delivered_at=a.delivered_at,
                delivery_error=a.delivery_error,
                acknowledged_by=names.get(a.acknowledged_by_id),
                acknowledged_at=a.acknowledged_at,
                resolved_by=names.get(a.resolved_by_id),
                resolved_at=a.resolved_at,
                resolution=a.resolution,
                created_at=a.created_at,
            )
        )
    return out


def _get(db: Session, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    return alert


@router.get("", response_model=AlertPage)
def list_alerts(
    _: CurrentUser,
    db: DbSession,
    status_: Annotated[AlertStatus | None, Query(alias="status")] = None,
    unresolved: bool = Query(default=False, description="open + acknowledged"),
    kind: AlertKind | None = None,
    severity: Severity | None = None,
    asset_id: int | None = None,
    scan_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AlertPage:
    query = select(Alert)
    if status_:
        query = query.where(Alert.status == status_)
    if unresolved:
        query = query.where(Alert.status.in_(UNRESOLVED))
    for column, value in ((Alert.kind, kind), (Alert.severity, severity),
                          (Alert.asset_id, asset_id), (Alert.scan_id, scan_id)):  # fmt: skip
        if value is not None:
            query = query.where(column == value)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit).offset(offset)
    ).all()
    return AlertPage(items=_out(db, list(items)), total=total)


@router.get("/summary", response_model=AlertSummary)
def alert_summary(_: CurrentUser, db: DbSession) -> AlertSummary:
    by_status = dict(db.execute(select(Alert.status, func.count()).group_by(Alert.status)).all())
    unresolved = Alert.status.in_(UNRESOLVED)
    by_severity = dict(
        db.execute(
            select(Alert.severity, func.count()).where(unresolved).group_by(Alert.severity)
        ).all()
    )
    by_kind = dict(
        db.execute(select(Alert.kind, func.count()).where(unresolved).group_by(Alert.kind)).all()
    )
    return AlertSummary(
        open=by_status.get("open", 0),
        acknowledged=by_status.get("acknowledged", 0),
        resolved=by_status.get("resolved", 0),
        by_severity={s: by_severity.get(s, 0) for s in reversed(SEVERITIES)},
        by_kind=by_kind,
        latest_at=db.scalar(select(func.max(Alert.created_at))),
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge(alert_id: int, admin: AdminUser, request: Request, db: DbSession) -> AlertOut:
    alert = _get(db, alert_id)
    if alert.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Alert is already {alert.status}")
    alert.status, alert.acknowledged_by_id, alert.acknowledged_at = (
        "acknowledged",
        admin.id,
        utcnow(),
    )
    audit.record(
        db, "alert.acknowledged", user=admin, entity_type="alert", entity_id=alert.id,
        details={"title": alert.title}, ip_address=client_ip(request),
    )  # fmt: skip
    db.commit()
    return _out(db, [alert])[0]


@router.post("/acknowledge-all")
def acknowledge_all(admin: AdminUser, request: Request, db: DbSession) -> dict[str, int]:
    alerts = db.scalars(select(Alert).where(Alert.status == "open")).all()
    now = utcnow()
    for alert in alerts:
        alert.status, alert.acknowledged_by_id, alert.acknowledged_at = (
            "acknowledged",
            admin.id,
            now,
        )
    if alerts:
        audit.record(
            db, "alert.acknowledged", user=admin, entity_type="alert", entity_id="all",
            details={"count": len(alerts)}, ip_address=client_ip(request),
        )  # fmt: skip
    db.commit()
    return {"acknowledged": len(alerts)}


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve(
    alert_id: int, body: ResolveBody, admin: AdminUser, request: Request, db: DbSession
) -> AlertOut:
    alert = _get(db, alert_id)
    if alert.status == "resolved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Alert is already resolved")
    note = (body.note or "").strip()
    alert.status, alert.resolved_by_id, alert.resolved_at = "resolved", admin.id, utcnow()
    alert.resolution = note or f"Resolved by {admin.full_name}"
    audit.record(
        db, "alert.resolved", user=admin, entity_type="alert", entity_id=alert.id,
        details={"title": alert.title, "note": note or None}, ip_address=client_ip(request),
    )  # fmt: skip
    db.commit()
    return _out(db, [alert])[0]


@router.post("/{alert_id}/notify", response_model=TestResult)
def resend(alert_id: int, admin: AdminUser, db: DbSession) -> TestResult:
    """Send one alert to n8n again (e.g. after fixing the Telegram token)."""
    alert = _get(db, alert_id)
    state, error = notifier.send(db, notifier.build_event(db, [alert], None))
    alert.delivery = {**(alert.delivery or {}), "webhook": state}
    alert.delivery_error = error
    db.commit()
    return TestResult(state=state, error=error)


# ---------------------------------------------------------------------- settings
def _settings(db: Session) -> NotificationSettings:
    s = get_settings()
    url = s.n8n_webhook_url
    return NotificationSettings(
        min_severity=notifier.min_severity(db),
        webhook_configured=bool(url),
        webhook_host=urlparse(url).netloc if url else None,
        app_url=s.app_url,
        channels=notifier.channel_status(db),
    )


@router.get("/settings", response_model=NotificationSettings)
def notification_settings(_: CurrentUser, db: DbSession) -> NotificationSettings:
    return _settings(db)


@router.put("/settings", response_model=NotificationSettings)
def update_notification_settings(
    body: NotificationSettingsUpdate, admin: AdminUser, request: Request, db: DbSession
) -> NotificationSettings:
    before = notifier.min_severity(db)
    notifier.set_setting(db, notifier.MIN_SEVERITY_KEY, body.min_severity)
    if before != body.min_severity:
        audit.record(
            db, "settings.updated", user=admin, entity_type="setting",
            entity_id=notifier.MIN_SEVERITY_KEY,
            details={"from": before, "to": body.min_severity}, ip_address=client_ip(request),
        )  # fmt: skip
    db.commit()
    return _settings(db)


@router.post("/test", response_model=TestResult)
def send_test(admin: AdminUser, request: Request, db: DbSession) -> TestResult:
    """A sample alert through the whole pipeline: backend -> n8n -> Telegram / email."""
    sample = Alert(
        id=0,
        kind="port_opened",
        severity="high",
        title="Test alert: port 23/tcp (telnet) opened on CS-0000 Test device",
        message="This is a test from CampusShield Settings. No action is needed.",
        payload={"ip": "192.0.2.10"},
        created_at=utcnow(),
    )
    state, error = notifier.send(db, notifier.build_event(db, [sample], None, test=True))
    audit.record(
        db, "alert.test_sent", user=admin, details={"state": state, "error": error},
        ip_address=client_ip(request),
    )  # fmt: skip
    db.commit()
    return TestResult(state=state, error=error)
