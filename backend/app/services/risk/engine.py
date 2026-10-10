"""Pure risk scoring: no database, no network. Same inputs -> same score and breakdown.

The breakdown lists every point with the evidence behind it, so any score shown in the
UI or the PDF report can be traced back to concrete findings (the "explainable" goal).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from app.services.risk import rules
from app.services.risk.versions import product_matches, version_matches


class CveRule(Protocol):
    cve_id: str
    product: str
    version_spec: str
    cvss: float
    summary: str


@dataclass
class PortEvidence:
    port: int
    protocol: str = "tcp"
    service: str | None = None
    product: str | None = None
    version: str | None = None
    scripts: dict[str, str] = field(default_factory=dict)
    version_scan_id: int | None = None  # scan that identified product/version
    script_scan_id: int | None = None  # scan whose NSE scripts produced `scripts`


@dataclass
class AssetContext:
    status: str  # registered | unregistered | retired
    criteria: tuple[int, int, int, int]  # sensitivity, dependency, users, replaceability
    baseline_ports: Sequence[int] = ()
    # checklist control label -> yes | no | na | unknown
    controls: dict[str, str] = field(default_factory=dict)


@dataclass
class Item:
    kind: str  # risky_port | cve | end_of_life | misconfiguration | baseline_drift | ...
    label: str
    points: int
    severity: str
    port: int | None = None
    cve_id: str | None = None
    detail: str | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Component:
    key: str
    label: str
    cap: int
    items: list[Item] = field(default_factory=list)

    @property
    def uncapped(self) -> int:
        return sum(i.points for i in self.items)

    @property
    def points(self) -> int:
        return min(self.cap, self.uncapped)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "points": self.points,
            "uncapped": self.uncapped,
            "cap": self.cap,
            "items": [i.as_dict() for i in self.items],
        }


@dataclass
class RiskResult:
    score: float
    band: str
    raw: int
    multiplier: float
    criticality: int
    components: list[Component]

    @property
    def findings(self) -> list[Item]:
        """Concrete problems (excludes checklist gaps and zero-point observations)."""
        return [i for c in self.components if c.key != "controls" for i in c.items if i.points]

    def breakdown(self) -> dict:
        parts = " + ".join(str(c.points) for c in self.components)
        return {
            "model_version": rules.MODEL_VERSION,
            "score": self.score,
            "band": self.band,
            "raw": self.raw,
            "criticality": self.criticality,
            "multiplier": self.multiplier,
            "formula": f"min(100, ({parts}) x {self.multiplier}) = {self.score:g}",
            "components": [c.as_dict() for c in self.components],
        }


def _exposure_severity(points: int) -> str:
    return "high" if points >= 12 else "medium" if points >= 8 else "low" if points else "info"


def _exposure(ports: Sequence[PortEvidence]) -> Component:
    component = Component("exposure", "Network exposure", rules.EXPOSURE_CAP)
    for p in ports:
        service = (p.service or rules.PORT_WEIGHTS.get(p.port) or "").lower()
        if service.startswith("ssl/"):  # e.g. ssl/http -> encrypted web
            service = "https"
        points, label = rules.SERVICE_WEIGHTS.get(
            service, (rules.OTHER_PORT_POINTS, f"Open port ({p.service or 'unknown service'})")
        )
        component.items.append(
            Item(
                "risky_port",
                f"{label} ({p.port}/{p.protocol})",
                points,
                _exposure_severity(points),
                port=p.port,
            )  # fmt: skip
        )
    return component


def _vulnerabilities(ports: Sequence[PortEvidence], cves: Sequence[CveRule]) -> Component:
    component = Component("vulnerabilities", "Known vulnerabilities", rules.VULNERABILITY_CAP)
    for p in ports:
        software = " ".join(filter(None, [p.product, p.version])) or None
        seen_in = f" (identified in scan #{p.version_scan_id})" if p.version_scan_id else ""
        for cve in cves:
            if product_matches(p.product, cve.product) and version_matches(
                p.version, cve.version_spec
            ):
                component.items.append(
                    Item(
                        "cve",
                        f"{cve.cve_id} in {software} (CVSS {cve.cvss})",
                        rules.cvss_points(cve.cvss),
                        rules.cvss_severity(cve.cvss),
                        port=p.port,
                        cve_id=cve.cve_id,
                        detail=cve.summary + seen_in,
                    )  # fmt: skip
                )
        for eol in rules.END_OF_LIFE:
            if product_matches(p.product, eol["product"]) and version_matches(
                p.version, eol["version_spec"]
            ):
                component.items.append(
                    Item(
                        "end_of_life",
                        f"{eol['title']} ({software})",
                        eol["points"],
                        "high",
                        port=p.port,
                        detail=eol["detail"] + seen_in,
                    )  # fmt: skip
                )
        for rule in rules.SCRIPT_FINDINGS:
            output = p.scripts.get(rule["script"], "")
            if rule["contains"] in output:
                source = f" (NSE {rule['script']}, scan #{p.script_scan_id})"
                component.items.append(
                    Item(
                        "misconfiguration",
                        f"{rule['title']} ({p.port}/{p.protocol})",
                        rule["points"],
                        "high",
                        port=p.port,
                        detail=rule["detail"] + source,
                    )  # fmt: skip
                )
    return component


def _drift(ports: Sequence[PortEvidence], ctx: AssetContext) -> Component:
    component = Component("drift", "Unexpected open ports", rules.DRIFT_CAP)
    if ctx.status != "registered":  # no approved baseline for an unknown device
        return component
    baseline = set(ctx.baseline_ports)
    for p in ports:
        if p.port not in baseline:
            component.items.append(
                Item(
                    "baseline_drift",
                    f"Port {p.port}/{p.protocol} open but not in the baseline",
                    rules.DRIFT_POINTS_PER_PORT,
                    "medium",
                    port=p.port,
                )  # fmt: skip
            )
    return component


def _controls(ctx: AssetContext) -> Component:
    component = Component("controls", "Missing security controls", rules.CONTROLS_CAP)
    for label, status in ctx.controls.items():
        if status in ("no", "unknown"):
            text = f"{label}: not in place" if status == "no" else f"{label}: not confirmed"
            component.items.append(
                Item(
                    "control_gap", text, rules.CONTROL_POINTS, "medium" if status == "no" else "low"
                )  # fmt: skip
            )
    return component


def _inventory(ctx: AssetContext) -> Component:
    component = Component("inventory", "Inventory status", rules.INVENTORY_POINTS)
    if ctx.status == "unregistered":
        component.items.append(
            Item(
                "unregistered",
                "Device is not registered (no owner, no approved services)",
                rules.INVENTORY_POINTS,
                "high",
            )  # fmt: skip
        )
    return component


def score_asset(
    ports: Sequence[PortEvidence], ctx: AssetContext, cves: Sequence[CveRule]
) -> RiskResult:
    components = [
        _exposure(ports),
        _vulnerabilities(ports, cves),
        _drift(ports, ctx),
        _controls(ctx),
        _inventory(ctx),
    ]
    raw = sum(c.points for c in components)
    criticality = sum(ctx.criteria)
    multiplier = rules.multiplier_for(criticality)
    score = round(min(100.0, raw * multiplier), 1)
    return RiskResult(
        score=score,
        band=rules.band_for(score),
        raw=raw,
        multiplier=multiplier,
        criticality=criticality,
        components=components,
    )
