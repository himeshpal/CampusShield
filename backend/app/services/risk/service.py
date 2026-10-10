"""Database side of risk scoring: gather evidence, score, store history and findings."""

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Asset,
    ChecklistEntry,
    ChecklistItem,
    CveRef,
    Finding,
    RiskScore,
    Scan,
    ScanHost,
)
from app.services.risk import rules
from app.services.risk.engine import AssetContext, PortEvidence, RiskResult, score_asset

OBSERVATION_WINDOW = 20  # scans looked back through for version / script evidence


def seed_cve_refs(db: Session) -> int:
    """Load rules.CVE_REFERENCE into the cve_refs table (insert or update)."""
    changed = 0
    for ref in rules.CVE_REFERENCE:
        row = db.scalar(
            select(CveRef).where(CveRef.cve_id == ref["cve_id"], CveRef.product == ref["product"])
        )
        if row is None:
            row = CveRef(cve_id=ref["cve_id"], product=ref["product"])
            db.add(row)
        values = {**ref, "severity": rules.cvss_severity(ref["cvss"])}
        if any(getattr(row, k, None) != v for k, v in values.items()):
            for k, v in values.items():
                setattr(row, k, v)
            changed += 1
    db.commit()
    return changed


def gather_evidence(
    db: Session, asset_id: int, current_scan_id: int | None = None
) -> tuple[list[PortEvidence], ScanHost | None]:
    """Open ports from the latest scan that saw the asset, with versions and NSE output
    carried forward from earlier scans when the latest one did not collect them
    (a quick sweep has no version detection, but the port is still the same service).

    `current_scan_id` is the scan being finished right now: it is still "running" while
    its results are scored, so it must be included explicitly."""
    usable = Scan.status == "completed"
    if current_scan_id is not None:
        usable = or_(usable, Scan.id == current_scan_id)
    observations = list(
        db.scalars(
            select(ScanHost)
            .join(Scan, Scan.id == ScanHost.scan_id)
            .where(ScanHost.asset_id == asset_id, usable)
            .options(selectinload(ScanHost.ports))
            .order_by(ScanHost.scan_id.desc())
            .limit(OBSERVATION_WINDOW)
        )
    )
    if not observations:
        return [], None
    latest = observations[0]
    evidence = []
    for port in latest.ports:
        same_port = [
            (obs.scan_id, p)
            for obs in observations
            for p in obs.ports
            if p.port == port.port and p.protocol == port.protocol
        ]
        versioned = next(((sid, p) for sid, p in same_port if p.product), None)
        scripted = next(((sid, p) for sid, p in same_port if p.script_output), None)
        evidence.append(
            PortEvidence(
                port=port.port,
                protocol=port.protocol,
                service=(versioned[1].service if versioned else None) or port.service,
                product=versioned[1].product if versioned else None,
                version=versioned[1].version if versioned else None,
                scripts=scripted[1].script_output if scripted else {},
                version_scan_id=versioned[0] if versioned else None,
                script_scan_id=scripted[0] if scripted else None,
            )
        )
    return evidence, latest


def controls_for(db: Session, asset_id: int) -> dict[str, str]:
    items = db.scalars(select(ChecklistItem).order_by(ChecklistItem.sort_order)).all()
    entries = {
        e.item_id: e.status
        for e in db.scalars(select(ChecklistEntry).where(ChecklistEntry.asset_id == asset_id))
    }
    return {item.label: entries.get(item.id, "unknown") for item in items}


def compute(
    db: Session, asset: Asset, current_scan_id: int | None = None
) -> tuple[RiskResult, ScanHost | None]:
    ports, latest = gather_evidence(db, asset.id, current_scan_id)
    ctx = AssetContext(
        status=asset.status,
        criteria=(
            asset.data_sensitivity,
            asset.service_dependency,
            asset.users_affected,
            asset.replaceability,
        ),
        baseline_ports=asset.baseline_ports or [],
        controls=controls_for(db, asset.id),
    )
    cves = db.scalars(select(CveRef)).all()
    return score_asset(ports, ctx, cves), latest


def rescore(
    db: Session,
    asset: Asset,
    *,
    record_findings: bool = False,
    current_scan_id: int | None = None,
) -> RiskScore | None:
    """Score an asset and append to its history. Retired assets are not scored.
    With record_findings, the findings are also stored against the observation used."""
    if asset.status == "retired":
        return None
    result, latest = compute(db, asset, current_scan_id)
    row = RiskScore(
        asset_id=asset.id,
        scan_id=latest.scan_id if latest else None,
        score=result.score,
        band=result.band,
        breakdown=result.breakdown(),
    )
    db.add(row)
    if record_findings and latest is not None:
        db.execute(delete(Finding).where(Finding.scan_host_id == latest.id))
        for item in result.findings:
            db.add(
                Finding(
                    scan_host_id=latest.id,
                    asset_id=asset.id,
                    kind=item.kind,
                    severity=item.severity,
                    title=item.label,
                    detail=item.detail,
                    port=item.port,
                    cve_id=item.cve_id,
                    points=item.points,
                )
            )
    db.flush()
    return row


def score_scan(db: Session, scan: Scan) -> int:
    """After a scan is matched: rescore every asset it observed. The caller commits."""
    asset_ids = {h.asset_id for h in scan.hosts if h.asset_id}
    for asset in db.scalars(select(Asset).where(Asset.id.in_(asset_ids))):
        rescore(db, asset, record_findings=True, current_scan_id=scan.id)
    return len(asset_ids)


def latest_scores(db: Session, asset_ids: list[int]) -> dict[int, RiskScore]:
    if not asset_ids:
        return {}
    newest = (
        select(func.max(RiskScore.id))
        .where(RiskScore.asset_id.in_(asset_ids))
        .group_by(RiskScore.asset_id)
    )
    return {r.asset_id: r for r in db.scalars(select(RiskScore).where(RiskScore.id.in_(newest)))}


def rescore_outdated(db: Session) -> int:
    """At startup: score assets that have no score yet or were scored by an older model."""
    assets = db.scalars(select(Asset).where(Asset.status != "retired")).all()
    current = latest_scores(db, [a.id for a in assets])
    stale = [
        a
        for a in assets
        if a.id not in current
        or current[a.id].breakdown.get("model_version") != rules.MODEL_VERSION
    ]
    for asset in stale:
        rescore(db, asset, record_findings=True)
    db.commit()
    return len(stale)
