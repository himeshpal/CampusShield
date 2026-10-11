from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ControlStatus = Literal["yes", "no", "na", "unknown"]


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    description: str
    points: float


class EntryOut(BaseModel):
    status: ControlStatus
    evidence: str | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None


class EntryUpdate(BaseModel):
    status: ControlStatus
    evidence: str | None = Field(default=None, max_length=500)


class BulkEntry(EntryUpdate):
    item_key: str


class BulkUpdate(BaseModel):
    entries: list[BulkEntry] = Field(min_length=1, max_length=20)


class ChecklistRow(BaseModel):
    asset_id: int
    asset_tag: str
    name: str | None
    asset_type: str
    status: str
    risk_score: float | None
    risk_band: str | None
    entries: dict[str, EntryOut]  # item key -> entry ("unknown" when never answered)
    answered: int  # controls not "unknown"


class ChecklistMatrix(BaseModel):
    items: list[ChecklistItemOut]
    rows: list[ChecklistRow]


class RiskChange(BaseModel):
    before: float | None
    after: float | None
    band_before: str | None
    band_after: str | None


class SaveResult(BaseModel):
    row: ChecklistRow
    risk: RiskChange


class ControlCoverage(BaseModel):
    key: str
    label: str
    counts: dict[ControlStatus, int]


class ChecklistSummary(BaseModel):
    assets: int
    answered: int  # cells not "unknown"
    total: int  # assets x controls
    gaps: int  # cells answered "no"
    coverage: list[ControlCoverage]
