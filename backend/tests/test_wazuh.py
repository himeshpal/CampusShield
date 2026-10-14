import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import Alert
from app.services.alerts.wazuh import severity_for
from app.services.risk.service import seed_cve_refs
from app.services.seed import seed_demo_assets

WAZUH = "/api/v1/automation/wazuh"
KEY = {"X-API-Key": get_settings().service_api_key}
AGENT = {"id": "001", "name": "lab-pc-01", "ip": "172.25.0.20"}


def event(rule_id: str, level: int, description: str, **extra) -> dict:
    """The shape wazuh-integratord hands to custom-campusshield (trimmed)."""
    return {
        "timestamp": "2026-10-14T07:30:00.000+0000",
        "rule": {"id": rule_id, "level": level, "description": description,
                 "groups": ["syslog"], "mitre": {"id": ["T1110"]}},
        "agent": AGENT,
        "id": "1791943000.12345",
        **extra,
    }  # fmt: skip


BAD_PASSWORD = event(
    "51003",
    5,
    "Dropbear: Bad password attempt.",
    data={"srcip": "172.25.0.66", "srcuser": "root"},
    full_log="Oct 14 07:30:00 lab-pc-01 dropbear[241]: Bad password attempt for 'root'",
)
BRUTE_FORCE = {
    **BAD_PASSWORD,
    "rule": {**BAD_PASSWORD["rule"], "id": "51007", "level": 10,
             "description": "Dropbear: brute force attempt."},
}  # fmt: skip


@pytest.fixture
def lab(db, admin_client, fake_nmap):
    seed_demo_assets(db)
    seed_cve_refs(db)
    admin_client.post("/api/v1/scans", json={"target": "172.25.0.0/24"})  # rogue .66 known


def test_levels_map_onto_severities():
    assert [severity_for(level) for level in (3, 5, 7, 10, 12, 15)] == [
        "info", "low", "medium", "high", "critical", "critical"
    ]  # fmt: skip


def test_brute_force_is_tied_to_the_host_and_the_attacking_device(client, lab, db, webhook):
    res = client.post(WAZUH, json=BRUTE_FORCE, headers=KEY)
    assert res.status_code == 202 and res.json()["created"] is True
    alert = db.get(Alert, res.json()["alert_id"])
    assert alert.kind == "wazuh" and alert.severity == "high"
    assert alert.title == "Dropbear: brute force attempt on CS-0004 Lab 3 Workstation 01"
    assert "Source 172.25.0.66: CS-0007, an unregistered device." in alert.message
    assert alert.payload["rule_id"] == "51007" and alert.payload["mitre"] == ["T1110"]
    assert alert.payload["source_asset_id"] is not None
    # pushed through the same n8n pipeline as scan alerts (after the response)
    assert any(c["payload"]["alerts"][0]["id"] == alert.id for c in webhook)


def test_repeats_are_merged_and_not_pushed_again(client, lab, db, webhook):
    first = client.post(WAZUH, json=BAD_PASSWORD, headers=KEY).json()
    for _ in range(8):
        again = client.post(WAZUH, json=BAD_PASSWORD, headers=KEY).json()
    assert again == {"alert_id": first["alert_id"], "created": False, "count": 9}
    assert (
        db.scalar(select(Alert).where(Alert.payload["rule_id"].as_string() == "51003")).delivery[
            "webhook"
        ]
        == "below_threshold"
    )  # level 5 = low: kept, not pushed
    assert webhook == [] or all(
        c["payload"]["alerts"][0]["id"] != first["alert_id"] for c in webhook
    )


def test_file_changes_collect_every_path(client, lab, db):
    for path in ("/etc/passwd", "/etc/shadow", "/etc/group"):
        res = client.post(
            WAZUH,
            json=event("100100", 10, "User accounts changed (account files modified)",
                       syscheck={"path": path, "event": "modified"}),
            headers=KEY,
        )  # fmt: skip
    alert = db.get(Alert, res.json()["alert_id"])
    assert alert.payload["count"] == 3
    assert alert.message.startswith("Files changed: /etc/passwd, /etc/shadow, /etc/group.")


def test_unknown_agent_address_still_creates_an_alert(client, db):
    stray = {**BRUTE_FORCE, "agent": {"id": "009", "name": "library-pc", "ip": "any"}}
    alert = db.get(Alert, client.post(WAZUH, json=stray, headers=KEY).json()["alert_id"])
    assert alert.asset_id is None and alert.title.endswith("on library-pc")
    assert "Source 172.25.0.66 (not in the inventory)." in alert.message


def test_only_the_manager_may_post(client, db):
    assert client.post(WAZUH, json=BRUTE_FORCE).status_code == 401
    assert client.post(WAZUH, json=BRUTE_FORCE, headers={"X-API-Key": "x"}).status_code == 401
    assert client.post(WAZUH, json={"hello": "world"}, headers=KEY).status_code == 422


def test_last_event_is_shown_in_settings(client, lab, auditor_client):
    client.post(WAZUH, json=BRUTE_FORCE, headers=KEY)
    status = auditor_client.get("/api/v1/alerts/settings").json()["wazuh"]
    assert status["last_agent"] == "lab-pc-01"
    assert status["last_rule"] == "Dropbear: brute force attempt."
    assert status["events"] == 1
