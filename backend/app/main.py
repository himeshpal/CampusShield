import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api import assets, audit_log, auth, checklist, health, reports, risk, scans, users
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.matching import backfill_unmatched_scans
from app.services.risk.service import rescore_outdated, seed_cve_refs
from app.services.scans import recover_interrupted
from app.services.seed import seed, seed_demo_assets

settings = get_settings()
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema is created by `alembic upgrade head` before the server starts.
    with SessionLocal() as db:
        seed(db)
        if settings.demo_data and (added := seed_demo_assets(db)):
            log.info("Registered %d demo lab assets", added)
        if interrupted := recover_interrupted(db):
            log.warning("Marked %d interrupted scan(s) as failed", interrupted)
        if backfilled := backfill_unmatched_scans(db):
            log.info("Matched %d earlier scan(s) against the inventory", backfilled)
        seed_cve_refs(db)
        if rescored := rescore_outdated(db):
            log.info("Computed risk scores for %d asset(s)", rescored)
    yield


app = FastAPI(title=f"{settings.app_name} API", version="0.6.0", lifespan=lifespan)

# Same baseline headers the Next.js app sets on its pages. Needed here too: Next does not
# add them to responses it proxies, and the API is also reachable directly on :8000.
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response


for router in (
    health.router,
    auth.router,
    users.router,
    audit_log.router,
    scans.router,
    assets.router,
    risk.router,
    checklist.router,
    reports.router,
):
    app.include_router(router, prefix="/api/v1")
