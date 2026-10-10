from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import audit_log, auth, health, users
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.seed import seed

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema is created by `alembic upgrade head` before the server starts.
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title=f"{settings.app_name} API", version="0.2.0", lifespan=lifespan)

for router in (health.router, auth.router, users.router, audit_log.router):
    app.include_router(router, prefix="/api/v1")
