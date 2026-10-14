from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import utcnow

ALERT_KINDS = (
    "new_device",
    "host_missing",
    "port_opened",
    "port_closed",
    "risk_jump",
    "wazuh",
)
ALERT_STATUSES = ("open", "acknowledged", "resolved")


class Alert(Base):
    """A change between two scans worth a human's attention (doc: change-based alerting)."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    # notification state: {"webhook": sent|failed|not_configured|below_threshold,
    #  "channels": {"telegram": {"ok": bool, "at": iso, "error": str|None}, ...}}
    delivery: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_error: Mapped[str | None] = mapped_column(Text)
    acknowledged_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # why it was resolved: by whom, or what the system saw (e.g. "Port closed in scan #31")
    resolution: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
