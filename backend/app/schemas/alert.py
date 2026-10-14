from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.scan import Profile

Severity = Literal["info", "low", "medium", "high", "critical"]
AlertStatus = Literal["open", "acknowledged", "resolved"]
AlertKind = Literal[
    "new_device", "host_missing", "port_opened", "port_closed", "risk_jump", "wazuh"
]


class AlertAsset(BaseModel):
    id: int
    asset_tag: str
    name: str | None
    status: str


class AlertOut(BaseModel):
    id: int
    kind: str
    severity: str
    title: str
    message: str
    status: str
    asset: AlertAsset | None
    scan_id: int | None
    payload: dict
    delivery: dict
    delivered_at: datetime | None
    delivery_error: str | None
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    resolved_by: str | None
    resolved_at: datetime | None
    resolution: str | None
    created_at: datetime


class AlertPage(BaseModel):
    items: list[AlertOut]
    total: int


class AlertSummary(BaseModel):
    open: int
    acknowledged: int
    resolved: int
    # unresolved (open + acknowledged) by severity and by kind
    by_severity: dict[str, int]
    by_kind: dict[str, int]
    latest_at: datetime | None


class ResolveBody(BaseModel):
    note: str | None = Field(default=None, max_length=200)


class NotificationSettings(BaseModel):
    min_severity: Severity
    webhook_configured: bool
    webhook_host: str | None  # e.g. "n8n:5678" (never the secret)
    app_url: str
    channels: dict[str, dict]  # last delivery result reported by n8n per channel


class NotificationSettingsUpdate(BaseModel):
    min_severity: Severity


class TestResult(BaseModel):
    state: str  # sent | failed | not_configured
    error: str | None


class AutomationScan(BaseModel):
    profile: Profile = "standard"
    target: str | None = Field(default=None, max_length=43)  # default: first authorised subnet


class DeliveryReport(BaseModel):
    alert_ids: list[int] = Field(default_factory=list, max_length=500)
    channel: Literal["telegram", "email"]
    ok: bool
    skipped: bool = False  # channel not configured: not an error
    error: str | None = Field(default=None, max_length=2000)
