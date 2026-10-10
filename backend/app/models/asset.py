from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin

ASSET_TYPES = (
    "server",
    "workstation",
    "wifi_ap",
    "iot_cctv",
    "iot_biometric",
    "printer",
    "network_device",
    "other",
)
ASSET_STATUSES = ("registered", "unregistered", "retired")


class Asset(TimestampMixin, Base):
    """A persistent campus IT asset. Scans are linked back to these records."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_tag: Mapped[str] = mapped_column(String(20), unique=True)  # CS-0001
    name: Mapped[str | None] = mapped_column(String(120))  # "ERP Portal Server"
    hostname: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45), index=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), index=True)
    mac_vendor: Mapped[str | None] = mapped_column(String(120))
    asset_type: Mapped[str] = mapped_column(String(30), default="other")
    os_name: Mapped[str | None] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(120))
    owner: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="registered", index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    # Objective valuation criteria (Ete et al., 2024), each 1 (low) .. 3 (high).
    # Combined into the criticality multiplier used by the risk engine.
    data_sensitivity: Mapped[int] = mapped_column(Integer, default=2)
    service_dependency: Mapped[int] = mapped_column(Integer, default=2)
    users_affected: Mapped[int] = mapped_column(Integer, default=2)
    replaceability: Mapped[int] = mapped_column(Integer, default=2)

    # Ports considered "normal" for this asset; anything else is baseline drift.
    baseline_ports: Mapped[list[int]] = mapped_column(JSON, default=list)

    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
