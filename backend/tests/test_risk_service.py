"""Risk scoring wired to the database: scans, carry-forward, rescoring, API."""

import pytest
from sqlalchemy import select

from app.models import Finding, RiskScore, Scan
from app.services import scans as scan_service
from app.services.risk import rules
from app.services.risk.service import rescore_outdated, seed_cve_refs
from app.services.seed import seed_demo_assets
from tests.conftest import FIXTURES

SCANS, ASSETS, RISK = "/api/v1/scans", "/api/v1/assets", "/api/v1/risk"


@pytest.fixture
def demo(db):
    seed_demo_assets(db)
    seed_cve_refs(db)


def run_scan(client, monkeypatch, fixture: str, profile: str = "standard") -> int:
    """Run a scan whose nmap output is a recorded lab scan."""

    def runner(target, prof, exclude, on_progress, should_cancel):
        return (FIXTURES / fixture).read_text()

    monkeypatch.setattr(scan_service, "nmap_runner", runner)
    res = client.post(SCANS, json={"target": "172.25.0.0/24", "profile": profile})
    assert res.status_code == 202
    return res.json()["id"]


def scores(client) -> dict[str, dict]:
    return {a["asset_tag"]: a for a in client.get(ASSETS).json()}


def test_scan_scores_every_asset_from_its_own_evidence(admin_client, demo, monkeypatch, db):
    scan_id = run_scan(admin_client, monkeypatch, "lab_standard.xml")
    assets = scores(admin_client)
    assert assets["CS-0002"]["risk_band"] == "high"  # Apache 2.4.49
    assert assets["CS-0003"]["risk_score"] == 66.0  # MySQL 5.7 end-of-life
    # regression: the scan being finished is still "running" while it is scored,
    # and must be the evidence used (scores were one scan behind before the fix)
    rows = db.scalars(select(RiskScore)).all()
    assert rows and {r.scan_id for r in rows} == {scan_id}
    assert db.scalar(select(Finding).where(Finding.cve_id == "CVE-2021-41773"))


def test_deep_scan_evidence_is_used_by_that_scan(admin_client, demo, monkeypatch):
    run_scan(admin_client, monkeypatch, "lab_standard.xml")
    deep = run_scan(admin_client, monkeypatch, "lab_deep.xml", "deep")
    detail = admin_client.get(f"{SCANS}/{deep}").json()
    pi = next(h for h in detail["hosts"] if h["ip_address"] == "172.25.0.66")
    assert any("Redis answers without authentication" in f["title"] for f in pi["findings"])
    assert pi["risk_band"] == "critical"
    lab_pc = next(h for h in detail["hosts"] if h["ip_address"] == "172.25.0.20")
    assert any(f["kind"] == "misconfiguration" for f in lab_pc["findings"])  # anonymous FTP


def test_quick_scan_keeps_versions_and_scripts_from_earlier_scans(admin_client, demo, monkeypatch):
    run_scan(admin_client, monkeypatch, "lab_deep.xml", "deep")
    before = scores(admin_client)
    quick = run_scan(admin_client, monkeypatch, "lab_quick.xml", "quick")
    after = scores(admin_client)
    for tag in ("CS-0002", "CS-0003", "CS-0004", "CS-0007"):
        assert after[tag]["risk_score"] == before[tag]["risk_score"], tag
        assert after[tag]["last_scan_id"] == quick
    detail = admin_client.get(f"{ASSETS}/2").json()
    cve = next(i for i in detail["risk"]["components"][1]["items"] if i.get("cve_id"))
    assert "identified in scan #" in cve["detail"]  # evidence source is shown


def test_editing_criticality_or_baseline_rescores(admin_client, demo, monkeypatch):
    run_scan(admin_client, monkeypatch, "lab_standard.xml")
    before = scores(admin_client)["CS-0004"]["risk_score"]  # FTP is drift
    res = admin_client.patch(f"{ASSETS}/4", json={"baseline_ports": [21, 22]})
    assert res.json()["risk_score"] < before
    res = admin_client.patch(f"{ASSETS}/4", json={"data_sensitivity": 3, "users_affected": 3})
    assert res.json()["risk_score"] > before


def test_registering_removes_inventory_points(admin_client, demo, monkeypatch):
    run_scan(admin_client, monkeypatch, "lab_standard.xml")
    rogue = admin_client.get(ASSETS, params={"status": "unregistered"}).json()[0]
    res = admin_client.post(
        f"{ASSETS}/{rogue['id']}/register",
        json={"name": "Robotics Club Pi", "asset_type": "other", "baseline_ports": [6379, 8080],
              "mac_address": rogue["mac_address"], "ip_address": rogue["ip_address"]},
    )  # fmt: skip
    detail = admin_client.get(f"{ASSETS}/{rogue['id']}").json()
    inventory = detail["risk"]["components"][4]
    assert inventory["points"] == 0
    assert res.json()["risk_score"] < rogue["risk_score"]
    assert [p["score"] for p in detail["risk_history"]][-1] == res.json()["risk_score"]


def test_retired_assets_are_not_scored(admin_client, demo, monkeypatch):
    run_scan(admin_client, monkeypatch, "lab_standard.xml")
    res = admin_client.patch(f"{ASSETS}/5", json={"status": "retired"})
    assert res.json()["risk_score"] is None
    assert admin_client.get(f"{ASSETS}/5").json()["risk"] is None


def test_never_scanned_asset_still_gets_a_score(admin_client, demo):
    res = admin_client.post(ASSETS, json={"name": "Library Kiosk", "asset_type": "workstation"})
    # only the six unconfirmed controls: 20 points x 1.15 (default criticality 8/12)
    assert res.json()["risk_score"] == 23.0
    assert res.json()["risk_band"] == "low"


def test_summary_and_ranking(auditor_client, admin_client, demo, monkeypatch):
    run_scan(admin_client, monkeypatch, "lab_deep.xml", "deep")
    summary = auditor_client.get(f"{RISK}/summary").json()
    assert summary["assessed"] == 7
    assert sum(summary["bands"].values()) == 7
    assert summary["top"][0]["asset_tag"] == "CS-0007"  # rogue Pi is the riskiest
    drivers = summary["drivers"]
    assert abs(sum(d["share"] for d in drivers) - 1) < 0.01
    assert drivers == sorted(drivers, key=lambda d: -d["points"])
    by_key = {d["key"]: d["points"] for d in drivers}
    assert by_key["controls"] == 7 * 20  # nothing confirmed yet on any of 7 assets
    assert by_key["inventory"] == 20  # one unregistered device
    listed = auditor_client.get(ASSETS).json()
    assert listed[0]["status"] == "unregistered"
    registered = [a["risk_score"] for a in listed if a["status"] == "registered"]
    assert registered == sorted(registered, reverse=True)  # riskiest first


def test_model_endpoint_publishes_the_rules(auditor_client, demo):
    model = auditor_client.get(f"{RISK}/model").json()
    assert model["version"] == rules.MODEL_VERSION
    assert len(model["cves"]) == len(rules.CVE_REFERENCE)
    assert model["cves"][0]["cvss"] >= model["cves"][-1]["cvss"]  # sorted by severity
    assert [c["cap"] for c in model["components"]] == [40, 40, 10, 20, 20]


def test_startup_rescores_when_model_version_changes(db, demo, monkeypatch):
    assert rescore_outdated(db) == 6  # demo assets had no score yet
    assert rescore_outdated(db) == 0
    monkeypatch.setattr(rules, "MODEL_VERSION", rules.MODEL_VERSION + 1)
    assert rescore_outdated(db) == 6


def test_cve_seed_is_idempotent(db):
    assert seed_cve_refs(db) == len(rules.CVE_REFERENCE)
    assert seed_cve_refs(db) == 0


def test_scoring_failure_does_not_lose_the_scan(admin_client, demo, monkeypatch, db):
    def broken(*_, **__):
        raise RuntimeError("scoring bug")

    monkeypatch.setattr(scan_service, "score_scan", broken)
    scan_id = run_scan(admin_client, monkeypatch, "lab_standard.xml")
    scan = db.get(Scan, scan_id)
    db.refresh(scan)
    assert scan.status == "failed" and "scoring bug" in scan.error
