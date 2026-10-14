"""Manual security checklist: controls a network scan cannot verify (doc section 1.2).

Only registered assets are assessed: an unregistered device has no owner to answer for
it, so it has to be registered first.
"""

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser, DbSession, client_ip
from app.models import Asset, ChecklistEntry, ChecklistItem, RiskScore, User
from app.models.base import utcnow
from app.schemas.checklist import (
    BulkUpdate,
    ChecklistItemOut,
    ChecklistMatrix,
    ChecklistRow,
    ChecklistSummary,
    ControlCoverage,
    EntryOut,
    EntryUpdate,
    RiskChange,
    SaveResult,
)
from app.services import audit
from app.services.risk.service import latest_scores, rescore

router = APIRouter(prefix="/checklist", tags=["checklist"])


def _items(db: Session) -> list[ChecklistItem]:
    return list(db.scalars(select(ChecklistItem).order_by(ChecklistItem.sort_order)))


def _assessable(db: Session) -> list[Asset]:
    return list(db.scalars(select(Asset).where(Asset.status == "registered").order_by(Asset.id)))


def _rows(db: Session, assets: list[Asset], items: list[ChecklistItem]) -> list[ChecklistRow]:
    ids = [a.id for a in assets]
    entries = (
        db.scalars(select(ChecklistEntry).where(ChecklistEntry.asset_id.in_(ids))).all()
        if ids
        else []
    )
    names = {u.id: u.full_name for u in db.scalars(select(User))}
    by_asset: dict[int, dict[int, ChecklistEntry]] = {}
    for e in entries:
        by_asset.setdefault(e.asset_id, {})[e.item_id] = e
    scores = latest_scores(db, ids)
    rows = []
    for asset in assets:
        cells = {}
        for item in items:
            e = by_asset.get(asset.id, {}).get(item.id)
            cells[item.key] = (
                EntryOut(
                    status=e.status,
                    evidence=e.evidence,
                    updated_by=names.get(e.updated_by_id),
                    updated_at=e.updated_at,
                )
                if e
                else EntryOut(status="unknown")
            )
        score = scores.get(asset.id)
        rows.append(
            ChecklistRow(
                asset_id=asset.id,
                asset_tag=asset.asset_tag,
                name=asset.name,
                asset_type=asset.asset_type,
                status=asset.status,
                risk_score=score.score if score else None,
                risk_band=score.band if score else None,
                entries=cells,
                answered=sum(c.status != "unknown" for c in cells.values()),
            )
        )
    return rows


@router.get("", response_model=ChecklistMatrix)
def checklist(_: CurrentUser, db: DbSession) -> ChecklistMatrix:
    items = _items(db)
    return ChecklistMatrix(
        items=[ChecklistItemOut.model_validate(i) for i in items],
        rows=_rows(db, _assessable(db), items),
    )


@router.get("/summary", response_model=ChecklistSummary)
def summary(_: CurrentUser, db: DbSession) -> ChecklistSummary:
    items = _items(db)
    rows = _rows(db, _assessable(db), items)
    coverage = []
    for item in items:
        counts = {"yes": 0, "no": 0, "na": 0, "unknown": 0}
        for row in rows:
            counts[row.entries[item.key].status] += 1
        coverage.append(ControlCoverage(key=item.key, label=item.label, counts=counts))
    return ChecklistSummary(
        assets=len(rows),
        answered=sum(r.answered for r in rows),
        total=len(rows) * len(items),
        gaps=sum(c.counts["no"] for c in coverage),
        coverage=coverage,
    )


def _apply(
    db: Session,
    asset_id: int,
    updates: list[tuple[str, EntryUpdate]],
    admin: User,
    ip: str | None,
) -> SaveResult:
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    if asset.status != "registered":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{asset.asset_tag} is {asset.status}: only registered assets have a checklist",
        )
    items = {i.key: i for i in _items(db)}
    unknown = [key for key, _ in updates if key not in items]
    if unknown:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown control: {', '.join(unknown)}")

    before = latest_scores(db, [asset.id]).get(asset.id)
    changed = {}
    for key, update in updates:
        item = items[key]
        entry = db.scalar(
            select(ChecklistEntry).where(
                ChecklistEntry.asset_id == asset.id, ChecklistEntry.item_id == item.id
            )
        )
        if entry is None:
            entry = ChecklistEntry(asset_id=asset.id, item_id=item.id, status="unknown")
            db.add(entry)
        evidence = (update.evidence or "").strip() or None
        if (entry.status, entry.evidence) == (update.status, evidence):
            continue  # nothing changed: no audit noise, no new score
        changed[key] = {"from": entry.status, "to": update.status}
        entry.status, entry.evidence = update.status, evidence
        entry.updated_by_id, entry.updated_at = admin.id, utcnow()

    after: RiskScore | None = before
    if changed:
        db.flush()
        after = rescore(db, asset)
        audit.record(
            db,
            "checklist.updated",
            user=admin,
            entity_type="asset",
            entity_id=asset.id,
            details={
                "asset_tag": asset.asset_tag,
                "controls": changed,
                "risk": [before.score if before else None, after.score if after else None],
            },
            ip_address=ip,
        )
    db.commit()
    return SaveResult(
        row=_rows(db, [asset], list(items.values()))[0],
        risk=RiskChange(
            before=before.score if before else None,
            after=after.score if after else None,
            band_before=before.band if before else None,
            band_after=after.band if after else None,
        ),
    )


@router.put("/{asset_id}/{item_key}", response_model=SaveResult)
def set_entry(
    asset_id: int,
    item_key: str,
    body: EntryUpdate,
    admin: AdminUser,
    request: Request,
    db: DbSession,
) -> SaveResult:
    return _apply(db, asset_id, [(item_key, body)], admin, client_ip(request))


@router.put("/{asset_id}", response_model=SaveResult)
def set_entries(
    asset_id: int, body: BulkUpdate, admin: AdminUser, request: Request, db: DbSession
) -> SaveResult:
    """Answer several controls of one asset at once (one rescore, one audit entry)."""
    keys = [e.item_key for e in body.entries]
    if len(keys) != len(set(keys)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Each control at most once")
    updates = [
        (e.item_key, EntryUpdate(status=e.status, evidence=e.evidence)) for e in body.entries
    ]
    return _apply(db, asset_id, updates, admin, client_ip(request))
