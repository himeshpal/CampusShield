"""Idempotent first-start data: user accounts and the manual security checklist."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Asset, ChecklistItem, User
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


# The legitimate devices of the lab network (docker-compose.yml). The Raspberry Pi at
# .66 is deliberately absent: discovering it is the point of the demo.
# Criticality criteria are data sensitivity, service dependency, users affected and
# replaceability, each 1 (low) .. 3 (high).
DEMO_ASSETS = [
    dict(
        asset_tag="CS-0001", name="ERP Portal Server", hostname="erp.campus.local",
        asset_type="server", ip_address="172.25.0.10", mac_address="3c:d9:2b:10:00:10",
        department="Administration", location="Server Room, Admin Block", owner="IT Cell",
        os_name="Linux", criteria=(3, 3, 3, 2), baseline_ports=[80, 443],
    ),
    dict(
        asset_tag="CS-0002", name="Department Website", hostname="cse.campus.local",
        asset_type="server", ip_address="172.25.0.11", mac_address="3c:d9:2b:10:00:11",
        department="Computer Engineering", location="Server Room, Admin Block",
        owner="CSE Web Team", os_name="Linux", criteria=(2, 2, 2, 1), baseline_ports=[80],
    ),
    dict(
        asset_tag="CS-0003", name="Student Records Database", hostname="db.campus.local",
        asset_type="server", ip_address="172.25.0.12", mac_address="3c:d9:2b:10:00:12",
        department="Examination Cell", location="Server Room, Admin Block", owner="IT Cell",
        os_name="Linux", criteria=(3, 3, 2, 2), baseline_ports=[3306],
    ),
    dict(
        asset_tag="CS-0004", name="Lab 3 Workstation 01", hostname="lab3-pc01",
        asset_type="workstation", ip_address="172.25.0.20", mac_address="18:db:f2:20:00:20",
        department="Computer Engineering", location="Computer Lab 3", owner="Lab Assistant",
        os_name="Linux", criteria=(1, 1, 1, 1), baseline_ports=[22],
    ),
    dict(
        asset_tag="CS-0005", name="Wi-Fi AP Block A", hostname="ap-block-a",
        asset_type="wifi_ap", ip_address="172.25.0.30", mac_address="24:a4:3c:30:00:30",
        department="IT Cell", location="Block A, 2nd floor", owner="Network Admin",
        os_name=None, criteria=(1, 2, 3, 1), baseline_ports=[22, 80],
    ),
    dict(
        asset_tag="CS-0006", name="CCTV Main Gate", hostname="cctv-gate-01",
        asset_type="iot_cctv", ip_address="172.25.0.40", mac_address="44:19:b6:40:00:40",
        department="Security Office", location="Main Gate", owner="Security Supervisor",
        os_name=None, criteria=(2, 2, 1, 1), baseline_ports=[80, 554],
    ),
]  # fmt: skip


def seed_demo_assets(db: Session) -> int:
    """Register the lab's legitimate devices once. Returns how many were added."""
    added = 0
    for spec in DEMO_ASSETS:
        spec = dict(spec)
        if db.scalar(select(Asset.id).where(Asset.asset_tag == spec["asset_tag"])):
            continue
        sensitivity, dependency, users, replaceability = spec.pop("criteria")
        asset = Asset(
            **spec,
            status="registered",
            data_sensitivity=sensitivity,
            service_dependency=dependency,
            users_affected=users,
            replaceability=replaceability,
        )
        db.add(asset)
        db.flush()
        audit.record(
            db, "asset.seeded", entity_type="asset", entity_id=asset.id,
            details={"asset_tag": asset.asset_tag},
        )  # fmt: skip
        added += 1
    db.commit()
    return added
