from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import utcnow
from app.models.user import User


class Report(Base):
    """A generated PDF audit report: a point-in-time snapshot, kept for the record.

    The PDF itself is stored in the database (a report is ~100-300 KB), so reports are
    backed up with everything else and need no file volume."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    generated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    include_details: Mapped[bool] = mapped_column(default=True)
    # headline numbers at generation time, so the history list needs no PDF parsing
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    pages: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    pdf: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    generated_by: Mapped[User | None] = relationship(lazy="joined")

    @property
    def number(self) -> str:
        return f"RPT-{self.id:04d}"
