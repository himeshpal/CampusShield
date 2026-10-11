from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import Asset, ChecklistItem, CveRef
from app.schemas.risk import RiskDriver, RiskModel, RiskSummary, TopAsset
from app.services.risk import rules
from app.services.risk.service import latest_scores

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/summary", response_model=RiskSummary)
def risk_summary(_: CurrentUser, db: DbSession) -> RiskSummary:
    assets = db.scalars(select(Asset).where(Asset.status != "retired")).all()
    scores = latest_scores(db, [a.id for a in assets])
    bands = {name: 0 for _, name in rules.BANDS}
    for score in scores.values():
        bands[score.band] += 1
    ranked = sorted(
        (a for a in assets if a.id in scores), key=lambda a: scores[a.id].score, reverse=True
    )
    # what the campus risk is made of: points per component across all assets
    totals: dict[str, list] = {}
    for score in scores.values():
        for c in score.breakdown.get("components", []):
            totals.setdefault(c["key"], [c["label"], 0])[1] += c["points"]
    grand = sum(points for _, points in totals.values()) or 1
    drivers = sorted(
        (
            RiskDriver(key=k, label=label, points=pts, share=round(pts / grand, 3))
            for k, (label, pts) in totals.items()
        ),
        key=lambda d: -d.points,
    )
    return RiskSummary(
        drivers=drivers,
        bands=bands,
        assessed=len(scores),
        average=round(sum(s.score for s in scores.values()) / len(scores), 1) if scores else None,
        top=[
            TopAsset(
                id=a.id,
                asset_tag=a.asset_tag,
                name=a.name,
                status=a.status,
                score=scores[a.id].score,
                band=scores[a.id].band,
            )
            for a in ranked[:5]
        ],
    )


@router.get("/model", response_model=RiskModel)
def risk_model(_: CurrentUser, db: DbSession) -> RiskModel:
    """The complete scoring model, so every number in the UI can be explained."""
    controls = db.scalar(select(func.count(ChecklistItem.id))) or 0
    return RiskModel(
        version=rules.MODEL_VERSION,
        formula=(
            "score = min(100, (exposure + vulnerabilities + drift + controls + inventory)"
            " x criticality multiplier)"
        ),
        components=[
            {"key": "exposure", "label": "Network exposure", "cap": rules.EXPOSURE_CAP},
            {
                "key": "vulnerabilities",
                "label": "Known vulnerabilities",
                "cap": rules.VULNERABILITY_CAP,
            },
            {
                "key": "drift",
                "label": "Unexpected open ports",
                "cap": rules.DRIFT_CAP,
                "rule": f"{rules.DRIFT_POINTS_PER_PORT} per port outside the baseline",
            },
            {
                "key": "controls",
                "label": "Missing security controls",
                "cap": rules.CONTROL_POINTS * controls,
                "rule": f"{rules.CONTROL_POINTS} per checklist control not confirmed "
                f"({controls} controls)",
            },
            {
                "key": "inventory",
                "label": "Inventory status",
                "cap": rules.INVENTORY_POINTS,
                "rule": "unregistered device",
            },
        ],  # fmt: skip
        multiplier="0.8x (criticality 4/12) to 1.5x (12/12), linear",
        bands=[{"band": name, "from": floor} for floor, name in rules.BANDS],
        cvss_points=[{"cvss_from": floor, "points": pts} for floor, pts in rules.CVSS_POINTS],
        service_weights=sorted(
            (
                {"service": svc, "points": pts, "label": label}
                for svc, (pts, label) in rules.SERVICE_WEIGHTS.items()
            ),
            key=lambda w: -w["points"],
        ),
        other_port_points=rules.OTHER_PORT_POINTS,
        cves=[
            {
                "cve_id": c.cve_id,
                "product": c.product,
                "version_spec": c.version_spec,
                "cvss": c.cvss,
                "severity": c.severity,
                "summary": c.summary,
            }
            for c in db.scalars(select(CveRef).order_by(CveRef.cvss.desc(), CveRef.cve_id))
        ],
        end_of_life=[
            {k: r[k] for k in ("product", "version_spec", "points", "title")}
            for r in rules.END_OF_LIFE
        ],
        script_findings=[
            {k: r[k] for k in ("script", "points", "title")} for r in rules.SCRIPT_FINDINGS
        ],
        limitations=[
            "Versions come from service banners: vendor backports (e.g. Ubuntu patching "
            "OpenSSH without changing its version) are invisible, so a matched CVE can be "
            "a false positive and should be confirmed on the host.",
            "Only TCP services in the scan profile are assessed; UDP (e.g. SNMP) is not scanned.",
            "Controls a scan cannot see come from the manual checklist and are only as good "
            "as the answers recorded there.",
        ],
    )
