import pytest
from sqlalchemy import select

from app.models import AuditLog, ChecklistEntry
from app.services.risk.service import seed_cve_refs
from app.services.seed import seed_demo_assets

CHECKLIST = "/api/v1/checklist"
KEYS = ["firewall", "antivirus", "disk_encryption", "mfa", "patch_policy", "default_credentials"]


@pytest.fixture
def demo(db, admin_client, fake_nmap):
    seed_demo_assets(db)
    seed_cve_refs(db)
    admin_client.post("/api/v1/scans", json={"target": "172.25.0.0/24"})  # scores + rogue


def test_matrix_lists_registered_assets_with_every_control_unknown(auditor_client, demo):
    matrix = auditor_client.get(CHECKLIST).json()
    assert [i["key"] for i in matrix["items"]] == KEYS
    assert len(matrix["rows"]) == 6  # the unregistered rogue is not assessed
    row = matrix["rows"][0]
    assert set(row["entries"]) == set(KEYS)
    assert all(e["status"] == "unknown" for e in row["entries"].values())
    assert row["answered"] == 0 and row["risk_score"] is not None


def test_answering_a_control_lowers_risk_and_is_audited(admin_client, demo, db):
    res = admin_client.put(
        f"{CHECKLIST}/2/firewall", json={"status": "yes", "evidence": " ufw: only port 80 "}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["risk"]["after"] < body["risk"]["before"]  # every control counts (model v2)
    cell = body["row"]["entries"]["firewall"]
    assert cell["status"] == "yes" and cell["evidence"] == "ufw: only port 80"
    assert cell["updated_by"] == "Campus IT Admin" and body["row"]["answered"] == 1
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "checklist.updated"))
    assert entry.details["controls"] == {"firewall": {"from": "unknown", "to": "yes"}}


def test_no_and_unknown_cost_points_yes_and_na_do_not(admin_client, demo):
    base = admin_client.put(f"{CHECKLIST}/6/antivirus", json={"status": "unknown"}).json()
    na = admin_client.put(f"{CHECKLIST}/6/antivirus", json={"status": "na"}).json()
    no = admin_client.put(f"{CHECKLIST}/6/antivirus", json={"status": "no"}).json()
    assert na["risk"]["after"] < base["risk"]["after"]
    assert no["risk"]["after"] == base["risk"]["after"]  # "no" costs as much as unknown


def test_bulk_update_rescores_once(admin_client, demo, db):
    entries = [{"item_key": k, "status": "yes"} for k in KEYS]
    res = admin_client.put(f"{CHECKLIST}/1", json={"entries": entries})
    assert res.status_code == 200
    assert res.json()["row"]["answered"] == 6
    detail = admin_client.get("/api/v1/assets/1").json()
    controls = next(c for c in detail["risk"]["components"] if c["key"] == "controls")
    assert controls["points"] == 0
    assert (
        len(db.scalars(select(AuditLog).where(AuditLog.action == "checklist.updated")).all()) == 1
    )


def test_saving_the_same_answer_twice_changes_nothing(admin_client, demo, db):
    admin_client.put(f"{CHECKLIST}/3/mfa", json={"status": "no"})
    again = admin_client.put(f"{CHECKLIST}/3/mfa", json={"status": "no"}).json()
    assert again["risk"]["before"] == again["risk"]["after"]
    assert (
        len(db.scalars(select(AuditLog).where(AuditLog.action == "checklist.updated")).all()) == 1
    )


def test_summary_counts_coverage(admin_client, auditor_client, demo):
    admin_client.put(f"{CHECKLIST}/1/firewall", json={"status": "yes"})
    admin_client.put(f"{CHECKLIST}/2/firewall", json={"status": "no"})
    admin_client.put(f"{CHECKLIST}/6/antivirus", json={"status": "na"})
    summary = auditor_client.get(f"{CHECKLIST}/summary").json()
    assert (summary["assets"], summary["total"], summary["answered"], summary["gaps"]) == (
        6, 36, 3, 1,
    )  # fmt: skip
    firewall = next(c for c in summary["coverage"] if c["key"] == "firewall")
    assert firewall["counts"] == {"yes": 1, "no": 1, "na": 0, "unknown": 4}


@pytest.mark.parametrize(
    ("path", "body", "code"),
    [
        ("7/firewall", {"status": "yes"}, 409),  # unregistered rogue
        ("999/firewall", {"status": "yes"}, 404),
        ("1/telepathy", {"status": "yes"}, 404),
        ("1/firewall", {"status": "maybe"}, 422),
        ("1/firewall", {"status": "yes", "evidence": "x" * 501}, 422),
    ],
)
def test_validation(admin_client, demo, path, body, code):
    assert admin_client.put(f"{CHECKLIST}/{path}", json=body).status_code == code


def test_duplicate_keys_in_bulk_rejected(admin_client, demo):
    entries = [{"item_key": "mfa", "status": "yes"}, {"item_key": "mfa", "status": "no"}]
    assert admin_client.put(f"{CHECKLIST}/1", json={"entries": entries}).status_code == 422


def test_auditor_cannot_answer(auditor_client, demo, db):
    assert auditor_client.put(f"{CHECKLIST}/1/mfa", json={"status": "yes"}).status_code == 403
    assert db.scalar(select(ChecklistEntry)) is None
