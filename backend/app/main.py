import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import audit_log, auth, health, scans, users
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.scans import recover_interrupted
from app.services.seed import seed

settings = get_settings()
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema is created by `alembic upgrade head` before the server starts.
    with SessionLocal() as db:
        seed(db)
        if interrupted := recover_interrupted(db):
            log.warning("Marked %d interrupted scan(s) as failed", interrupted)
    yield


app = FastAPI(title=f"{settings.app_name} API", version="0.3.0", lifespan=lifespan)

for router in (health.router, auth.router, users.router, audit_log.router, scans.router):
    app.include_router(router, prefix="/api/v1")
