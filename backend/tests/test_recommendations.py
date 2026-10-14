"""Recommendations are pure functions of score breakdowns: no database needed."""

from dataclasses import dataclass, field

from app.services.report.recommendations import recommend


@dataclass
class FakeAsset:
    tag: str
    label: str
    ip: str | None = "172.25.0.10"
    status: str = "registered"
    band: str = "high"
    multiplier: float = 1.0
    components: list[dict] = field(default_factory=list)


def component(key: str, cap: int, *items: dict) -> dict:
    return {"key": key, "label": key.title(), "cap": cap, "items": list(items)}


def cve(cve_id: str, cvss: float, points: int, severity: str = "critical") -> dict:
    return {
        "kind": "cve",
        "label": f"{cve_id} in Apache httpd 2.4.49 (CVSS {cvss})",
        "points": points,
        "severity": severity,
        "port": 80,
        "cve_id": cve_id,
        "detail": "Path traversal (identified in scan #3)",
    }


def gap(label: str) -> dict:
    return {"kind": "control_gap", "label": label, "points": 4}


def port(label: str, number: int, points: int, severity: str = "high") -> dict:
    return {
        "kind": "risky_port",
        "label": f"{label} ({number}/tcp)",
        "points": points,
        "severity": severity,
        "port": number,
    }


def test_cves_of_one_software_become_one_upgrade_capped_like_the_score():
    web = FakeAsset(
        "CS-0002",
        "CS-0002 Department Website",
        multiplier=1.5,
        components=[
            component(
                "vulnerabilities",
                40,
                cve("CVE-2021-42013", 9.8, 30),
                cve("CVE-2021-41773", 7.5, 20, "high"),
            )
        ],
    )
    [rec] = recommend([web])
    assert rec.action == "Upgrade Apache httpd 2.4.49 to a supported, patched release"
    assert rec.priority == "critical"  # the worst CVE sets the priority
    assert rec.reason == (
        "Fixes 2 known vulnerabilities (CVE-2021-42013, CVE-2021-41773); highest CVSS 9.8."
    )
    assert rec.points == 60  # 30 + 20 = 50, capped at 40, x 1.5
    assert rec.assets == ["CS-0002 Department Website (port 80)"]


def test_same_service_on_two_assets_is_one_action_listing_both():
    cam = FakeAsset(
        "CS-0006",
        "CS-0006 CCTV",
        components=[component("exposure", 40, port("Telnet: cleartext remote login", 23, 15))],
    )
    pc = FakeAsset(
        "CS-0004",
        "CS-0004 Lab PC",
        multiplier=0.8,
        components=[component("exposure", 40, port("Telnet: cleartext remote login", 2323, 15))],
    )
    [rec] = recommend([cam, pc])
    assert rec.action == "Disable Telnet and administer the device over SSH"
    assert rec.assets == ["CS-0006 CCTV (port 23)", "CS-0004 Lab PC (port 2323)"]
    assert rec.points == 27  # 15 x 1.0 + 15 x 0.8


def test_minor_exposure_is_not_worth_an_action():
    asset = FakeAsset(
        "CS-0001",
        "CS-0001 ERP",
        components=[component("exposure", 40, port("SSH remote administration exposed", 22, 2))],
    )
    assert recommend([asset]) == []


def test_unregistered_device_gets_a_register_action_not_checklist_actions():
    gap = {"kind": "control_gap", "label": "Host firewall enabled: not confirmed", "points": 4}
    rogue = FakeAsset(
        "CS-0007",
        "CS-0007 (unknown device)",
        ip="172.25.0.66",
        status="unregistered",
        band="critical",
        components=[
            component("controls", 24, gap),
            component(
                "inventory",
                20,
                {"kind": "unregistered", "label": "Device is not registered", "points": 20},
            ),
        ],
    )
    [rec] = recommend([rogue])
    assert rec.kind == "unregistered" and rec.priority == "critical"
    assert "172.25.0.66" in rec.action


def test_checklist_gaps_split_into_implement_and_confirm():
    asset = FakeAsset(
        "CS-0001",
        "CS-0001 ERP",
        components=[
            component(
                "controls",
                24,
                gap("Multi-factor authentication: not in place"),
                gap("Disk encryption: not confirmed"),
                gap("Host firewall enabled: not confirmed"),
            )
        ],
    )
    implement, confirm = recommend([asset])
    assert implement.action == "Implement: Multi-factor authentication"
    assert implement.priority == "medium"
    assert confirm.priority == "low"
    assert confirm.assets == ["CS-0001 ERP (2 controls)"]


def test_order_is_priority_first_then_points():
    asset = FakeAsset(
        "CS-0003",
        "CS-0003 DB",
        components=[
            component(
                "exposure",
                40,
                port("Web interface without TLS", 80, 4, "low"),
                port("MySQL database reachable from the network", 3306, 10, "medium"),
                port("Telnet: cleartext remote login", 23, 15),
                port("RTSP camera stream exposed", 554, 6, "low"),
            )
        ],
    )
    assert [(r.priority, r.points) for r in recommend([asset])] == [
        ("high", 15),
        ("medium", 10),
        ("low", 6),
        ("low", 4),
    ]
