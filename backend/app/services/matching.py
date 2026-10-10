"""Tie each scanned host to a persistent asset record.

Order of evidence (strongest first):
  1. MAC address  - survives DHCP changing the IP; the asset's IP is updated.
  2. IP address   - only when there is no MAC on one side to contradict it.
  3. Same IP, *different* MAC -> "ip_conflict": a different device now answers on a
     registered address (replaced, cloned or spoofed). Treated as a new device.
  4. Nothing      -> a new asset with status "unregistered" (doc: unmatched hosts are
     flagged, never silently dropped). Seen again later, it matches by MAC like any asset.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, Scan, ScanHost
from app.models.base import utcnow
from app.services import audit
from app.services.classify import suggest_asset_type


@dataclass
class MatchSummary:
    matched: int = 0
    new_devices: list[int] = field(default_factory=list)  # asset ids
    ip_conflicts: list[int] = field(default_factory=list)  # asset ids of the new devices
    ip_changes: int = 0


def next_asset_tag(db: Session) -> str:
    highest = db.scalar(select(func.max(Asset.id))) or 0
    tag = f"CS-{highest + 1:04d}"
    while db.scalar(select(Asset.id).where(Asset.asset_tag == tag)):  # after manual tags
        highest += 1
        tag = f"CS-{highest + 1:04d}"
    return tag


def _find_by_mac(db: Session, mac: str) -> Asset | None:
    return db.scalar(
        select(Asset)
        .where(Asset.mac_address == mac)
        .order_by((Asset.status == "retired").asc(), Asset.id)  # prefer active records
    )


def _find_by_ip(db: Session, ip: str) -> Asset | None:
    return db.scalar(
        select(Asset).where(Asset.ip_address == ip, Asset.status != "retired").order_by(Asset.id)
    )


def match_host(db: Session, host: ScanHost, seen_at: datetime, summary: MatchSummary) -> Asset:
    asset: Asset | None = None
    method = "new"

    if host.mac_address:
        asset = _find_by_mac(db, host.mac_address)
        if asset:
            method = "mac"
            if asset.ip_address != host.ip_address:  # DHCP moved it
                summary.ip_changes += 1
                asset.ip_address = host.ip_address

    if asset is None:
        by_ip = _find_by_ip(db, host.ip_address)
        if by_ip and (by_ip.mac_address is None or host.mac_address is None):
            asset, method = by_ip, "ip"
            if host.mac_address and not by_ip.mac_address:
                by_ip.mac_address = host.mac_address  # learn the MAC
        elif by_ip:
            method = "ip_conflict"  # registered IP, but a different device answered

    if asset is None:
        ports = {p.port for p in host.ports}
        asset = Asset(
            asset_tag=next_asset_tag(db),
            hostname=host.hostname,
            ip_address=host.ip_address,
            mac_address=host.mac_address,
            mac_vendor=host.mac_vendor,
            os_name=host.os_guess,
            asset_type=suggest_asset_type(host.mac_vendor, ports),
            status="unregistered",
            baseline_ports=sorted(ports),
            first_seen_at=seen_at,
        )
        db.add(asset)
        db.flush()
        summary.new_devices.append(asset.id)
        if method == "ip_conflict":
            summary.ip_conflicts.append(asset.id)
        audit.record(
            db,
            "asset.discovered",
            actor="system",
            entity_type="asset",
            entity_id=asset.id,
            details={
                "ip": host.ip_address,
                "mac": host.mac_address,
                "vendor": host.mac_vendor,
                "ip_conflict": method == "ip_conflict",
            },
        )
    else:
        summary.matched += 1

    # keep the inventory record current with what the network just showed
    asset.last_seen_at = seen_at
    asset.first_seen_at = asset.first_seen_at or seen_at
    asset.mac_vendor = asset.mac_vendor or host.mac_vendor
    asset.os_name = asset.os_name or host.os_guess

    host.asset_id = asset.id
    host.is_registered = asset.status == "registered"
    host.match_method = method
    db.flush()  # the next host's lookups must see this asset's new IP/MAC
    return asset


def match_scan(db: Session, scan: Scan) -> MatchSummary:
    """Match every host of a completed scan. The caller commits."""
    summary = MatchSummary()
    seen_at = scan.finished_at or scan.started_at or utcnow()
    for host in scan.hosts:
        match_host(db, host, seen_at, summary)
    scan.summary = {
        **scan.summary,
        "matched": summary.matched,
        "new_devices": len(summary.new_devices),
        "ip_conflicts": len(summary.ip_conflicts),
    }
    return summary


def backfill_unmatched_scans(db: Session) -> int:
    """Match completed scans recorded before matching existed (oldest first)."""
    scans = db.scalars(
        select(Scan)
        .where(Scan.status == "completed")
        .where(Scan.hosts.any(ScanHost.match_method.is_(None)))
        .order_by(Scan.id)
    ).all()
    for scan in scans:
        match_scan(db, scan)
    db.commit()
    return len(scans)
