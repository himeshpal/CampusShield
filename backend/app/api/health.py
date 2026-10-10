import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
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
