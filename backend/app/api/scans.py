from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.models import RiskScore, Scan, ScanHost
from app.models.scan import ACTIVE_STATUSES
from app.schemas.scan import ScanCreate, ScanDetail, ScanOptions, ScanOut
from app.services import scans as scan_service
from app.services.scanner.profiles import PROFILES, display_command
from app.services.scanner.scope import ScopeError

router = APIRouter(prefix="/scans", tags=["scans"])


def _out(scan: Scan, model: type[ScanOut] = ScanOut) -> ScanOut:
    data = model.model_validate(scan, from_attributes=True)
    data.requested_by_name = scan.requested_by.full_name if scan.requested_by else None
    data.open_ports = scan.summary.get("open_ports", 0)
    data.command = scan.summary.get("command")
    if isinstance(data, ScanDetail):
        data.matched = scan.summary.get("matched", 0)
        data.new_devices = scan.summary.get("new_devices", 0)
        data.ip_conflicts = scan.summary.get("ip_conflicts", 0)
    return data


@router.get("/options", response_model=ScanOptions)
def scan_options(_: CurrentUser) -> ScanOptions:
    settings = get_settings()
    subnets = settings.authorized_subnet_list
    default = subnets[0] if subnets else ""
    return ScanOptions(
        profiles=[
            {
                "key": p.key,
                "label": p.label,
                "description": p.description,
                "estimate": p.estimate,
                "command": display_command(default, p, settings.scan_exclude_list),
            }
            for p in PROFILES.values()
        ],
        authorized_subnets=subnets,
        excluded=settings.scan_exclude_list,
        default_target=default,
    )


@router.post("", response_model=ScanOut, status_code=status.HTTP_202_ACCEPTED)
def create_scan(body: ScanCreate, admin: AdminUser, request: Request, db: DbSession) -> ScanOut:
    try:
        scan = scan_service.start_scan(
            db,
            target=body.target,
            profile=body.profile,
            user=admin,
            ip_address=client_ip(request),
        )
    except ScopeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
    except scan_service.ScanConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    db.refresh(scan)
    return _out(scan)


@router.get("", response_model=list[ScanOut])
def list_scans(
    _: CurrentUser, db: DbSession, limit: int = Query(default=20, ge=1, le=100)
) -> list[ScanOut]:
    scans = db.scalars(select(Scan).order_by(Scan.id.desc()).limit(limit))
    return [_out(s) for s in scans]


@router.get("/active", response_model=ScanOut | None)
def active_scan(_: CurrentUser, db: DbSession) -> ScanOut | None:
    scan = db.scalar(select(Scan).where(Scan.status.in_(ACTIVE_STATUSES)))
    return _out(scan) if scan else None


@router.get("/{scan_id}", response_model=ScanDetail)
def get_scan(scan_id: int, _: CurrentUser, db: DbSession) -> ScanOut:
    scan = db.scalar(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(
            selectinload(Scan.hosts).selectinload(ScanHost.ports),
            selectinload(Scan.hosts).selectinload(ScanHost.asset),
            selectinload(Scan.hosts).selectinload(ScanHost.findings),
        )
    )
    if not scan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    detail = _out(scan, ScanDetail)
    # the score each asset got from this scan (the first one recorded for it)
    scores: dict[int, RiskScore] = {}
    for row in db.scalars(
        select(RiskScore).where(RiskScore.scan_id == scan_id).order_by(RiskScore.id)
    ):
        scores.setdefault(row.asset_id, row)
    for host in detail.hosts:
        if host.asset and (risk := scores.get(host.asset.id)):
            host.risk_score, host.risk_band = risk.score, risk.band
    return detail


@router.post("/{scan_id}/cancel", response_model=ScanOut)
def cancel_scan(scan_id: int, admin: AdminUser, db: DbSession) -> ScanOut:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    if scan.status not in ACTIVE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a running scan can be cancelled")
    scan_service.request_cancel(db, scan, admin)
    return _out(scan)
