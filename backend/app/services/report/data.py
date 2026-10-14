"""Collect everything the audit report shows into one point-in-time snapshot.

Kept separate from rendering so the numbers can be tested without producing a PDF, and
so the report reads the same stored scores and breakdowns the UI shows.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Alert, Asset, ChecklistEntry, ChecklistItem, Scan, User
from app.models.base import as_utc, utcnow
from app.services.report.recommendations import Recommendation, recommend
from app.services.risk import rules
from app.services.risk.service import gather_evidence, latest_scores
from app.services.risk.trend import TrendPoint, campus_trend

TYPE_LABELS = {
    "server": "Server",
    "workstation": "Workstation",
    "wifi_ap": "Wi-Fi access point",
    "iot_cctv": "CCTV camera",
    "iot_biometric": "Biometric device",
    "printer": "Printer",
    "network_device": "Network device",
    "other": "Other",
}
BAND_LABELS = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
VULN_KINDS = ("cve", "end_of_life", "misconfiguration")
CONTROL_STATES = ("yes", "no", "na", "unknown")


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else many or one + 's'}"


@dataclass
class PortRow:
    port: int
    protocol: str
    service: str | None
    software: str | None


@dataclass
class AssetReport:
    id: int
    tag: str
    name: str | None
    label: str  # "CS-0002 Department Website"
    asset_type: str
    status: str
    ip: str | None
    mac: str | None
    vendor: str | None
    department: str | None
    location: str | None
    owner: str | None
    criticality: int
    last_seen: datetime | None
    score: float | None = None
    band: str | None = None
    raw: int = 0
    multiplier: float = 1.0
    formula: str | None = None
    components: list[dict] = field(default_factory=list)
    ports: list[PortRow] = field(default_factory=list)
    controls: dict[str, str] = field(default_factory=dict)  # control label -> status

    @property
    def type_label(self) -> str:
        return TYPE_LABELS.get(self.asset_type, "Other")

    @property
    def display_name(self) -> str:
        return self.name or ("Unknown device" if self.status == "unregistered" else self.tag)

    @property
    def top_driver(self) -> str | None:
        scored = [c for c in self.components if c["points"]]
        return max(scored, key=lambda c: c["points"])["label"] if scored else None

    @property
    def findings(self) -> list[dict]:
        """Items with points, worst first (what the per-asset section lists)."""
        items = [
            {**i, "component": c["label"]}
            for c in self.components
            for i in c["items"]
            if i["points"]
        ]
        return sorted(items, key=lambda i: -i["points"])


@dataclass
class Vulnerability:
    asset: AssetReport
    kind: str
    title: str
    severity: str
    points: int
    port: int | None
    cve_id: str | None
    detail: str | None


@dataclass
class ControlCoverage:
    label: str
    counts: dict[str, int]  # yes / no / na / unknown

    @property
    def answered(self) -> int:
        return sum(v for k, v in self.counts.items() if k != "unknown")


@dataclass
class OpenAlert:
    kind: str
    severity: str
    status: str
    title: str
    message: str
    created_at: datetime
    count: int


@dataclass
class ScanInfo:
    id: int
    profile: str
    target: str
    finished_at: datetime
    hosts_up: int
    open_ports: int


@dataclass
class ReportData:
    title: str
    number: str
    institution: str
    generated_at: datetime
    generated_by: str
    include_details: bool
    scope: list[str]
    excluded: list[str]
    latest_scan: ScanInfo | None
    first_scan_at: datetime | None
    scans_completed: int
    counts: dict[str, int]  # registered / unregistered / retired
    by_type: dict[str, int]
    assets: list[AssetReport]  # riskiest first, unassessed last
    bands: dict[str, int]
    average: float | None
    drivers: list[dict]
    vulnerabilities: list[Vulnerability]
    controls: list[ControlCoverage]
    control_gaps: list[tuple[AssetReport, str]]
    recommendations: list[Recommendation]
    trend: list[TrendPoint]
    open_alerts: list["OpenAlert"] = field(default_factory=list)
    open_alerts_total: int = 0

    @property
    def assessed(self) -> list[AssetReport]:
        return [a for a in self.assets if a.score is not None]

    @property
    def unregistered(self) -> list[AssetReport]:
        return [a for a in self.assets if a.status == "unregistered"]

    @property
    def average_band(self) -> str | None:
        return rules.band_for(self.average) if self.average is not None else None

    @property
    def checklist_answered(self) -> int:
        return sum(c.answered for c in self.controls)

    @property
    def checklist_total(self) -> int:
        return sum(sum(c.counts.values()) for c in self.controls)

    @property
    def high_or_critical(self) -> int:
        return self.bands["high"] + self.bands["critical"]

    def summary(self) -> dict:
        """Headline numbers stored with the report (shown in the report history)."""
        return {
            "assets": self.counts["registered"],
            "unregistered": self.counts["unregistered"],
            "assessed": len(self.assessed),
            "average": self.average,
            "average_band": self.average_band,
            "bands": self.bands,
            "vulnerabilities": len(self.vulnerabilities),
            "recommendations": len(self.recommendations),
            "open_alerts": self.open_alerts_total,
            "checklist_answered": self.checklist_answered,
            "checklist_total": self.checklist_total,
            "latest_scan_id": self.latest_scan.id if self.latest_scan else None,
        }

    def narrative(self) -> list[str]:
        """Plain-language findings for the executive summary, written from the numbers."""
        if not self.assessed:
            return ["No device has been assessed yet: run a network scan before reporting."]
        n = len(self.assessed)
        lines = [
            f"{plural(n, 'device')} {'was' if n == 1 else 'were'} assessed. The average "
            f"risk score is {self.average:g}/100 ({BAND_LABELS[self.average_band]})."
        ]
        if self.high_or_critical:
            worst = self.assessed[0]
            lines.append(
                f"{self.high_or_critical} of {n} devices are rated High or Critical; the "
                f"riskiest is {worst.label} at {worst.score:g}/100, driven mainly by "
                f"{(worst.top_driver or 'its findings').lower()}."
            )
        else:
            lines.append("No device is rated High or Critical.")
        cves = sorted({v.cve_id for v in self.vulnerabilities if v.cve_id})
        if cves:
            more = ", ..." if len(cves) > 3 else ""
            lines.append(
                f"{plural(len(cves), 'known vulnerability', 'known vulnerabilities')} "
                f"({', '.join(cves[:3])}{more}) matched software versions found on the network."
            )
        if self.unregistered:
            ips = ", ".join(a.ip or a.tag for a in self.unregistered)
            k = len(self.unregistered)
            lines.append(
                f"{plural(k, 'unregistered device')} {'is' if k == 1 else 'are'} active on "
                f"the network ({ips}) with no owner or approved services."
            )
        if self.checklist_total:
            pct = round(100 * self.checklist_answered / self.checklist_total)
            missing = sum(c.counts["no"] for c in self.controls)
            gaps = (
                f"{plural(missing, 'control')} recorded as missing"
                if missing
                else "no gaps recorded yet"
            )
            lines.append(f"The security checklist is {pct}% complete, with {gaps}.")
        if self.open_alerts_total:
            urgent = sum(a.severity in ("high", "critical") for a in self.open_alerts)
            hosts = sum(a.kind == "wazuh" for a in self.open_alerts)
            n = self.open_alerts_total
            lines.append(
                f"{plural(n, 'alert')} {'is' if n == 1 else 'are'} unresolved"
                f" ({urgent} high or critical"
                + (f", {plural(hosts, 'host security event')} from Wazuh" if hosts else "")
                + ")."
            )
        return lines


def _software(product: str | None, version: str | None) -> str | None:
    return " ".join(filter(None, [product, version])) or None


def _asset_label(asset: Asset) -> str:
    if asset.name:
        return f"{asset.asset_tag} {asset.name}"
    return f"{asset.asset_tag} (unknown device)"


def _asset_report(
    db: Session, asset: Asset, score, items: list[ChecklistItem], entries: dict
) -> AssetReport:
    breakdown = score.breakdown if score else {}
    ports, _ = gather_evidence(db, asset.id)
    return AssetReport(
        id=asset.id,
        tag=asset.asset_tag,
        name=asset.name,
        label=_asset_label(asset),
        asset_type=asset.asset_type,
        status=asset.status,
        ip=asset.ip_address,
        mac=asset.mac_address,
        vendor=asset.mac_vendor,
        department=asset.department,
        location=asset.location,
        owner=asset.owner,
        criticality=asset.data_sensitivity
        + asset.service_dependency
        + asset.users_affected
        + asset.replaceability,
        last_seen=as_utc(asset.last_seen_at) if asset.last_seen_at else None,
        score=score.score if score else None,
        band=score.band if score else None,
        raw=breakdown.get("raw", 0),
        multiplier=breakdown.get("multiplier", 1.0),
        formula=breakdown.get("formula"),
        components=breakdown.get("components", []),
        ports=[
            PortRow(p.port, p.protocol, p.service, _software(p.product, p.version)) for p in ports
        ],
        # only registered assets have a checklist (unregistered ones have no owner)
        controls={
            i.label: entries.get((asset.id, i.id), "unknown")
            for i in items
            if asset.status == "registered"
        },
    )


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
MAX_ALERTS_LISTED = 25


def _open_alerts(db: Session) -> dict:
    """Unresolved alerts (scan changes and Wazuh host events), most severe first."""
    rows = db.scalars(select(Alert).where(Alert.status.in_(("open", "acknowledged")))).all()
    rows = sorted(rows, key=lambda a: (SEVERITY_RANK.get(a.severity, 9), -a.id))
    return {
        "open_alerts_total": len(rows),
        "open_alerts": [
            OpenAlert(
                kind=a.kind,
                severity=a.severity,
                status=a.status,
                title=a.title,
                message=a.message,
                created_at=as_utc(a.created_at),
                count=(a.payload or {}).get("count", 1),
            )
            for a in rows[:MAX_ALERTS_LISTED]
        ],
    }


def collect(
    db: Session,
    *,
    title: str,
    number: str,
    generated_by: User | None,
    include_details: bool = True,
) -> ReportData:
    settings = get_settings()
    assets = list(db.scalars(select(Asset).where(Asset.status != "retired").order_by(Asset.id)))
    scores = latest_scores(db, [a.id for a in assets])
    items = list(db.scalars(select(ChecklistItem).order_by(ChecklistItem.sort_order)))
    entries = {(e.asset_id, e.item_id): e.status for e in db.scalars(select(ChecklistEntry))}

    rows = [_asset_report(db, a, scores.get(a.id), items, entries) for a in assets]
    rows.sort(key=lambda a: (a.score is None, -(a.score or 0), a.tag))
    assessed = [a for a in rows if a.score is not None]

    bands = {name: 0 for _, name in reversed(rules.BANDS)}
    totals: dict[str, list] = {}
    for a in assessed:
        bands[a.band] += 1
        for c in a.components:
            totals.setdefault(c["key"], [c["label"], 0])[1] += c["points"]
    grand = sum(p for _, p in totals.values()) or 1
    drivers = sorted(
        (
            {"key": k, "label": label, "points": pts, "share": pts / grand}
            for k, (label, pts) in totals.items()
            if pts
        ),
        key=lambda d: -d["points"],
    )

    vulnerabilities = sorted(
        (
            Vulnerability(
                asset=a,
                kind=i["kind"],
                title=i["label"],
                severity=i.get("severity", "high"),
                points=i["points"],
                port=i.get("port"),
                cve_id=i.get("cve_id"),
                detail=i.get("detail"),
            )
            for a in assessed
            for c in a.components
            for i in c["items"]
            if i["kind"] in VULN_KINDS
        ),
        key=lambda v: (-v.points, v.asset.tag),
    )

    registered = [a for a in rows if a.status == "registered"]
    controls, gaps = [], []
    for item in items:
        counts = Counter(a.controls.get(item.label, "unknown") for a in registered)
        controls.append(ControlCoverage(item.label, {k: counts[k] for k in CONTROL_STATES}))
        gaps += [(a, item.label) for a in registered if a.controls.get(item.label) == "no"]

    completed = select(Scan).where(Scan.status == "completed")
    latest = db.scalar(completed.order_by(Scan.finished_at.desc(), Scan.id.desc()).limit(1))
    first_at = db.scalar(select(func.min(Scan.finished_at)).where(Scan.status == "completed"))
    counts = dict(db.execute(select(Asset.status, func.count()).group_by(Asset.status)).all())

    return ReportData(
        title=title,
        number=number,
        institution=settings.institution_name,
        generated_at=utcnow(),
        generated_by=generated_by.full_name if generated_by else "system",
        include_details=include_details,
        scope=settings.authorized_subnet_list,
        excluded=settings.scan_exclude_list,
        latest_scan=ScanInfo(
            id=latest.id,
            profile=latest.profile,
            target=latest.target,
            finished_at=as_utc(latest.finished_at),
            hosts_up=latest.hosts_up,
            open_ports=(latest.summary or {}).get("open_ports", 0),
        )
        if latest and latest.finished_at
        else None,
        first_scan_at=as_utc(first_at) if first_at else None,
        scans_completed=db.scalar(select(func.count()).select_from(completed.subquery())) or 0,
        counts={k: counts.get(k, 0) for k in ("registered", "unregistered", "retired")},
        by_type=dict(Counter(a.asset_type for a in registered).most_common()),
        assets=rows,
        bands=bands,
        average=round(sum(a.score for a in assessed) / len(assessed), 1) if assessed else None,
        drivers=drivers,
        vulnerabilities=vulnerabilities,
        controls=controls,
        control_gaps=gaps,
        recommendations=recommend(assessed),
        trend=campus_trend(db),
        **_open_alerts(db),
    )
