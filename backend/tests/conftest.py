"""Tests run against a fresh in-memory SQLite database, never the real Postgres."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.db import Base, get_db
from app.main import app
from app.services import scans as scan_service
from app.services.seed import seed

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def db(monkeypatch) -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestSession() as session:
        seed(session)

    def override_get_db() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # scan worker: same test DB, run inline instead of on a thread
    monkeypatch.setattr(scan_service, "session_factory", TestSession)
    monkeypatch.setattr(scan_service, "dispatch", lambda fn: fn())
    with TestSession() as session:
        yield session
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def fake_nmap(monkeypatch):
    """Replace nmap with a recorded lab scan. Returns the list of calls made."""
    calls: list[dict] = []

    def run(target, profile, exclude, on_progress, should_cancel):
        calls.append({"target": target, "profile": profile.key, "exclude": exclude})
        on_progress(40, "Detecting services and versions")
        return (FIXTURES / "lab_standard.xml").read_text()

    monkeypatch.setattr(scan_service, "nmap_runner", run)
    return calls


@pytest.fixture
def client(db) -> TestClient:
    # Not used as a context manager, so the lifespan (seeding the real DB) never runs.
    return TestClient(app)


def _login(email: str, password: str) -> TestClient:
    c = TestClient(app)
    res = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return c


@pytest.fixture
def admin_client(db) -> TestClient:
    s = get_settings()
    return _login(s.admin_email, s.admin_password)


@pytest.fixture
def auditor_client(db) -> TestClient:
    s = get_settings()
    return _login(s.auditor_email, s.auditor_password)
