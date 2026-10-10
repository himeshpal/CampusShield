"""Asset-scan matching rules and device-type suggestion."""

import pytest
from sqlalchemy import func, select

from app.models import Asset, AuditLog, Scan, ScanHost, ScanPort
from app.models.base import utcnow
from app.services.classify import suggest_asset_type
from app.services.matching import match_scan, next_asset_tag
from app.services.seed import seed_demo_assets


def _scan(db, *hosts: dict) -> Scan:
    """A completed scan with the given hosts: {ip, mac?, vendor?, ports?}."""
    scan = Scan(target="172.25.0.0/24", profile="quick", status="completed", started_at=utcnow())
    for h in hosts:
        scan.hosts.append(
            ScanHost(
                ip_address=h["ip"],
                mac_address=h.get("mac"),
                mac_vendor=h.get("vendor"),
                ports=[ScanPort(port=p, protocol="tcp", state="open") for p in h.get("ports", [])],
            )
        )
    db.add(scan)
    db.flush()
    return scan


def _asset(db, **fields) -> Asset:
    fields.setdefault("status", "registered")
    asset = Asset(asset_tag=next_asset_tag(db), name="Test", **fields)
    db.add(asset)
    db.flush()
    return asset


def test_mac_match_links_registered_asset(db):
    asset = _asset(db, ip_address="172.25.0.10", mac_address="3c:d9:2b:10:00:10")
    scan = _scan(db, {"ip": "172.25.0.10", "mac": "3c:d9:2b:10:00:10"})
    summary = match_scan(db, scan)
    host = scan.hosts[0]
    assert (host.asset_id, host.match_method, host.is_registered) == (asset.id, "mac", True)
    assert summary.matched == 1 and summary.new_devices == []
    assert asset.last_seen_at is not None


def test_mac_match_follows_dhcp_ip_change(db):
    asset = _asset(db, ip_address="172.25.0.10", mac_address="3c:d9:2b:10:00:10")
    summary = match_scan(db, _scan(db, {"ip": "172.25.0.77", "mac": "3c:d9:2b:10:00:10"}))
    assert asset.ip_address == "172.25.0.77"
    assert summary.ip_changes == 1


def test_ip_match_when_mac_unknown_and_mac_is_learned(db):
    asset = _asset(db, ip_address="172.25.0.20", mac_address=None)
    scan = _scan(db, {"ip": "172.25.0.20", "mac": "18:db:f2:20:00:20"})
    match_scan(db, scan)
    assert scan.hosts[0].match_method == "ip"
    assert asset.mac_address == "18:db:f2:20:00:20"


def test_same_ip_different_mac_is_an_ip_conflict(db):
    registered = _asset(db, ip_address="172.25.0.12", mac_address="3c:d9:2b:10:00:12")
    scan = _scan(db, {"ip": "172.25.0.12", "mac": "de:ad:be:ef:00:01", "vendor": "Unknown"})
    summary = match_scan(db, scan)

    host = scan.hosts[0]
    assert host.match_method == "ip_conflict"
    assert host.asset_id != registered.id
    assert db.get(Asset, host.asset_id).status == "unregistered"
    assert summary.ip_conflicts == [host.asset_id]
    assert registered.last_seen_at is None  # the registered device was NOT seen


def test_unknown_host_becomes_unregistered_asset_with_suggested_type(db):
    scan = _scan(
        db,
        {"ip": "172.25.0.66", "mac": "b8:27:eb:66:00:66", "vendor": "Raspberry Pi Foundation",
         "ports": [6379, 8080]},
    )  # fmt: skip
    summary = match_scan(db, scan)
    asset = db.get(Asset, scan.hosts[0].asset_id)
    assert asset.status == "unregistered"
    assert asset.asset_tag.startswith("CS-")
    assert asset.baseline_ports == [6379, 8080]
    assert asset.asset_type == "server"  # Redis port -> server
    assert asset.first_seen_at == asset.last_seen_at
    assert summary.new_devices == [asset.id]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "asset.discovered"))


def test_rogue_device_seen_again_is_not_duplicated(db):
    rogue = {"ip": "172.25.0.66", "mac": "b8:27:eb:66:00:66"}
    match_scan(db, _scan(db, rogue))
    second = _scan(db, rogue)
    summary = match_scan(db, second)
    assert db.scalar(select(func.count(Asset.id))) == 1
    assert second.hosts[0].match_method == "mac"
    assert summary.new_devices == []


def test_two_new_devices_in_one_scan_get_distinct_tags(db):
    scan = _scan(db, {"ip": "172.25.0.70", "mac": "aa:aa:aa:00:00:01"},
                 {"ip": "172.25.0.71", "mac": "aa:aa:aa:00:00:02"})  # fmt: skip
    match_scan(db, scan)
    tags = {db.get(Asset, h.asset_id).asset_tag for h in scan.hosts}
    assert len(tags) == 2


def test_retired_asset_is_not_matched_by_ip(db):
    _asset(db, ip_address="172.25.0.30", mac_address=None, status="retired")
    scan = _scan(db, {"ip": "172.25.0.30", "mac": "24:a4:3c:30:00:30"})
    match_scan(db, scan)
    assert scan.hosts[0].match_method == "new"


def test_demo_lab_scan_flags_only_the_raspberry_pi(db):
    from app.services.scanner.parser import parse_nmap_xml
    from tests.conftest import FIXTURES

    seed_demo_assets(db)
    parsed = parse_nmap_xml((FIXTURES / "lab_standard.xml").read_text())
    scan = _scan(db, *({"ip": h.ip, "mac": h.mac, "vendor": h.vendor,
                        "ports": [p.port for p in h.ports]} for h in parsed.hosts))  # fmt: skip
    summary = match_scan(db, scan)

    assert summary.matched == 6
    (new_id,) = summary.new_devices
    rogue = db.get(Asset, new_id)
    assert rogue.ip_address == "172.25.0.66"
    assert rogue.mac_vendor == "Raspberry Pi Foundation"
    assert scan.summary["new_devices"] == 1


@pytest.mark.parametrize(
    ("vendor", "ports", "expected"),
    [
        ("Hangzhou Hikvision Digital Technology", set(), "iot_cctv"),
        ("Ubiquiti", {22, 80}, "wifi_ap"),
        ("ZKTeco", {4370}, "iot_biometric"),
        ("Canon", set(), "printer"),
        ("Dell", {3389}, "workstation"),
        ("Hewlett Packard", {9100}, "printer"),
        ("Hewlett Packard", {3306}, "server"),
        (None, {554}, "iot_cctv"),
        ("Raspberry Pi Foundation", {6379, 8080}, "server"),
        (None, set(), "other"),
    ],
)
def test_asset_type_suggestion(vendor, ports, expected):
    assert suggest_asset_type(vendor, ports) == expected
