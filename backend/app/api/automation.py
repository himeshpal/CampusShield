"""Machine-to-machine endpoints for n8n and the Wazuh manager, authenticated with the
service API key (header X-API-Key), never with a user session."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Response, status

from app.api.deps import DbSession, require_service_key
from app.core.config import get_settings
from app.models import Alert
from app.schemas.alert import AutomationScan, DeliveryReport
from app.schemas.scan import ScanOut
from app.services import audit
from app.services import scans as scan_service
from app.services.alerts import notify as notifier
from app.services.alerts import wazuh
from app.services.scanner.scope import ScopeError

router = APIRouter(
    prefix="/automation",
    tags=["automation"],
    dependencies=[Depends(require_service_key)],
)


@router.post("/scans", response_model=ScanOut, status_code=status.HTTP_202_ACCEPTED)
def scheduled_scan(body: AutomationScan, db: DbSession) -> ScanOut:
    """Start a scan from an n8n schedule (shown as triggered by "n8n")."""
    subnets = get_settings().authorized_subnet_list
    target = body.target or (subnets[0] if subnets else "")
    try:
        scan = scan_service.start_scan(
            db, target=target, profile=body.profile, user=None, triggered_by="n8n"
        )
    except ScopeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    except scan_service.ScanConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    db.refresh(scan)
    out = ScanOut.model_validate(scan, from_attributes=True)
    out.command = scan.summary.get("command")
    return out


@router.post("/delivery", status_code=status.HTTP_204_NO_CONTENT)
def delivery_report(body: DeliveryReport, db: DbSession) -> Response:
    """n8n reports whether a channel (Telegram, email) delivered the alerts it was sent."""
    updated = notifier.record_delivery(
        db, body.alert_ids, body.channel, body.ok, body.error, skipped=body.skipped
    )
    if not body.ok and not body.skipped:
        audit.record(
            db, "alert.delivery_failed", actor="n8n",
            details={"channel": body.channel, "alerts": updated, "error": body.error},
        )  # fmt: skip
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _notify_later(alert_id: int) -> None:
    """After the response: Wazuh should not wait for n8n."""
    with scan_service.session_factory() as db:
        alert = db.get(Alert, alert_id)
        if alert is not None:
            notifier.notify(db, [alert])
            db.commit()


@router.post("/wazuh", status_code=status.HTTP_202_ACCEPTED)
def wazuh_alert(
    background: BackgroundTasks,
    db: DbSession,
    event: Annotated[dict[str, Any], Body()],
) -> dict:
    """One alert from the Wazuh manager (integration custom-campusshield)."""
    if not isinstance(event.get("rule"), dict) or not isinstance(event.get("agent"), dict):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Not a Wazuh alert")
    alert, created = wazuh.ingest(db, event)
    db.commit()
    if created:
        background.add_task(_notify_later, alert.id)
    return {"alert_id": alert.id, "created": created, "count": alert.payload.get("count", 1)}
