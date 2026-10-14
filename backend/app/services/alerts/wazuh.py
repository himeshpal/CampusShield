"""Wazuh SIEM alerts -> CampusShield alerts.

The Wazuh manager forwards every alert of level 5+ (custom integration, see wazuh/).
Each one is tied to the asset whose IP the agent registered with, and the source IP of an
attack (e.g. SSH brute force) is looked up in the inventory too, so a scan finding and a
host event about the same device meet in one place. Repeats of the same rule on the same
host within a short window are merged into one alert with a counter instead of flooding.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Asset
from app.models.base import utcnow
from app.services.alerts.detect import UNRESOLVED
from app.services.alerts.notify import get_setting, set_setting

MERGE_WINDOW = timedelta(minutes=15)
STATUS_KEY = "wazuh_status"


def severity_for(level: int) -> str:
    """Wazuh rule levels (0-15) onto CampusShield severities."""
    if level >= 12:
        return "critical"
    if level >= 10:
        return "high"
    if level >= 7:
        return "medium"
    if level >= 5:
        return "low"
    return "info"


def _asset_by_ip(db: Session, ip: str | None) -> Asset | None:
    if not ip or ip == "any":
        return None
    return db.scalar(
        select(Asset).where(Asset.ip_address == ip, Asset.status != "retired").order_by(Asset.id)
    )


def _label(asset: Asset) -> str:
    return (
        f"{asset.asset_tag} {asset.name}" if asset.name else f"{asset.asset_tag} (unknown device)"
    )


def _details(event: dict, db: Session) -> tuple[str, dict]:
    rule, agent, data = event.get("rule", {}), event.get("agent", {}), event.get("data", {}) or {}
    parts, extra = [], {}
    syscheck = event.get("syscheck") or {}
    if syscheck.get("path"):
        parts.append(f"File {syscheck['path']} was {syscheck.get('event', 'changed')}.")
        extra["path"] = syscheck["path"]
    srcip = data.get("srcip")
    if srcip:
        source = _asset_by_ip(db, srcip)
        if source is None:
            who = " (not in the inventory)"
        elif source.status == "unregistered":
            who = f": {source.asset_tag}, an unregistered device"
        else:
            who = f": {source.asset_tag} {source.name or ''}".rstrip()
        parts.append(f"Source {srcip}{who}.")
        extra["srcip"] = srcip
        extra["source_asset_id"] = source.id if source else None
    user = data.get("srcuser") or data.get("dstuser")
    if user:
        parts.append(f"User: {user}.")
        extra["user"] = user
    log = (event.get("full_log") or "").strip()
    if log and not syscheck:
        excerpt = log[:240]
        parts.append(f"Log: {excerpt}" + ("" if excerpt.endswith((".", "!", "?")) else "."))
    parts.append(
        f"Wazuh rule {rule.get('id')} (level {rule.get('level')}) on agent {agent.get('name')}."
    )
    return " ".join(parts), extra


def ingest(db: Session, event: dict) -> tuple[Alert, bool]:
    """Store one Wazuh alert. Returns (alert, created); created is False when it was
    merged into a recent alert for the same rule and host. The caller commits."""
    rule, agent = event.get("rule") or {}, event.get("agent") or {}
    level = int(rule.get("level", 0))
    rule_id = str(rule.get("id", ""))
    asset = _asset_by_ip(db, agent.get("ip"))
    severity = severity_for(level)
    message, extra = _details(event, db)
    now = utcnow()
    _record_status(db, agent.get("name"), rule.get("description"))

    recent = db.scalars(
        select(Alert).where(
            Alert.kind == "wazuh",
            Alert.status.in_(UNRESOLVED),
            Alert.created_at >= now - MERGE_WINDOW,
            Alert.asset_id == asset.id if asset else Alert.asset_id.is_(None),
        )
    ).all()
    same = next(
        (a for a in recent if a.payload.get("rule_id") == rule_id
         and a.payload.get("agent", {}).get("name") == agent.get("name")),
        None,
    )  # fmt: skip
    if same is not None:
        payload = dict(same.payload)
        payload["count"] = payload.get("count", 1) + 1
        payload["last_at"] = now.isoformat()
        if extra.get("path"):  # e.g. passwd, shadow and group changed together
            paths = [p for p in payload.get("paths", [payload.get("path")]) if p]
            if extra["path"] not in paths:
                paths = [*paths, extra["path"]][:10]
            payload["paths"] = paths
            if len(paths) > 1:
                _, _, rest = message.partition(". ")
                message = f"Files changed: {', '.join(paths)}. {rest}"
        same.payload, same.message = payload, message
        return same, False

    where = _label(asset) if asset else agent.get("name") or "an unknown host"
    description = (rule.get("description") or "Wazuh alert").rstrip(".")
    alert = Alert(
        kind="wazuh",
        severity=severity,
        title=f"{description} on {where}"[:255],
        message=message,
        asset_id=asset.id if asset else None,
        payload={
            "asset_tag": asset.asset_tag if asset else None,
            "asset_name": asset.name if asset else None,
            "ip": asset.ip_address if asset else agent.get("ip"),
            "rule_id": rule_id,
            "level": level,
            "groups": rule.get("groups", []),
            "mitre": (rule.get("mitre") or {}).get("id", []),
            "agent": {k: agent.get(k) for k in ("id", "name", "ip")},
            "location": event.get("location"),
            "wazuh_id": event.get("id"),
            "count": 1,
            "first_at": now.isoformat(),
            "last_at": now.isoformat(),
            **extra,
        },
        status="open",
        delivery={},
    )
    db.add(alert)
    db.flush()
    return alert, True


def _record_status(db: Session, agent: str | None, description: str | None) -> None:
    status = dict(get_setting(db, STATUS_KEY, {}) or {})
    status.update(
        last_event_at=utcnow().isoformat(),
        last_agent=agent,
        last_rule=description,
        events=status.get("events", 0) + 1,
    )
    set_setting(db, STATUS_KEY, status)


def status(db: Session) -> dict | None:
    return get_setting(db, STATUS_KEY, None)
