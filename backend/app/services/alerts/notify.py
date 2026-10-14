"""Hand alerts to n8n, which delivers them (Telegram, email) and reports back.

The backend only knows one webhook: routing, formatting per channel and retries live in
the n8n workflow (n8n/campusshield-alerts.json), so channels can change without code.
The shared secret travels in a header and is checked by the workflow.
"""

import logging
from collections.abc import Callable, Sequence

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Alert, AppSetting, Asset, Scan
from app.models.base import utcnow
from app.services.alerts.detect import SEVERITIES

log = logging.getLogger(__name__)

MIN_SEVERITY_KEY = "alert_min_severity"
DEFAULT_MIN_SEVERITY = "medium"  # info / low changes are kept in the app, not pushed
CHANNELS_KEY = "notification_channels"  # last result reported per channel
TIMEOUT_SECONDS = 5


def _post(url: str, payload: dict, headers: dict[str, str]) -> tuple[bool, str | None]:
    try:
        res = httpx.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        return False, f"n8n not reachable: {exc.__class__.__name__}"
    if res.is_success:
        return True, None
    return False, f"n8n answered {res.status_code}: {res.text[:200]}"


# Swappable in tests (no network): (url, payload, headers) -> (ok, error)
post_webhook: Callable[[str, dict, dict[str, str]], tuple[bool, str | None]] = _post


def get_setting(db: Session, key: str, default):
    row = db.get(AppSetting, key)
    return row.value if row is not None else default


def set_setting(db: Session, key: str, value) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def min_severity(db: Session) -> str:
    value = get_setting(db, MIN_SEVERITY_KEY, DEFAULT_MIN_SEVERITY)
    return value if value in SEVERITIES else DEFAULT_MIN_SEVERITY


def _at_least(severity: str, floor: str) -> bool:
    return SEVERITIES.index(severity) >= SEVERITIES.index(floor)


def _alert_json(alert: Alert, asset: Asset | None, app_url: str) -> dict:
    return {
        "id": alert.id,
        "kind": alert.kind,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "asset_tag": asset.asset_tag if asset else None,
        "asset_name": asset.name if asset else None,
        "ip": alert.payload.get("ip"),
        "scan_id": alert.scan_id,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "url": f"{app_url}/alerts?focus={alert.id}",
    }


def build_event(
    db: Session, alerts: Sequence[Alert], scan: Scan | None, *, test: bool = False
) -> dict:
    settings = get_settings()
    app_url = settings.app_url.rstrip("/")
    assets = {
        a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_({x.asset_id for x in alerts})))
    }
    ordered = sorted(alerts, key=lambda a: (-SEVERITIES.index(a.severity), a.id))
    counts = {s: sum(a.severity == s for a in alerts) for s in reversed(SEVERITIES)}
    return {
        "event": "test" if test else "alerts.created",
        "source": settings.app_name,
        "test": test,
        "sent_at": utcnow().isoformat(),
        "app_url": app_url,
        "alerts_url": f"{app_url}/alerts",
        "scan": {
            "id": scan.id,
            "profile": scan.profile,
            "target": scan.target,
            "triggered_by": scan.triggered_by,
            "hosts_up": scan.hosts_up,
            "url": f"{app_url}/scans/{scan.id}",
        }
        if scan
        else None,
        "counts": {k: v for k, v in counts.items() if v},
        "highest": ordered[0].severity if ordered else None,
        "alerts": [_alert_json(a, assets.get(a.asset_id), app_url) for a in ordered],
    }


def send(db: Session, event: dict) -> tuple[str, str | None]:
    """POST an event to n8n. Returns (state, error); state is sent|failed|not_configured."""
    settings = get_settings()
    if not settings.n8n_webhook_url:
        return "not_configured", "N8N_WEBHOOK_URL is not set"
    headers = {
        "X-CampusShield-Event": event["event"],
        "X-CampusShield-Secret": settings.n8n_webhook_secret or "",
    }
    ok, error = post_webhook(settings.n8n_webhook_url, event, headers)
    if not ok:
        log.warning("alert webhook failed: %s", error)
    return ("sent" if ok else "failed"), error


def notify(db: Session, alerts: Sequence[Alert], scan: Scan | None = None) -> str | None:
    """Push the alerts that reach the severity threshold; record the outcome on each.
    The caller commits. Returns the webhook state, or None if nothing was due."""
    floor = min_severity(db)
    due = [a for a in alerts if _at_least(a.severity, floor)]
    for alert in alerts:
        if alert not in due:
            alert.delivery = {**(alert.delivery or {}), "webhook": "below_threshold"}
    if not due:
        return None
    state, error = send(db, build_event(db, due, scan))
    for alert in due:
        alert.delivery = {**(alert.delivery or {}), "webhook": state}
        alert.delivery_error = error
    return state


def record_delivery(
    db: Session,
    alert_ids: Sequence[int],
    channel: str,
    ok: bool,
    error: str | None,
    *,
    skipped: bool = False,
) -> int:
    """n8n's callback after trying one channel. The caller commits."""
    now = utcnow()
    result = {
        "ok": ok,
        "skipped": skipped,
        "at": now.isoformat(),
        "error": (error or None) and error[:500],
    }
    channels = dict(get_setting(db, CHANNELS_KEY, {}) or {})
    channels[channel] = result
    set_setting(db, CHANNELS_KEY, channels)
    alerts = db.scalars(select(Alert).where(Alert.id.in_(alert_ids))).all() if alert_ids else []
    for alert in alerts:
        delivery = dict(alert.delivery or {})
        delivery["channels"] = {**delivery.get("channels", {}), channel: result}
        alert.delivery = delivery
        if ok:
            alert.delivered_at = alert.delivered_at or now
        elif not skipped:
            alert.delivery_error = f"{channel}: {error or 'failed'}"[:2000]
    return len(alerts)


def channel_status(db: Session) -> dict[str, dict]:
    return dict(get_setting(db, CHANNELS_KEY, {}) or {})
