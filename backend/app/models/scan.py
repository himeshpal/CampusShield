from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import utcnow
from app.models.user import User

SCAN_PROFILES = ("quick", "standard", "deep")
SCAN_STATUSES = ("queued", "running", "completed", "failed", "cancelled")
ACTIVE_STATUSES = ("queued", "running")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[str] = mapped_column(String(100))
    profile: Mapped[str] = mapped_column(String(20), default="standard")
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    triggered_by: Mapped[str] = mapped_column(String(20), default="user")  # user|schedule|n8n
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str | None] = mapped_column(String(80))  # e.g. "Detecting services"
    hosts_up: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    hosts: Mapped[list["ScanHost"]] = relationship(  # noqa: UP037 - defined below
        back_populates="scan", cascade="all, delete-orphan", order_by="ScanHost.id"
    )
    requested_by: Mapped[User | None] = relationship(lazy="joined")


class ScanHost(Base):
    """One host as seen by one scan (raw observation, linked to an asset if matched)."""

    __tablename__ = "scan_hosts"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45))
    mac_address: Mapped[str | None] = mapped_column(String(17))
    mac_vendor: Mapped[str | None] = mapped_column(String(120))
    hostname: Mapped[str | None] = mapped_column(String(255))
    os_guess: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(20), default="up")
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)

    scan: Mapped[Scan] = relationship(back_populates="hosts")
    ports: Mapped[list["ScanPort"]] = relationship(  # noqa: UP037 - defined below
        back_populates="host", cascade="all, delete-orphan", order_by="ScanPort.port"
    )


class ScanPort(Base):
    __tablename__ = "scan_ports"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_host_id: Mapped[int] = mapped_column(
        ForeignKey("scan_hosts.id", ondelete="CASCADE"), index=True
    )
    port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(10), default="tcp")
    state: Mapped[str] = mapped_column(String(20), default="open")
    service: Mapped[str | None] = mapped_column(String(60))
    product: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[str | None] = mapped_column(String(60))
    extra_info: Mapped[str | None] = mapped_column(String(255))
    script_output: Mapped[dict] = mapped_column(JSON, default=dict)

    host: Mapped[ScanHost] = relationship(back_populates="ports")
