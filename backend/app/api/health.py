import shutil

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: DbSession) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "down"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "nmap": "ok" if shutil.which("nmap") else "missing",
    }
