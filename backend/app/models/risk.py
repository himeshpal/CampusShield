from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import utcnow

SEVERITIES = ("info", "low", "medium", "high", "critical")
RISK_BANDS = ("low", "medium", "high", "critical")
CHECKLIST_STATUSES = ("yes", "no", "na", "unknown")


class CveRef(Base):
    """Static reference list: known-vulnerable product/version -> CVE and CVSS."""

    __tablename__ = "cve_refs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cve_id: Mapped[str] = mapped_column(String(30), index=True)
    product: Mapped[str] = mapped_column(String(120), index=True)
    version_spec: Mapped[str] = mapped_column(String(60))  # e.g. "==2.4.49", "<5.7.44"
    cvss: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_host_id: Mapped[int] = mapped_column(
        ForeignKey("scan_hosts.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))  # risky_port|cve|baseline_drift|unregistered
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text)
    port: Mapped[int | None] = mapped_column(Integer)
    cve_id: Mapped[str | None] = mapped_column(String(30))
    points: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChecklistItem(Base):
    """A security control that cannot be verified by a network scan (MFA, AV, ...)."""

    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    points: Mapped[float] = mapped_column(Float, default=4)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ChecklistEntry(Base):
    __tablename__ = "checklist_entries"
    __table_args__ = (UniqueConstraint("asset_id", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("checklist_items.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(10), default="unknown")
    evidence: Mapped[str | None] = mapped_column(Text)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RiskScore(Base):
    """Score history per asset; `breakdown` explains every point of the score."""

    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"))
    score: Mapped[float] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(20))
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
