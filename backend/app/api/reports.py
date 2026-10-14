"""PDF audit reports: generate a point-in-time snapshot, keep it, download it later."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import undefer

from app.api.deps import AdminUser, CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.models import Report
from app.models.base import as_utc, utcnow
from app.schemas.report import ReportCreate, ReportOut
from app.services import audit
from app.services.report.data import collect
from app.services.report.render import render_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


def _out(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        number=report.number,
        title=report.title,
        include_details=report.include_details,
        summary=report.summary,
        pages=report.pages,
        size_bytes=report.size_bytes,
        sha256=report.sha256,
        generated_by=report.generated_by.full_name if report.generated_by else None,
        created_at=report.created_at,
    )


def _local(value: datetime) -> datetime:
    return as_utc(value).astimezone(ZoneInfo(get_settings().report_timezone))


def default_title(now: datetime) -> str:
    return f"Campus security audit, {_local(now).strftime('%B %Y')}"


@router.get("", response_model=list[ReportOut])
def list_reports(
    _: CurrentUser, db: DbSession, limit: int = Query(default=50, ge=1, le=200)
) -> list[ReportOut]:
    reports = db.scalars(select(Report).order_by(Report.id.desc()).limit(limit))
    return [_out(r) for r in reports]


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(
    body: ReportCreate, user: CurrentUser, request: Request, db: DbSession
) -> ReportOut:
    """Any signed-in user may generate one: a report changes no security data, and
    producing reports is exactly what the auditor role is for."""
    title = (body.title or "").strip() or default_title(utcnow())
    report = Report(
        title=title,
        generated_by_id=user.id,
        include_details=body.include_details,
        summary={},
        pages=0,
        size_bytes=0,
        sha256="",
        pdf=b"",
    )
    db.add(report)
    db.flush()  # the id gives the report number printed inside the PDF
    data = collect(
        db,
        title=title,
        number=report.number,
        generated_by=user,
        include_details=body.include_details,
    )
    rendered = render_pdf(data)
    report.summary = data.summary()
    report.pdf, report.pages = rendered.pdf, rendered.pages
    report.size_bytes, report.sha256 = len(rendered.pdf), rendered.sha256
    report.created_at = data.generated_at
    audit.record(
        db,
        "report.generated",
        user=user,
        entity_type="report",
        entity_id=report.id,
        details={"number": report.number, "title": title, "pages": rendered.pages},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(report)
    return _out(report)


@router.get("/{report_id}/pdf")
def download_report(
    report_id: int,
    _: CurrentUser,
    db: DbSession,
    download: bool = Query(default=False, description="attachment instead of inline"),
) -> Response:
    report = db.scalar(select(Report).where(Report.id == report_id).options(undefer(Report.pdf)))
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    filename = f"CampusShield-{report.number}-{_local(report.created_at):%Y-%m-%d}.pdf"
    disposition = "attachment" if download else "inline"
    return Response(
        content=report.pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            # describes security weaknesses: keep it out of shared caches
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, admin: AdminUser, request: Request, db: DbSession) -> None:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    audit.record(
        db,
        "report.deleted",
        user=admin,
        entity_type="report",
        entity_id=report.id,
        details={"number": report.number, "title": report.title},
        ip_address=client_ip(request),
    )
    db.delete(report)
    db.commit()
