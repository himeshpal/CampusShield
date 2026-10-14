"""Static SVG charts for the PDF (WeasyPrint renders inline SVG; no JavaScript)."""

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from app.services.risk.trend import TrendPoint

PRIMARY = "#059669"  # emerald-600, the app's accent
GRID = "#e5e7eb"
AXIS_TEXT = "#6b7280"
INK = "#111827"


def trend_svg(points: list[TrendPoint], tz: ZoneInfo, width: int = 640, height: int = 170) -> str:
    """Campus average score after each scoring event: one series, so no legend box;
    band thresholds as hairlines, the latest value labelled directly."""
    left, right, top, bottom = 34, 52, 10, 24
    plot_w, plot_h = width - left - right, height - top - bottom

    def x(i: int) -> float:
        return left + (plot_w * i / (len(points) - 1) if len(points) > 1 else plot_w / 2)

    def y(score: float) -> float:
        return top + plot_h * (1 - score / 100)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Inter, DejaVu Sans, sans-serif">'
    ]
    for tick in (0, 25, 50, 75, 100):
        parts.append(
            f'<line x1="{left}" x2="{left + plot_w}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
            f'<text x="{left - 6}" y="{y(tick) + 3:.1f}" font-size="8" fill="{AXIS_TEXT}" '
            f'text-anchor="end">{tick}</text>'
        )
    coords = [(x(i), y(p.average)) for i, p in enumerate(points)]
    if len(coords) > 1:
        path = " ".join(f"{cx:.1f},{cy:.1f}" for cx, cy in coords)
        parts.append(
            f'<polyline points="{path}" fill="none" stroke="{PRIMARY}" stroke-width="2" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
    # markers only when they stay readable (>= 8px apart)
    if len(coords) == 1 or plot_w / (len(coords) - 1) >= 8:
        for cx, cy in coords:
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{PRIMARY}" '
                'stroke="#ffffff" stroke-width="1.5"/>'
            )
    last_x, last_y = coords[-1]
    parts.append(
        f'<text x="{last_x + 8:.1f}" y="{last_y + 3:.1f}" font-size="9" font-weight="600" '
        f'fill="{INK}">{points[-1].average:g}</text>'
    )
    for i in sorted({0, len(points) - 1}):
        anchor = "start" if i == 0 else "end"
        parts.append(
            f'<text x="{x(i):.1f}" y="{height - 6}" font-size="8" fill="{AXIS_TEXT}" '
            f'text-anchor="{anchor}">{escape(_short(points[i].at, tz))}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _short(value: datetime, tz: ZoneInfo) -> str:
    return value.astimezone(tz).strftime("%d %b, %H:%M")
