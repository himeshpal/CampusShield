import pytest
from sqlalchemy import select

from app.models import AuditLog, Report
from app.services.report.data import collect
from app.services.report.render import render_html
from app.services.risk.service import seed_cve_refs
from app.services.seed import seed_demo_assets

REPORTS = "/api/v1/reports"


@pytest.fixture
def demo(db, admin_client, fake_nmap):
    seed_demo_assets(db)
    seed_cve_refs(db)
    admin_client.post("/api/v1/scans", json={"target": "172.25.0.0/24"})  # scores + rogue


def test_auditor_generates_a_report_matching_the_dashboard(auditor_client, demo, db):
    res = auditor_client.post(REPORTS, json={"title": "  Mid-semester audit  "})
    assert res.status_code == 201, res.text
    report = res.json()
    assert report["number"] == "RPT-0001" and report["title"] == "Mid-semester audit"
    assert report["generated_by"] == "Security Auditor"
    assert report["pages"] > 5 and report["size_bytes"] > 10_000 and len(report["sha256"]) == 64

    risk = auditor_client.get("/api/v1/risk/summary").json()
    summary = report["summary"]
    assert summary["average"] == risk["average"]
    assert summary["bands"] == risk["bands"]
    assert summary["assets"] == 6 and summary["unregistered"] == 1
    assert summary["vulnerabilities"] > 0 and summary["recommendations"] > 0

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "report.generated"))
    assert entry.actor == "auditor@campusshield.local"
    assert entry.details["number"] == "RPT-0001"


def test_pdf_download_inline_or_attachment(admin_client, demo):
    report = admin_client.post(REPORTS, json={"include_details": False}).json()
    inline = admin_client.get(f"{REPORTS}/{report['id']}/pdf")
    assert inline.status_code == 200
    assert inline.headers["content-type"] == "application/pdf"
    assert inline.content.startswith(b"%PDF-") and len(inline.content) == report["size_bytes"]
    disposition = inline.headers["content-disposition"]
    assert disposition.startswith("inline;") and 'filename="CampusShield-RPT-0001-' in disposition
    assert "no-store" in inline.headers["cache-control"]

    attachment = admin_client.get(f"{REPORTS}/{report['id']}/pdf", params={"download": True})
    assert attachment.headers["content-disposition"].startswith("attachment;")


def test_details_section_is_optional(admin_client, demo):
    full = admin_client.post(REPORTS, json={"include_details": True}).json()
    short = admin_client.post(REPORTS, json={"include_details": False}).json()
    assert short["pages"] < full["pages"]


def test_default_title_and_validation(admin_client, demo):
    blank = admin_client.post(REPORTS, json={"title": "   "}).json()
    assert blank["title"].startswith("Campus security audit, ")
    assert admin_client.post(REPORTS, json={"title": "x" * 201}).status_code == 422


def test_history_is_newest_first_without_pdf_bytes(admin_client, demo):
    for _ in range(2):
        admin_client.post(REPORTS, json={"include_details": False})
    listed = admin_client.get(REPORTS).json()
    assert [r["number"] for r in listed] == ["RPT-0002", "RPT-0001"]
    assert "pdf" not in listed[0]


def test_only_admins_delete_reports(admin_client, auditor_client, demo, db):
    report = admin_client.post(REPORTS, json={"include_details": False}).json()
    assert auditor_client.delete(f"{REPORTS}/{report['id']}").status_code == 403
    assert admin_client.delete(f"{REPORTS}/{report['id']}").status_code == 204
    assert admin_client.get(f"{REPORTS}/{report['id']}/pdf").status_code == 404
    assert db.scalar(select(Report)) is None
    assert db.scalar(select(AuditLog).where(AuditLog.action == "report.deleted")) is not None


def test_reports_require_sign_in(client, db):
    assert client.get(REPORTS).status_code == 401
    assert client.post(REPORTS, json={}).status_code == 401
    assert client.get(f"{REPORTS}/1/pdf").status_code == 401


def test_report_before_any_scan_still_renders(admin_client):
    res = admin_client.post(REPORTS, json={"include_details": False})
    assert res.status_code == 201
    assert res.json()["summary"]["assessed"] == 0


def test_report_content_covers_the_lab_findings(demo, db):
    data = collect(db, title="Lab audit", number="RPT-0042", generated_by=None)
    assert data.assets[0].score >= data.assets[-1].score  # riskiest first
    assert [a.ip for a in data.unregistered] == ["172.25.0.66"]
    assert any(v.cve_id == "CVE-2021-41773" for v in data.vulnerabilities)
    upgrade = next(r for r in data.recommendations if r.kind == "cve")
    assert upgrade.priority == "critical" and "Apache httpd 2.4.49" in upgrade.action
    assert any("172.25.0.66" in line for line in data.narrative())

    html = render_html(data)
    for text in ("RPT-0042", "Lab audit", "Priority recommendations", "CVE-2021-41773",
                 "172.25.0.66", "Scope and methodology", "Asset details"):  # fmt: skip
        assert text in html


def test_campus_trend_follows_the_latest_scores(admin_client, demo):
    before = admin_client.get("/api/v1/risk/trend").json()
    assert before and before[-1]["assessed"] == 7
    admin_client.put("/api/v1/checklist/1/firewall", json={"status": "yes"})
    after = admin_client.get("/api/v1/risk/trend").json()
    assert after[-1]["average"] <= before[-1]["average"]
    assert sum(after[-1]["bands"].values()) == 7


def test_trend_groups_scores_written_together_into_one_event(db):
    from datetime import UTC, datetime, timedelta

    from app.models import Asset, RiskScore
    from app.services.risk.trend import campus_trend

    a, b = Asset(asset_tag="CS-0001"), Asset(asset_tag="CS-0002")
    db.add_all([a, b])
    db.flush()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    for asset, score, offset in [(a, 40, 0), (b, 80, 2), (a, 20, 600), (b, 60, 3600)]:
        db.add(RiskScore(asset_id=asset.id, score=score, band="low",
                         computed_at=t0 + timedelta(seconds=offset)))  # fmt: skip
    db.commit()
    assert [(p.average, p.assessed) for p in campus_trend(db)] == [(60, 2), (50, 2), (40, 2)]
