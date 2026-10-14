import xml.etree.ElementTree as ET

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import Alert, AuditLog, Scan
from app.services import scans as scan_service
from app.services.alerts import notify
from app.services.risk.service import seed_cve_refs
from app.services.scanner.profiles import covered_ports
from app.services.seed import seed_demo_assets
from tests.conftest import FIXTURES

ALERTS = "/api/v1/alerts"
SERVICE_KEY = {"X-API-Key": get_settings().service_api_key}


def lab_xml(
    *,
    drop: tuple[str, ...] = (),
    add_port: tuple[str, int, str] | None = None,
    mac: tuple[str, str] | None = None,
) -> str:
    """The recorded standard lab scan, edited: hosts dropped, a port added, a MAC changed."""
    root = ET.parse(FIXTURES / "lab_standard.xml").getroot()
    for host in root.findall("host"):
        ip = host.find("address[@addrtype='ipv4']").get("addr")
        if ip in drop:
            root.remove(host)
        if add_port and ip == add_port[0]:
            port = ET.SubElement(
                host.find("ports"), "port", protocol="tcp", portid=str(add_port[1])
            )
            ET.SubElement(port, "state", state="open", reason="syn-ack", reason_ttl="64")
            ET.SubElement(port, "service", name=add_port[2], method="probed", conf="10")
        if mac and ip == mac[0]:
            host.find("address[@addrtype='mac']").set("addr", mac[1])
    return ET.tostring(root, encoding="unicode")


@pytest.fixture
def lab(db, admin_client, monkeypatch, webhook):
    """Run scans against edited versions of the recorded lab. Returns run(xml, profile)."""
    seed_demo_assets(db)
    seed_cve_refs(db)

    def run(xml: str | None = None, profile: str = "standard", target: str = "172.25.0.0/24"):
        text = xml or lab_xml()
        monkeypatch.setattr(scan_service, "nmap_runner", lambda *a: text)
        res = admin_client.post("/api/v1/scans", json={"target": target, "profile": profile})
        assert res.status_code == 202, res.text
        scan_id = res.json()["id"]
        db.expire_all()
        assert db.get(Scan, scan_id).status == "completed"
        return scan_id

    return run


def alerts_of(db, scan_id: int) -> list[Alert]:
    db.expire_all()
    return list(db.scalars(select(Alert).where(Alert.scan_id == scan_id).order_by(Alert.id)))


def test_profiles_know_which_ports_they_probe():
    assert {21, 23, 6379, 8080} <= covered_ports("quick")
    assert 631 not in covered_ports("quick")
    assert set(range(1, 1025)) <= covered_ports("standard") == covered_ports("deep")


def test_first_scan_reports_the_rogue_device_and_pushes_it_to_n8n(lab, db, webhook):
    scan_id = lab()
    [alert] = alerts_of(db, scan_id)  # registered devices have no earlier scan to differ from
    assert alert.kind == "new_device" and alert.severity == "high"
    assert alert.title == "Unregistered device at 172.25.0.66"
    assert "Raspberry Pi Foundation" in alert.message and "6379/tcp (redis)" in alert.message
    assert alert.delivery["webhook"] == "sent"

    [call] = webhook
    assert call["headers"]["X-CampusShield-Secret"] == "s3cret"
    event = call["payload"]
    assert event["event"] == "alerts.created" and event["scan"]["id"] == scan_id
    assert [a["id"] for a in event["alerts"]] == [alert.id]
    assert event["alerts"][0]["url"].endswith(f"/alerts?focus={alert.id}")
    assert db.get(Scan, scan_id).summary["alerts"] == 1


def test_an_identical_rescan_raises_nothing(lab, db, webhook):
    lab()
    assert alerts_of(db, lab()) == []
    assert len(webhook) == 1


def test_port_opened_then_closed_again_resolves_itself(lab, db):
    lab()
    opened = lab(lab_xml(add_port=("172.25.0.20", 23, "telnet")))
    port_alert = next(a for a in alerts_of(db, opened) if a.kind == "port_opened")
    assert port_alert.severity == "high"
    assert port_alert.title == "Port 23/tcp (telnet) opened on CS-0004 Lab 3 Workstation 01"
    assert "Not in the approved baseline" in port_alert.message

    closed = lab()
    db.refresh(port_alert)
    assert port_alert.status == "resolved"
    assert port_alert.resolution == f"Port closed again in scan #{closed}"
    assert not [a for a in alerts_of(db, closed) if a.kind == "port_closed"]  # no double report


def test_closing_a_port_nobody_was_alerted_about_is_info(lab, db):
    lab(lab_xml(add_port=("172.25.0.20", 23, "telnet")))  # first scan: open from the start
    closed = lab()
    [alert] = [a for a in alerts_of(db, closed) if a.kind == "port_closed"]
    assert alert.severity == "info" and alert.payload["port"] == 23
    assert alert.message == f"Open in scan #{closed - 1}, closed in scan #{closed}."


def test_no_port_changes_claimed_outside_what_both_scans_probed(lab, db):
    lab(profile="quick")
    # a standard audit finds 631, which the quick sweep never probed: not "opened"
    standard = lab(lab_xml(add_port=("172.25.0.20", 631, "ipp")))
    assert not [a for a in alerts_of(db, standard) if a.kind.startswith("port_")]
    # a quick sweep does not probe 631 either: not "closed"
    quick = lab(profile="quick")
    assert not [a for a in alerts_of(db, quick) if a.kind.startswith("port_")]


def test_missing_host_is_reported_once_and_resolves_when_back(lab, db, webhook):
    lab()
    gone = lab(lab_xml(drop=("172.25.0.30",)))
    [missing] = [a for a in alerts_of(db, gone) if a.kind == "host_missing"]
    assert missing.title == "CS-0005 Wi-Fi AP Block A did not respond"
    assert missing.severity == "medium"  # criticality below 10/12

    assert not [
        a for a in alerts_of(db, lab(lab_xml(drop=("172.25.0.30",)))) if a.kind == "host_missing"
    ]
    back = lab()
    db.refresh(missing)
    assert missing.status == "resolved" and missing.resolution == f"Responded again in scan #{back}"


def test_scanning_one_address_does_not_report_the_rest_missing(lab, db):
    lab()
    single = lab(lab_xml(drop=tuple(f"172.25.0.{n}" for n in (11, 12, 20, 30, 40, 66))),
                 target="172.25.0.10")  # fmt: skip
    assert alerts_of(db, single) == []


def test_different_mac_on_a_registered_address_is_critical(lab, db):
    lab()
    swapped = lab(lab_xml(mac=("172.25.0.12", "DE:AD:BE:EF:00:12")))
    conflict = next(a for a in alerts_of(db, swapped) if a.kind == "new_device")
    assert conflict.severity == "critical" and conflict.payload["ip_conflict"] is True
    assert "CS-0003 Student Records Database" in conflict.title


def test_risk_jump_explains_what_changed(lab, db):
    lab()
    jumped = lab(lab_xml(add_port=("172.25.0.30", 23, "telnet")))
    [jump] = [a for a in alerts_of(db, jumped) if a.kind == "risk_jump"]
    assert jump.payload["after"] - jump.payload["before"] >= 10
    assert jump.title.startswith("Risk of CS-0005 Wi-Fi AP Block A rose from")
    assert "Network exposure +15" in jump.message

    calm = lab()
    db.refresh(jump)
    assert jump.status == "resolved" and jump.resolution.startswith("Risk back to ")
    assert jump.resolution.endswith(f"in scan #{calm}")


def test_registering_the_device_resolves_its_alert(lab, db, admin_client):
    [alert] = alerts_of(db, lab())
    fields = {"name": "Library kiosk", "asset_type": "workstation", "baseline_ports": [8080],
              "data_sensitivity": 1, "service_dependency": 1, "users_affected": 1,
              "replaceability": 1}  # fmt: skip
    assert (
        admin_client.post(f"/api/v1/assets/{alert.asset_id}/register", json=fields).status_code
        == 200
    )
    db.refresh(alert)
    assert alert.status == "resolved" and alert.resolution == "Registered by Campus IT Admin"


def test_below_threshold_alerts_are_kept_but_not_pushed(lab, db, admin_client, webhook):
    res = admin_client.put(f"{ALERTS}/settings", json={"min_severity": "critical"})
    assert res.json()["min_severity"] == "critical"
    [alert] = alerts_of(db, lab())
    assert alert.delivery["webhook"] == "below_threshold" and webhook == []


def test_scan_completes_when_n8n_is_missing_or_broken(lab, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "n8n_webhook_url", None)
    [alert] = alerts_of(db, lab())
    assert alert.delivery["webhook"] == "not_configured"

    def boom(*_):
        raise RuntimeError("network down")

    monkeypatch.setattr(get_settings(), "n8n_webhook_url", "http://n8n/webhook")
    monkeypatch.setattr(notify, "post_webhook", boom)
    lab(lab_xml(add_port=("172.25.0.20", 23, "telnet")))  # asserts the scan completed


def test_review_workflow_and_permissions(lab, db, admin_client, auditor_client):
    lab()
    lab(lab_xml(drop=("172.25.0.30",), add_port=("172.25.0.20", 23, "telnet")))
    page = auditor_client.get(ALERTS, params={"unresolved": True}).json()
    assert page["total"] >= 3
    summary = auditor_client.get(f"{ALERTS}/summary").json()
    assert summary["open"] == page["total"] and summary["by_severity"]["high"] >= 2

    first = page["items"][0]["id"]
    assert auditor_client.post(f"{ALERTS}/{first}/acknowledge").status_code == 403
    acked = admin_client.post(f"{ALERTS}/{first}/acknowledge").json()
    assert acked["status"] == "acknowledged" and acked["acknowledged_by"] == "Campus IT Admin"
    assert admin_client.post(f"{ALERTS}/{first}/acknowledge").status_code == 409

    done = admin_client.post(f"{ALERTS}/{first}/resolve", json={"note": "AP rebooted"}).json()
    assert done["status"] == "resolved" and done["resolution"] == "AP rebooted"
    assert (
        admin_client.post(f"{ALERTS}/acknowledge-all").json()["acknowledged"] == page["total"] - 1
    )
    assert auditor_client.get(f"{ALERTS}/summary").json()["open"] == 0
    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.action.startswith("alert."))))
    assert {"alert.raised", "alert.acknowledged", "alert.resolved"} <= actions

    kinds = auditor_client.get(ALERTS, params={"kind": "host_missing"}).json()["items"]
    assert {a["kind"] for a in kinds} == {"host_missing"}
    assert kinds[0]["asset"]["asset_tag"] == "CS-0005"


def test_n8n_starts_scans_with_the_service_key_only(client, lab, db):
    assert client.post("/api/v1/automation/scans", json={}).status_code == 401
    bad = client.post("/api/v1/automation/scans", json={}, headers={"X-API-Key": "nope"})
    assert bad.status_code == 401
    res = client.post("/api/v1/automation/scans", json={"profile": "quick"}, headers=SERVICE_KEY)
    assert res.status_code == 202
    scan = db.get(Scan, res.json()["id"])
    assert scan.triggered_by == "n8n" and scan.target == "172.25.0.0/24"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "scan.started"))
    assert entry.actor == "n8n"


def test_delivery_reports_from_n8n(client, lab, db, auditor_client):
    [alert] = alerts_of(db, lab())
    ok = {"alert_ids": [alert.id], "channel": "telegram", "ok": True}
    assert client.post("/api/v1/automation/delivery", json=ok).status_code == 401
    assert (
        client.post("/api/v1/automation/delivery", json=ok, headers=SERVICE_KEY).status_code == 204
    )
    failed = {"alert_ids": [alert.id], "channel": "email", "ok": False, "error": "SMTP refused"}
    client.post("/api/v1/automation/delivery", json=failed, headers=SERVICE_KEY)

    db.refresh(alert)
    assert alert.delivered_at is not None
    assert alert.delivery["channels"]["telegram"]["ok"] is True
    assert alert.delivery_error == "email: SMTP refused"
    channels = auditor_client.get(f"{ALERTS}/settings").json()["channels"]
    assert channels["telegram"]["ok"] and not channels["email"]["ok"]


def test_test_alert_goes_through_the_webhook(admin_client, auditor_client, webhook):
    assert auditor_client.post(f"{ALERTS}/test").status_code == 403
    assert admin_client.post(f"{ALERTS}/test").json() == {"state": "sent", "error": None}
    event = webhook[0]["payload"]
    assert event["test"] is True and event["event"] == "test"
    assert webhook[0]["headers"]["X-CampusShield-Event"] == "test"
    settings = admin_client.get(f"{ALERTS}/settings").json()
    assert settings["webhook_configured"] and settings["webhook_host"] == "n8n:5678"
    assert (
        admin_client.put(f"{ALERTS}/settings", json={"min_severity": "urgent"}).status_code == 422
    )
