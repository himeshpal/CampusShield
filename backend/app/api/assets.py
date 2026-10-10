from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AdminUser, CurrentUser, DbSession, client_ip
from app.models import Asset, Scan, ScanHost
from app.schemas.asset import (
    AssetDetail,
    AssetFields,
    AssetOut,
    AssetStatus,
    AssetSummary,
    AssetType,
    AssetUpdate,
    Observation,
    ObservedPort,
    criticality_level,
)
from app.services import audit
from app.services.matching import next_asset_tag

router = APIRouter(prefix="/assets", tags=["assets"])


def _latest_hosts(db: Session, asset_ids: list[int]) -> dict[int, ScanHost]:
    """Most recent observation of each asset (from completed scans)."""
    if not asset_ids:
        return {}
    latest = (
        select(func.max(ScanHost.id))
        .join(Scan, Scan.id == ScanHost.scan_id)
        .where(ScanHost.asset_id.in_(asset_ids), Scan.status == "completed")
        .group_by(ScanHost.asset_id)
    )
    hosts = db.scalars(
        select(ScanHost).where(ScanHost.id.in_(latest)).options(selectinload(ScanHost.ports))
    )
    return {h.asset_id: h for h in hosts}


def _out(asset: Asset, latest: ScanHost | None, model: type[AssetOut] = AssetOut, **extra):
    total = (
        asset.data_sensitivity
        + asset.service_dependency
        + asset.users_affected
        + asset.replaceability
    )
    data = model.model_validate(
        {
            **{c: getattr(asset, c) for c in AssetOut.model_fields if hasattr(asset, c)},
            "criticality": total,
            "criticality_level": criticality_level(total),
            "observed_ports": [ObservedPort.model_validate(p) for p in latest.ports]
            if latest
            else None,
            "last_scan_id": latest.scan_id if latest else None,
            **extra,
        }
    )
    return data


def _get(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return asset


def _check_mac_unique(db: Session, mac: str | None, exclude_id: int | None = None) -> None:
    if not mac:
        return
    query = select(Asset).where(Asset.mac_address == mac, Asset.status != "retired")
    if exclude_id:
        query = query.where(Asset.id != exclude_id)
    if other := db.scalar(query):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{other.asset_tag} already uses MAC address {mac}"
        )


@router.get("/summary", response_model=AssetSummary)
def summary(_: CurrentUser, db: DbSession) -> AssetSummary:
    counts = dict(db.execute(select(Asset.status, func.count()).group_by(Asset.status)).all())
    by_type = dict(
        db.execute(
            select(Asset.asset_type, func.count())
            .where(Asset.status == "registered")
            .group_by(Asset.asset_type)
        ).all()
    )
    return AssetSummary(
        registered=counts.get("registered", 0),
        unregistered=counts.get("unregistered", 0),
        retired=counts.get("retired", 0),
        by_type=by_type,
    )


@router.get("", response_model=list[AssetOut])
def list_assets(
    _: CurrentUser,
    db: DbSession,
    status_filter: Annotated[AssetStatus | None, Query(alias="status")] = None,
    asset_type: AssetType | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[AssetOut]:
    query = select(Asset)
    if status_filter:
        query = query.where(Asset.status == status_filter)
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.where(
            or_(
                *(
                    col.ilike(like)
                    for col in (
                        Asset.asset_tag, Asset.name, Asset.hostname, Asset.ip_address,
                        Asset.mac_address, Asset.mac_vendor, Asset.department,
                        Asset.location, Asset.owner,
                    )
                )
            )
        )  # fmt: skip
    # unregistered first: they need attention
    assets = list(db.scalars(query.order_by((Asset.status == "unregistered").desc(), Asset.id)))
    latest = _latest_hosts(db, [a.id for a in assets])
    return [_out(a, latest.get(a.id)) for a in assets]


@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset(asset_id: int, _: CurrentUser, db: DbSession) -> AssetOut:
    asset = _get(db, asset_id)
    rows = db.execute(
        select(ScanHost, Scan)
        .join(Scan, Scan.id == ScanHost.scan_id)
        .where(ScanHost.asset_id == asset_id, Scan.status == "completed")
        .options(selectinload(ScanHost.ports))
        .order_by(ScanHost.id.desc())
        .limit(20)
    ).all()
    observations = [
        Observation(
            scan_id=scan.id,
            scanned_at=scan.finished_at or scan.created_at,
            profile=scan.profile,
            ip_address=host.ip_address,
            match_method=host.match_method,
            ports=[ObservedPort.model_validate(p) for p in host.ports],
        )
        for host, scan in rows
    ]
    latest = rows[0][0] if rows else None
    return _out(asset, latest, AssetDetail, observations=observations)


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(body: AssetFields, admin: AdminUser, request: Request, db: DbSession):
    _check_mac_unique(db, body.mac_address)
    asset = Asset(**body.model_dump(), asset_tag=next_asset_tag(db), status="registered")
    db.add(asset)
    db.flush()
    audit.record(
        db, "asset.created", user=admin, entity_type="asset", entity_id=asset.id,
        details={"asset_tag": asset.asset_tag, "name": asset.name},
        ip_address=client_ip(request),
    )  # fmt: skip
    db.commit()
    return _out(asset, None)


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: int, body: AssetUpdate, admin: AdminUser, request: Request, db: DbSession
):
    asset = _get(db, asset_id)
    changes = body.model_dump(exclude_unset=True)
    if "mac_address" in changes:
        _check_mac_unique(db, changes["mac_address"], exclude_id=asset.id)
    if changes.get("status") == "registered" and not (changes.get("name") or asset.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Give the asset a name to register it")
    for field, value in changes.items():
        setattr(asset, field, value)
    action = {"retired": "asset.retired", "registered": "asset.registered"}.get(
        changes.get("status", ""), "asset.updated"
    )
    audit.record(
        db, action, user=admin, entity_type="asset", entity_id=asset.id,
        details={k: v for k, v in changes.items() if k != "notes"},
        ip_address=client_ip(request),
    )  # fmt: skip
    db.commit()
    return _out(asset, _latest_hosts(db, [asset.id]).get(asset.id))


@router.post("/{asset_id}/register", response_model=AssetOut)
def register_asset(
    asset_id: int, body: AssetFields, admin: AdminUser, request: Request, db: DbSession
):
    """Turn a discovered (unregistered) device into a registered asset."""
    asset = _get(db, asset_id)
    if asset.status != "unregistered":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{asset.asset_tag} is already {asset.status}"
        )
    _check_mac_unique(db, body.mac_address, exclude_id=asset.id)
    for field, value in body.model_dump().items():
        setattr(asset, field, value)
    asset.status = "registered"
    # observations from earlier scans now belong to a registered asset
    for host in db.scalars(select(ScanHost).where(ScanHost.asset_id == asset.id)):
        host.is_registered = True
    audit.record(
        db, "asset.registered", user=admin, entity_type="asset", entity_id=asset.id,
        details={"asset_tag": asset.asset_tag, "name": asset.name, "type": asset.asset_type},
        ip_address=client_ip(request),
    )  # fmt: skip
    db.commit()
    return _out(asset, _latest_hosts(db, [asset.id]).get(asset.id))
