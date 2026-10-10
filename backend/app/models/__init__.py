"""Import every model so Base.metadata is complete (Alembic, create_all in tests)."""

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.audit import AuditLog
from app.models.risk import ChecklistEntry, ChecklistItem, CveRef, Finding, RiskScore
from app.models.scan import Scan, ScanHost, ScanPort
from app.models.setting import AppSetting
from app.models.user import User

__all__ = [
    "Alert",
    "AppSetting",
    "Asset",
    "AuditLog",
    "ChecklistEntry",
    "ChecklistItem",
    "CveRef",
    "Finding",
    "RiskScore",
    "Scan",
    "ScanHost",
    "ScanPort",
    "User",
]
