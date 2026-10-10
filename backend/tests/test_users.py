from sqlalchemy import select

from app.models import AuditLog, User

USERS = "/api/v1/users"
NEW_USER = {
    "email": "hod.cse@campus.local",
    "full_name": "HOD Computer Engg",
    "password": "Strong@Pass1",
    "role": "auditor",
}


def test_admin_can_list_users(admin_client):
    res = admin_client.get(USERS)
    assert res.status_code == 200
    assert {u["role"] for u in res.json()} == {"admin", "auditor"}
    assert all("password_hash" not in u for u in res.json())


def test_auditor_cannot_manage_users(auditor_client):
    assert auditor_client.get(USERS).status_code == 403
    assert auditor_client.post(USERS, json=NEW_USER).status_code == 403


def test_admin_creates_user_with_hashed_password(admin_client, db):
    res = admin_client.post(USERS, json=NEW_USER)
    assert res.status_code == 201
    user = db.scalar(select(User).where(User.email == NEW_USER["email"]))
    assert user.password_hash.startswith("$argon2")
    assert NEW_USER["password"] not in user.password_hash
    assert db.scalar(select(AuditLog).where(AuditLog.action == "user.created"))


def test_duplicate_email_rejected(admin_client):
    assert admin_client.post(USERS, json=NEW_USER).status_code == 201
    assert admin_client.post(USERS, json=NEW_USER).status_code == 409


def test_weak_password_and_bad_role_rejected(admin_client):
    assert admin_client.post(USERS, json=NEW_USER | {"password": "short"}).status_code == 422
    assert admin_client.post(USERS, json=NEW_USER | {"role": "superuser"}).status_code == 422


def test_admin_can_deactivate_another_user(admin_client, db):
    auditor = db.scalar(select(User).where(User.role == "auditor"))
    res = admin_client.patch(f"{USERS}/{auditor.id}", json={"is_active": False})
    assert res.status_code == 200 and res.json()["is_active"] is False


def test_admin_deletes_user_and_it_is_audited(admin_client, db):
    created = admin_client.post(USERS, json=NEW_USER).json()
    assert admin_client.delete(f"{USERS}/{created['id']}").status_code == 204
    assert db.get(User, created["id"]) is None
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "user.deleted"))
    assert entry.details["email"] == NEW_USER["email"]
    assert admin_client.delete(f"{USERS}/{created['id']}").status_code == 404


def test_delete_rules(admin_client, auditor_client, db):
    me = admin_client.get("/api/v1/auth/me").json()
    assert admin_client.delete(f"{USERS}/{me['id']}").status_code == 400
    assert auditor_client.delete(f"{USERS}/{me['id']}").status_code == 403


def test_admin_cannot_disable_or_demote_self(admin_client):
    me = admin_client.get("/api/v1/auth/me").json()
    assert admin_client.patch(f"{USERS}/{me['id']}", json={"is_active": False}).status_code == 400
    assert admin_client.patch(f"{USERS}/{me['id']}", json={"role": "auditor"}).status_code == 400
