from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import AuditLog, User

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def creds():
    s = get_settings()
    return {"email": s.admin_email, "password": s.admin_password}


def test_login_sets_httponly_session_cookie(client, db):
    res = client.post(LOGIN, json=creds())
    assert res.status_code == 200
    assert res.json()["role"] == "admin"
    cookie = res.headers["set-cookie"]
    assert get_settings().session_cookie in cookie
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie

    user = db.scalar(select(User).where(User.email == creds()["email"]))
    db.refresh(user)
    assert user.last_login_at is not None


def test_login_is_case_insensitive_on_email(client):
    body = creds() | {"email": creds()["email"].upper()}
    assert client.post(LOGIN, json=body).status_code == 200


def test_wrong_password_rejected_and_audited(client, db):
    res = client.post(LOGIN, json=creds() | {"password": "wrong"})
    assert res.status_code == 401
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed"))


def test_unknown_email_gets_same_error_as_wrong_password(client):
    wrong_pw = client.post(LOGIN, json=creds() | {"password": "wrong"})
    no_user = client.post(LOGIN, json={"email": "nobody@campus.local", "password": "x"})
    assert no_user.status_code == wrong_pw.status_code == 401
    assert no_user.json() == wrong_pw.json()  # no user enumeration


def test_lockout_after_repeated_failures(client):
    for _ in range(get_settings().login_max_failures):
        assert client.post(LOGIN, json=creds() | {"password": "wrong"}).status_code == 401
    # even the correct password is refused while locked out
    assert client.post(LOGIN, json=creds()).status_code == 429


def test_inactive_user_cannot_login(client, db):
    user = db.scalar(select(User).where(User.email == creds()["email"]))
    user.is_active = False
    db.commit()
    assert client.post(LOGIN, json=creds()).status_code == 401


def test_me_requires_authentication(client):
    assert client.get(ME).status_code == 401


def test_me_returns_current_user(admin_client):
    res = admin_client.get(ME)
    assert res.status_code == 200
    assert res.json()["email"] == get_settings().admin_email


def test_bearer_token_is_accepted(client, db):
    user = db.scalar(select(User).where(User.role == "auditor"))
    token = create_access_token(user.id, user.role, user.token_version)
    res = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200 and res.json()["role"] == "auditor"


def test_tampered_and_expired_tokens_rejected(client, db):
    user = db.scalar(select(User).where(User.role == "admin"))
    wrong_secret = "x" * 32 + "-not-the-real-secret"
    forged = jwt.encode({"sub": str(user.id), "role": "admin"}, wrong_secret, "HS256")
    expired = jwt.encode(
        {"sub": str(user.id), "role": "admin", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        get_settings().jwt_secret,
        "HS256",
    )
    for token in (forged, expired, "garbage"):
        res = client.get(ME, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401


def test_logout_clears_cookie_and_is_audited(admin_client, db):
    res = admin_client.post("/api/v1/auth/logout")
    assert res.status_code == 204
    assert admin_client.get(ME).status_code == 401
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.logout"))


def test_token_copied_before_logout_is_revoked(client):
    """Regression: logout used to only delete the cookie, so a copied JWT kept working."""
    login = client.post(LOGIN, json=creds())
    token = login.cookies[get_settings().session_cookie]
    bearer = {"Authorization": f"Bearer {token}"}
    assert client.get(ME, headers=bearer).status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get(ME, headers=bearer).status_code == 401  # replay fails


def test_new_login_after_logout_works(client):
    client.post(LOGIN, json=creds())
    client.post("/api/v1/auth/logout")
    assert client.post(LOGIN, json=creds()).status_code == 200
    assert client.get(ME).status_code == 200


def test_session_endpoint_never_401s(client):
    assert client.get("/api/v1/auth/session").status_code == 200
    assert client.get("/api/v1/auth/session").json() is None
    client.post(LOGIN, json=creds())
    assert client.get("/api/v1/auth/session").json()["role"] == "admin"
    garbage = client.get("/api/v1/auth/session", headers={"Authorization": "Bearer junk"})
    assert garbage.status_code == 200
