"""Render a report snapshot to PDF: Jinja2 HTML template + WeasyPrint."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML

from app.core.config import get_settings
from app.services.report.charts import trend_svg
from app.services.report.data import BAND_LABELS, ReportData, plural
from app.services.risk import rules

TEMPLATES = Path(__file__).parent / "templates"
PROFILE_LABELS = {"quick": "Quick sweep", "standard": "Standard audit", "deep": "Deep inspection"}
CONTROL_LABELS = {"yes": "In place", "no": "Missing", "na": "N/A", "unknown": "Not confirmed"}


@dataclass
class RenderedReport:
    pdf: bytes
    pages: int
    sha256: str


@lru_cache
def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tz = ZoneInfo(get_settings().report_timezone)

    def local(value: datetime | None, fmt: str = "%d %b %Y, %H:%M") -> str:
        if value is None:
            return "—"
        moment = value.astimezone(tz)
        return f"{moment.strftime(fmt)} {moment.tzname()}" if "%H" in fmt else moment.strftime(fmt)

    env.filters.update(
        local=local,
        band=lambda b: BAND_LABELS.get(b or "", "Not assessed"),
        score=lambda s: "—" if s is None else f"{s:g}",
        pct=lambda v: f"{round(v * 100)}%",
        profile=lambda p: PROFILE_LABELS.get(p, p),
        control=lambda s: CONTROL_LABELS.get(s, s),
    )
    env.globals.update(plural=plural, band_order=list(BAND_LABELS))
    env.globals["trend_chart"] = lambda points: Markup(trend_svg(points, tz))
    return env


def render_html(data: ReportData) -> str:
    return (
        _env()
        .get_template("report.html")
        .render(
            r=data,
            model={
                "version": rules.MODEL_VERSION,
                "caps": _caps(len(data.controls)),
                "bands": [(BAND_LABELS[name], floor) for floor, name in reversed(rules.BANDS)],
                "limitations": rules.LIMITATIONS,
            },
        )
    )


def _caps(controls: int) -> list[tuple[str, int, str]]:
    """Score components with their maximum and rule, for the methodology section."""
    return [
        ("Network exposure", rules.EXPOSURE_CAP, "weight per reachable service"),
        ("Known vulnerabilities", rules.VULNERABILITY_CAP,
         "CVE matches, end-of-life software, NSE findings"),
        ("Unexpected open ports", rules.DRIFT_CAP,
         f"{rules.DRIFT_POINTS_PER_PORT} per port outside the baseline"),
        ("Missing controls", rules.CONTROL_POINTS * controls,
         f"{rules.CONTROL_POINTS} per control missing or not confirmed"),
        ("Inventory status", rules.INVENTORY_POINTS, "unregistered device"),
    ]  # fmt: skip


def render_pdf(data: ReportData) -> RenderedReport:
    document = HTML(string=render_html(data), base_url=str(TEMPLATES)).render()
    pdf = document.write_pdf()
    digest = hashlib.sha256(pdf).hexdigest()
    return RenderedReport(pdf=pdf, pages=len(document.pages), sha256=digest)
