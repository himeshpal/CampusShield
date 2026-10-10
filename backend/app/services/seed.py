"""Idempotent first-start data: user accounts and the manual security checklist."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import ChecklistItem, User
from app.services import audit

# Controls an unauthenticated network scan cannot verify (doc section 1.2, "coverage gap").
CHECKLIST_ITEMS = [
    (
        "firewall",
        "Host firewall enabled",
        "A host or network firewall restricts inbound connections to required services only.",
    ),
    (
        "antivirus",
        "Antivirus / EDR active",
        "Up-to-date antivirus or endpoint protection is installed and running.",
    ),
    (
        "disk_encryption",
        "Disk encryption",
        "Storage is encrypted at rest (BitLocker, LUKS, or vendor equivalent).",
    ),
    (
        "mfa",
        "Multi-factor authentication",
        "Administrative and user logins require a second factor.",
    ),
    (
        "patch_policy",
        "Patch policy followed",
        "OS and firmware updates are applied within the institution's patch window.",
    ),
    (
        "default_credentials",
        "Default credentials changed",
        "Factory usernames and passwords (admin/admin, etc.) have been replaced.",
    ),
]


def seed(db: Session) -> None:
    settings = get_settings()
    accounts = [
        (settings.admin_email, settings.admin_password, settings.admin_name, "admin"),
        (settings.auditor_email, settings.auditor_password, settings.auditor_name, "auditor"),
    ]
    for email, password, name, role in accounts:
        if not db.scalar(select(User).where(User.email == email)):
            user = User(
                email=email, full_name=name, role=role, password_hash=hash_password(password)
            )
            db.add(user)
            db.flush()
            audit.record(
                db, "user.seeded", entity_type="user", entity_id=user.id, details={"role": role}
            )

    existing = set(db.scalars(select(ChecklistItem.key)))
    for order, (key, label, description) in enumerate(CHECKLIST_ITEMS):
        if key not in existing:
            db.add(ChecklistItem(key=key, label=label, description=description, sort_order=order))

    db.commit()
