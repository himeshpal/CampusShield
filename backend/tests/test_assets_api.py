import pytest
from sqlalchemy import select

from app.models import Asset, AuditLog, ScanHost
from app.services.seed import seed_demo_assets

ASSETS = "/api/v1/assets"
SCANS = "/api/v1/scans"
NEW_ASSET = {
    "name": "Library Kiosk",
    "asset_type": "workstation",
    "ip_address": "172.25.0.90",
    "mac_address": "AA-BB-CC-00-00-90",
    "department": "Library",
    "location": "Ground floor",
    "owner": "Librarian",
    "data_sensitivity": 1,
    "service_dependency": 2,
    "users_affected": 3,
    "replaceability": 1,
    "baseline_ports": [3389, 22, 22],
}


@pytest.fixture
def demo(db):
    seed_demo_assets(db)


@pytest.fixture
def scanned(admin_client, demo, fake_nmap):
    """The demo inventory plus one completed lab scan (recorded nmap output)."""
    return admin_client.post(SCANS, json={"target": "172.25.0.0/24"}).json()["id"]


def test_seed_demo_assets_is_idempotent(db):
    assert seed_demo_assets(db) == 6
    assert seed_demo_assets(db) == 0


def test_scan_creates_unregistered_rogue_and_summary_counts(auditor_client, scanned):
    summary = auditor_client.get(f"{ASSETS}/summary").json()
    assert summary["registered"] == 6 and summary["unregistered"] == 1
    assert summary["by_type"]["server"] == 3

    assets = auditor_client.get(ASSETS).json()
    assert assets[0]["status"] == "unregistered"  # needs attention -> listed first
    assert assets[0]["ip_address"] == "172.25.0.66"


def test_list_includes_criticality_and_latest_observation(auditor_client, scanned):
    erp = next(a for a in auditor_client.get(ASSETS).json() if a["asset_tag"] == "CS-0001")
    assert erp["criticality"] == 11 and erp["criticality_level"] == "high"
    assert [p["port"] for p in erp["observed_ports"]] == [80, 443]
    assert erp["last_scan_id"] == scanned

    lab_pc = next(a for a in auditor_client.get(ASSETS).json() if a["asset_tag"] == "CS-0004")
    assert lab_pc["baseline_ports"] == [22]
    assert {p["port"] for p in lab_pc["observed_ports"]} == {21, 22}  # FTP is drift


@pytest.mark.parametrize(
    ("params", "expected_tags"),
    [
        ({"status": "unregistered"}, {"CS-0007"}),
        ({"asset_type": "iot_cctv"}, {"CS-0006"}),
        ({"q": "raspberry"}, {"CS-0007"}),
        ({"q": "Server Room"}, {"CS-0001", "CS-0002", "CS-0003"}),
        ({"q": "172.25.0.30"}, {"CS-0005"}),
    ],
)
def test_filters_and_search(auditor_client, scanned, params, expected_tags):
    found = {a["asset_tag"] for a in auditor_client.get(ASSETS, params=params).json()}
    assert found == expected_tags


def test_detail_has_observation_history(auditor_client, scanned, admin_client, fake_nmap):
    admin_client.post(SCANS, json={"target": "172.25.0.0/24"})  # second scan
    detail = auditor_client.get(f"{ASSETS}/2").json()
    assert detail["name"] == "Department Website"
    assert len(detail["observations"]) == 2
    first = detail["observations"][0]
    assert first["match_method"] == "mac"
    assert first["ports"][0]["product"] == "Apache httpd"


def test_create_normalises_and_audits(admin_client, demo, db):
    res = admin_client.post(ASSETS, json=NEW_ASSET)
    assert res.status_code == 201
    body = res.json()
    assert body["asset_tag"] == "CS-0007" and body["status"] == "registered"
    assert body["mac_address"] == "aa:bb:cc:00:00:90"
    assert body["baseline_ports"] == [22, 3389]
    assert body["criticality"] == 7
    assert db.scalar(select(AuditLog).where(AuditLog.action == "asset.created"))


@pytest.mark.parametrize(
    "bad",
    [
        {"ip_address": "999.1.1.1"},
        {"mac_address": "not-a-mac"},
        {"data_sensitivity": 4},
        {"asset_type": "toaster"},
        {"baseline_ports": [70000]},
        {"name": "x"},
    ],
)
def test_create_validation(admin_client, bad):
    assert admin_client.post(ASSETS, json=NEW_ASSET | bad).status_code == 422


def test_duplicate_mac_rejected(admin_client, demo):
    res = admin_client.post(ASSETS, json=NEW_ASSET | {"mac_address": "3c:d9:2b:10:00:10"})
    assert res.status_code == 409
    assert "CS-0001" in res.json()["detail"]


def test_register_rogue_device(admin_client, scanned, db):
    rogue = admin_client.get(ASSETS, params={"status": "unregistered"}).json()[0]
    res = admin_client.post(
        f"{ASSETS}/{rogue['id']}/register",
        json={
            "name": "Robotics Club Pi",
            "asset_type": "other",
            "ip_address": rogue["ip_address"],
            "mac_address": rogue["mac_address"],
            "department": "Robotics Club",
            "owner": "Club coordinator",
            "baseline_ports": [8080],
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "registered"
    assert admin_client.get(f"{ASSETS}/summary").json()["unregistered"] == 0
    # its past observations now count as registered
    hosts = db.scalars(select(ScanHost).where(ScanHost.asset_id == rogue["id"])).all()
    assert hosts and all(h.is_registered for h in hosts)
    assert db.scalar(select(AuditLog).where(AuditLog.action == "asset.registered"))
    # registering twice is refused
    again = admin_client.post(f"{ASSETS}/{rogue['id']}/register", json=NEW_ASSET)
    assert again.status_code == 409


def test_retire_and_update(admin_client, demo, db):
    res = admin_client.patch(f"{ASSETS}/4", json={"status": "retired", "notes": "Lab PC replaced"})
    assert res.status_code == 200 and res.json()["status"] == "retired"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "asset.retired"))
    res = admin_client.patch(f"{ASSETS}/5", json={"location": "Block B", "users_affected": 1})
    assert res.json()["location"] == "Block B" and res.json()["criticality"] == 5


def test_auditor_is_read_only(auditor_client, demo):
    assert auditor_client.get(ASSETS).status_code == 200
    assert auditor_client.post(ASSETS, json=NEW_ASSET).status_code == 403
    assert auditor_client.patch(f"{ASSETS}/1", json={"name": "Hacked"}).status_code == 403
    assert auditor_client.post(f"{ASSETS}/1/register", json=NEW_ASSET).status_code == 403


def test_scan_detail_shows_match_information(auditor_client, scanned):
    detail = auditor_client.get(f"{SCANS}/{scanned}").json()
    assert (detail["matched"], detail["new_devices"]) == (6, 1)
    rogue = next(h for h in detail["hosts"] if h["ip_address"] == "172.25.0.66")
    assert rogue["match_method"] == "new"
    assert rogue["asset"]["status"] == "unregistered"
    web = next(h for h in detail["hosts"] if h["ip_address"] == "172.25.0.11")
    assert web["asset"]["asset_tag"] == "CS-0002"


def test_missing_asset_404(auditor_client):
    assert auditor_client.get(f"{ASSETS}/999").status_code == 404


def test_startup_backfill_matches_old_scans(db):
    from app.models import Scan
    from app.services.matching import backfill_unmatched_scans

    scan = Scan(target="172.25.0.0/24", profile="quick", status="completed")
    scan.hosts.append(ScanHost(ip_address="172.25.0.99", mac_address="aa:00:00:00:00:99"))
    db.add(scan)
    db.commit()
    assert backfill_unmatched_scans(db) == 1
    assert backfill_unmatched_scans(db) == 0  # idempotent
    assert db.scalar(select(Asset).where(Asset.ip_address == "172.25.0.99")).status == (
        "unregistered"
    )
