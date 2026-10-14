"""Access-control sweep over every API route, so a new endpoint cannot ship unprotected.

Every route needs a session (or, for the n8n / Wazuh machine endpoints, the service key);
every write needs the admin role, except the few listed below that auditors may use.
"""

import re

import pytest

from app.main import app

PUBLIC = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/auth/session"),  # answers null instead of 401 by design
}
SERVICE_KEY_PREFIX = "/api/v1/automation/"
AUDITOR_WRITES = {
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/reports"),  # producing reports is the auditor's job
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def routes() -> list[tuple[str, str]]:
    """Every operation the API exposes, read from its OpenAPI schema."""
    return sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if path.startswith("/api/v1/")
    )


def concrete(path: str) -> str:
    """Fill path parameters with plausible values (/scans/{scan_id} -> /scans/1)."""
    return re.sub(r"\{[^}]+\}", lambda m: "firewall" if "key" in m.group() else "1", path)


ROUTES = routes()


def test_the_sweep_sees_every_module():
    prefixes = {path.split("/")[3] for _, path in ROUTES}
    assert prefixes >= {"auth", "users", "audit-log", "scans", "assets", "risk", "checklist",
                        "reports", "alerts", "automation", "health"}  # fmt: skip
    assert len(ROUTES) >= 40


@pytest.mark.parametrize(("method", "path"), [r for r in ROUTES if r not in PUBLIC])
def test_no_route_answers_without_credentials(client, method, path):
    res = client.request(method, concrete(path), json={})
    assert res.status_code == 401, f"{method} {path} -> {res.status_code}"


@pytest.mark.parametrize(
    ("method", "path"),
    [r for r in ROUTES if r[0] in WRITE_METHODS and r not in PUBLIC and r not in AUDITOR_WRITES
     and not r[1].startswith(SERVICE_KEY_PREFIX)],
)  # fmt: skip
def test_auditors_cannot_write(auditor_client, method, path):
    res = auditor_client.request(method, concrete(path), json={})
    assert res.status_code == 403, f"{method} {path} -> {res.status_code}"


@pytest.mark.parametrize(
    ("method", "path"), [r for r in ROUTES if r[1].startswith(SERVICE_KEY_PREFIX)]
)
def test_machine_endpoints_ignore_user_sessions(admin_client, method, path):
    """n8n and Wazuh authenticate with the service key; an admin session is not enough."""
    res = admin_client.request(method, concrete(path), json={})
    assert res.status_code == 401, f"{method} {path} -> {res.status_code}"
