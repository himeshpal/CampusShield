from sqlalchemy import func, select

from app.core.security import hash_password, verify_password
from app.models import ChecklistItem, User
from app.services.seed import seed


def test_seed_is_idempotent(db):
    seed(db)
    seed(db)
    assert db.scalar(select(func.count(User.id))) == 2
    assert db.scalar(select(func.count(ChecklistItem.id))) == 6


def test_password_hashing_roundtrip():
    hashed = hash_password("Campus@2026")
    assert verify_password("Campus@2026", hashed)
    assert not verify_password("campus@2026", hashed)


def test_audit_log_lists_newest_first_with_filter(admin_client, client):
    client.post("/api/v1/auth/login", json={"email": "x@campus.local", "password": "bad"})
    res = admin_client.get("/api/v1/audit-log", params={"action": "auth."})
    assert res.status_code == 200
    body = res.json()
    actions = [i["action"] for i in body["items"]]
    assert actions[0] == "auth.login_failed"  # newest first
    assert all(a.startswith("auth.") for a in actions)
    assert body["total"] == len(actions)


def test_audit_log_pagination(admin_client):
    page = admin_client.get("/api/v1/audit-log", params={"limit": 1}).json()
    assert len(page["items"]) == 1
    assert page["total"] >= 3  # two seeded users + this login


def test_auditor_can_read_audit_log(auditor_client):
    assert auditor_client.get("/api/v1/audit-log").status_code == 200


def test_audit_log_requires_login(client):
    assert client.get("/api/v1/audit-log").status_code == 401
