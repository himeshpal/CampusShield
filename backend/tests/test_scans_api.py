from sqlalchemy import select

from app.models import AuditLog, Scan
from app.services import scans as scan_service
from app.services.scanner.runner import ScanCancelled, ScanFailed

SCANS = "/api/v1/scans"
LAB = {"target": "172.25.0.0/24", "profile": "standard"}


def test_options_list_profiles_and_scope(auditor_client):
    body = auditor_client.get(f"{SCANS}/options").json()
    assert [p["key"] for p in body["profiles"]] == ["quick", "standard", "deep"]
    assert body["default_target"] == "172.25.0.0/24"
    assert all(p["command"].startswith("nmap -n ") for p in body["profiles"])


def test_scan_runs_and_results_are_stored(admin_client, fake_nmap, db):
    res = admin_client.post(SCANS, json=LAB)
    assert res.status_code == 202
    scan_id = res.json()["id"]

    assert fake_nmap == [
        {"target": "172.25.0.0/24", "profile": "standard", "exclude": fake_nmap[0]["exclude"]}
    ]
    detail = admin_client.get(f"{SCANS}/{scan_id}").json()
    assert detail["status"] == "completed" and detail["progress"] == 100
    assert detail["hosts_up"] == 7 and detail["open_ports"] == 13
    assert detail["requested_by_name"] == "Campus IT Admin"
    apache = next(h for h in detail["hosts"] if h["ip_address"] == "172.25.0.11")
    assert apache["ports"][0]["product"] == "Apache httpd"
    assert apache["ports"][0]["version"] == "2.4.49"

    actions = list(db.scalars(select(AuditLog.action).where(AuditLog.entity_type == "scan")))
    assert actions == ["scan.started", "scan.completed"]


def test_out_of_scope_target_rejected_without_running_nmap(admin_client, fake_nmap):
    res = admin_client.post(SCANS, json={"target": "10.0.0.0/8", "profile": "quick"})
    assert res.status_code == 400
    assert "outside the authorised scan scope" in res.json()["detail"]
    assert fake_nmap == []


def test_unknown_profile_rejected(admin_client):
    assert admin_client.post(SCANS, json=LAB | {"profile": "aggressive"}).status_code == 422


def test_auditor_cannot_start_scans(auditor_client, fake_nmap):
    assert auditor_client.post(SCANS, json=LAB).status_code == 403
    assert fake_nmap == []


def test_only_one_scan_at_a_time(admin_client, monkeypatch):
    monkeypatch.setattr(scan_service, "dispatch", lambda fn: None)  # stays queued
    assert admin_client.post(SCANS, json=LAB).status_code == 202
    second = admin_client.post(SCANS, json=LAB)
    assert second.status_code == 409
    assert "still running" in second.json()["detail"]
    assert admin_client.get(f"{SCANS}/active").json()["status"] == "queued"


def test_cancel_stops_a_running_scan(admin_client, monkeypatch, db):
    monkeypatch.setattr(scan_service, "dispatch", lambda fn: None)
    scan_id = admin_client.post(SCANS, json=LAB).json()["id"]
    assert admin_client.post(f"{SCANS}/{scan_id}/cancel").status_code == 200

    def run(target, profile, exclude, on_progress, should_cancel):
        assert should_cancel()
        raise ScanCancelled("cancelled")

    monkeypatch.setattr(scan_service, "nmap_runner", run)
    scan_service.execute_scan(scan_id)
    assert admin_client.get(f"{SCANS}/{scan_id}").json()["status"] == "cancelled"
    # finished scans can't be cancelled again
    assert admin_client.post(f"{SCANS}/{scan_id}/cancel").status_code == 409


def test_nmap_failure_is_recorded_on_the_scan(admin_client, monkeypatch):
    def run(*_):
        raise ScanFailed("nmap exited with code 1: Failed to open device eth9")

    monkeypatch.setattr(scan_service, "nmap_runner", run)
    scan_id = admin_client.post(SCANS, json=LAB).json()["id"]
    detail = admin_client.get(f"{SCANS}/{scan_id}").json()
    assert detail["status"] == "failed"
    assert "Failed to open device" in detail["error"]
    assert admin_client.get(f"{SCANS}/active").json() is None  # a new scan may start


def test_restart_marks_interrupted_scans_failed(db):
    db.add(Scan(target="172.25.0.0/24", profile="quick", status="running"))
    db.commit()
    assert scan_service.recover_interrupted(db) == 1
    scan = db.scalar(select(Scan))
    assert scan.status == "failed" and "restarted" in scan.error


def test_scan_history_newest_first(admin_client, fake_nmap):
    for profile in ("quick", "standard"):
        admin_client.post(SCANS, json=LAB | {"profile": profile})
    history = admin_client.get(SCANS).json()
    assert [s["profile"] for s in history] == ["standard", "quick"]


def test_missing_scan_is_404(auditor_client):
    assert auditor_client.get(f"{SCANS}/999").status_code == 404
