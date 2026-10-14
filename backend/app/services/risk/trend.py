"""Campus-wide risk over time, rebuilt from the per-asset score history."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, RiskScore
from app.models.base import as_utc
from app.services.risk import rules

# Scores written within this window belong to one event (a scan rescoring every host it
# saw, a checklist save, a startup rescore), so they become one point on the trend.
EVENT_WINDOW = timedelta(seconds=60)


@dataclass
class TrendPoint:
    at: datetime
    average: float
    assessed: int
    bands: dict[str, int]


def campus_trend(db: Session, limit: int = 60) -> list[TrendPoint]:
    """Average score of the current (non-retired) assets after each scoring event."""
    rows = db.execute(
        select(RiskScore.asset_id, RiskScore.score, RiskScore.band, RiskScore.computed_at)
        .join(Asset, Asset.id == RiskScore.asset_id)
        .where(Asset.status != "retired")
        .order_by(RiskScore.computed_at, RiskScore.id)
    ).all()
    current: dict[int, tuple[float, str]] = {}
    points: list[TrendPoint] = []
    event_start: datetime | None = None
    last_at: datetime | None = None
    for asset_id, score, band, computed_at in rows:
        at = as_utc(computed_at)
        if event_start is not None and at - event_start > EVENT_WINDOW:
            points.append(_point(current, last_at))
            event_start = None
        if event_start is None:
            event_start = at
        current[asset_id] = (score, band)
        last_at = at
    if current and last_at is not None:
        points.append(_point(current, last_at))
    return points[-limit:]


def _point(current: dict[int, tuple[float, str]], at: datetime) -> TrendPoint:
    bands = {name: 0 for _, name in rules.BANDS}
    for _, band in current.values():
        bands[band] += 1
    average = sum(score for score, _ in current.values()) / len(current)
    return TrendPoint(at=at, average=round(average, 1), assessed=len(current), bands=bands)
