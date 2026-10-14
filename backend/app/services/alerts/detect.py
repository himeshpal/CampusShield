"""Change detection: compare a finished scan with what was known before it.

Every alert is a *difference* between two observations, so a condition is reported once
(when it appears), not on every scan. Differences are only claimed where both scans could
have seen them: a port is "closed" only if this scan probed that port, and "opened" only
if the previous scan probed it too (a quick sweep covers ~35 ports, a standard audit
1-1024 plus campus services). When a condition clears, its open alert resolves itself.
"""

import ipaddress
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Alert, Asset, RiskScore, Scan, ScanHost
from app.models.base import utcnow
from app.services.matching import MatchSummary
from app.services.risk import rules
from app.services.risk.service import latest_scores
from app.services.scanner.profiles import covered_ports

SEVERITIES = ("info", "low", "medium", "high", "critical")
RISK_JUMP_POINTS = 10  # score rise that is worth an alert even without a band change
BAND_RANK = {name: i for i, (_, name) in enumerate(reversed(rules.BANDS))}
UNRESOLVED = ("open", "acknowledged")
PREVIOUS_SCANS = 50  # how far back to look for the last scan that covered an address


def _service(port: int, service: str | None) -> str:
    return (service or rules.PORT_WEIGHTS.get(port) or "unknown").lower()


def _port_severity(port: int, service: str, baseline: set[int], registered: bool) -> str:
    if registered and port in baseline:
        return "info"  # an approved service is back
    points = rules.SERVICE_WEIGHTS.get(service, (rules.OTHER_PORT_POINTS, ""))[0]
    return "high" if points >= 12 else "medium" if points >= 6 else "low"


def _label(asset: Asset) -> str:
    return (
        f"{asset.asset_tag} {asset.name}" if asset.name else f"{asset.asset_tag} (unknown device)"
    )


@dataclass
class Detection:
    created: list[Alert]
    resolved: list[Alert]


class _Detector:
    def __init__(self, db: Session, scan: Scan, before: dict[int, RiskScore]):
        self.db, self.scan, self.before = db, scan, before
        self.created: list[Alert] = []
        self.resolved: list[Alert] = []
        self.unresolved = list(
            db.scalars(
                select(Alert).where(Alert.status.in_(UNRESOLVED), Alert.asset_id.isnot(None))
            )
        )

    def add(self, kind: str, severity: str, asset: Asset, title: str, message: str, **payload):
        alert = Alert(
            kind=kind,
            severity=severity,
            title=title[:255],
            message=message,
            asset_id=asset.id,
            scan_id=self.scan.id,
            payload={
                "asset_tag": asset.asset_tag,
                "asset_name": asset.name,
                "ip": asset.ip_address,
                **payload,
            },  # fmt: skip
            status="open",
            delivery={},
        )
        self.db.add(alert)
        self.created.append(alert)

    def resolve(self, alert: Alert, reason: str) -> None:
        alert.status, alert.resolved_at, alert.resolution = "resolved", utcnow(), reason[:255]
        self.resolved.append(alert)

    def pending(self, kind: str, asset_id: int, port: int | None = None) -> list[Alert]:
        return [
            a
            for a in self.unresolved
            if a.kind == kind
            and a.asset_id == asset_id
            and a.status in UNRESOLVED
            and (port is None or a.payload.get("port") == port)
        ]

    # ------------------------------------------------------------------ checks
    def new_device(self, host: ScanHost, asset: Asset, conflict: bool) -> None:
        ports = ", ".join(
            f"{p.port}/{p.protocol} ({_service(p.port, p.service)})" for p in host.ports
        )
        found = f"open ports {ports}" if ports else "no open ports in the scanned range"
        vendor = f", vendor {host.mac_vendor}" if host.mac_vendor else ""
        mac = f"MAC {host.mac_address}{vendor}" if host.mac_address else "no MAC address"
        if conflict:
            owner = self.db.scalar(
                select(Asset).where(
                    Asset.ip_address == host.ip_address,
                    Asset.status == "registered",
                    Asset.id != asset.id,
                )
            )
            owner_text = _label(owner) if owner else "a registered asset"
            self.add(
                "new_device",
                "critical",
                asset,
                f"Different device on the address of {owner_text} ({host.ip_address})",
                f"A device with {mac} answered on {host.ip_address}, which is registered to "
                f"{owner_text}. It may have been replaced, cloned or spoofed; {found}.",
                ip_conflict=True,
                mac=host.mac_address,
            )
            return
        self.add(
            "new_device",
            "high",
            asset,
            f"Unregistered device at {host.ip_address}",
            f"A device that is not in the inventory answered on the network ({mac}) with "
            f"{found}. Register it with an owner or remove it from the network.",
            ip_conflict=False,
            mac=host.mac_address,
            ports=[p.port for p in host.ports],
        )

    def port_changes(
        self, host: ScanHost, asset: Asset, previous: ScanHost, cleared: set[int]
    ) -> None:
        now = {p.port: p for p in host.ports}
        before = {p.port: p for p in previous.ports}
        probed_now = covered_ports(self.scan.profile)
        probed_before = covered_ports(previous.scan.profile)
        baseline = set(asset.baseline_ports or [])
        registered = asset.status == "registered"
        since = f"scan #{previous.scan_id}"

        for port in sorted(set(now) - set(before)):
            if port not in probed_before:
                continue  # the earlier scan never looked at this port
            service = _service(port, now[port].service)
            weight = rules.SERVICE_WEIGHTS.get(service)
            what = weight[1] if weight else f"Open port ({service})"
            outside = registered and port not in baseline
            self.add(
                "port_opened",
                _port_severity(port, service, baseline, registered),
                asset,
                f"Port {port}/tcp ({service}) opened on {_label(asset)}",
                f"{what}. Closed in {since}, open in scan #{self.scan.id}"
                + (". Not in the approved baseline." if outside else "."),
                port=port,
                service=service,
                in_baseline=port in baseline,
            )
        for port in sorted(set(before) - set(now) - cleared):  # cleared: its alert resolved
            if port not in probed_now:
                continue  # this scan did not look at the port: no evidence it closed
            service = _service(port, before[port].service)
            self.add(
                "port_closed",
                "info",
                asset,
                f"Port {port}/tcp ({service}) closed on {_label(asset)}",
                f"Open in {since}, closed in scan #{self.scan.id}"
                + (
                    " (it is in the approved baseline: check the service)."
                    if port in baseline
                    else "."
                ),
                port=port,
                service=service,
                in_baseline=port in baseline,
            )

    def clear_port_alerts(self, host: ScanHost, asset: Asset) -> set[int]:
        """Resolve "port opened" alerts whose port is closed again; returns those ports."""
        open_now = {p.port for p in host.ports}
        probed = covered_ports(self.scan.profile)
        cleared = set()
        for alert in self.pending("port_opened", asset.id):
            port = alert.payload.get("port")
            if port in probed and port not in open_now:
                self.resolve(alert, f"Port closed again in scan #{self.scan.id}")
                cleared.add(port)
        return cleared

    def missing_hosts(self, observed: set[int]) -> None:
        network = ipaddress.ip_network(self.scan.target, strict=False)
        previous = list(
            self.db.scalars(
                select(Scan)
                .where(Scan.status == "completed", Scan.id < self.scan.id)
                .order_by(Scan.id.desc())
                .limit(PREVIOUS_SCANS)
            )
        )
        candidates = self.db.scalars(
            select(Asset).where(Asset.status == "registered", Asset.ip_address.isnot(None))
        )
        for asset in candidates:
            if asset.id in observed:
                continue
            ip = ipaddress.ip_address(asset.ip_address)
            if ip not in network:
                continue
            last = next(
                (s for s in previous if ip in ipaddress.ip_network(s.target, strict=False)), None
            )
            if last is None:
                continue
            was_seen = self.db.scalar(
                select(ScanHost.id).where(
                    ScanHost.scan_id == last.id, ScanHost.asset_id == asset.id
                )
            )
            if not was_seen or self.pending("host_missing", asset.id):
                continue
            criticality = (
                asset.data_sensitivity
                + asset.service_dependency
                + asset.users_affected
                + asset.replaceability
            )
            self.add(
                "host_missing",
                "high" if criticality >= 10 else "medium",
                asset,
                f"{_label(asset)} did not respond",
                f"Seen at {asset.ip_address} in scan #{last.id} but not in scan #{self.scan.id}. "
                "It may be switched off, disconnected, moved or failing.",
                last_scan_id=last.id,
            )

    def risk_jumps(self, assets: dict[int, Asset], skip: set[int]) -> None:
        after = latest_scores(self.db, list(assets))
        for asset_id, asset in assets.items():
            old, new = self.before.get(asset_id), after.get(asset_id)
            for alert in self.pending("risk_jump", asset_id):
                if new is not None and new.score <= alert.payload.get("before", -1):
                    self.resolve(alert, f"Risk back to {new.score:g} in scan #{self.scan.id}")
            if asset_id in skip or old is None or new is None or new.id == old.id:
                continue
            rise = round(new.score - old.score, 1)
            band_up = BAND_RANK[new.band] > BAND_RANK[old.band]
            if rise < RISK_JUMP_POINTS and not band_up:
                continue
            deltas = _component_deltas(old.breakdown, new.breakdown)
            reasons = ", ".join(f"{label} +{d}" for label, d in deltas[:3]) or "see the breakdown"
            bands = f"{old.band.title()} to {new.band.title()}" if band_up else new.band.title()
            self.add(
                "risk_jump",
                new.band if new.band in ("high", "critical") else "medium",
                asset,
                f"Risk of {_label(asset)} rose from {old.score:g} to {new.score:g} ({bands})",
                f"Main changes: {reasons} (points before the criticality multiplier).",
                before=old.score,
                after=new.score,
                band_before=old.band,
                band_after=new.band,
            )


def _component_deltas(old: dict, new: dict) -> list[tuple[str, int]]:
    before = {c["key"]: c["points"] for c in old.get("components", [])}
    deltas = [
        (c["label"], c["points"] - before.get(c["key"], 0)) for c in new.get("components", [])
    ]
    return sorted((d for d in deltas if d[1] > 0), key=lambda d: -d[1])


def _previous_observation(db: Session, asset_id: int, scan_id: int) -> ScanHost | None:
    return db.scalar(
        select(ScanHost)
        .join(Scan, Scan.id == ScanHost.scan_id)
        .where(ScanHost.asset_id == asset_id, Scan.status == "completed", Scan.id < scan_id)
        .options(selectinload(ScanHost.ports), selectinload(ScanHost.scan))
        .order_by(Scan.id.desc())
        .limit(1)
    )


def detect_changes(
    db: Session, scan: Scan, match: MatchSummary, before: dict[int, RiskScore]
) -> Detection:
    """Create alerts for what changed in `scan` (matched and scored, not yet committed).
    `before` holds each asset's latest score from before this scan was scored."""
    detector = _Detector(db, scan, before)
    hosts = [h for h in scan.hosts if h.asset_id]
    assets = {
        a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_([h.asset_id for h in hosts])))
    }
    new = set(match.new_devices)
    conflicts = set(match.ip_conflicts)

    for host in hosts:
        asset = assets[host.asset_id]
        if asset.id in new:
            detector.new_device(host, asset, conflict=asset.id in conflicts)
            continue
        for alert in detector.pending("host_missing", asset.id):
            detector.resolve(alert, f"Responded again in scan #{scan.id}")
        cleared = detector.clear_port_alerts(host, asset)
        previous = _previous_observation(db, asset.id, scan.id)
        if previous is not None:
            detector.port_changes(host, asset, previous, cleared)

    detector.missing_hosts(set(assets))
    detector.risk_jumps(assets, skip=new)
    db.flush()
    return Detection(created=detector.created, resolved=detector.resolved)


def resolve_for_asset(db: Session, asset: Asset, kinds: tuple[str, ...], reason: str) -> int:
    """Resolve an asset's open alerts of the given kinds (e.g. registered -> new_device)."""
    alerts = db.scalars(
        select(Alert).where(
            Alert.asset_id == asset.id, Alert.kind.in_(kinds), Alert.status.in_(UNRESOLVED)
        )
    ).all()
    for alert in alerts:
        alert.status, alert.resolved_at, alert.resolution = "resolved", utcnow(), reason[:255]
    return len(alerts)
