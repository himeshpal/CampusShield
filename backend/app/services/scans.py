"""Scan orchestration: validate -> queue -> run nmap in the background -> persist.

One scan runs at a time (a campus IT team rarely needs more, and it keeps load on the
network predictable). Scans run on a worker thread with their own DB session.
"""

import logging
import threading
from collections.abc import Callable

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import Scan, ScanHost, ScanPort, User
from app.models.base import utcnow
from app.models.scan import ACTIVE_STATUSES
from app.services import audit
from app.services.matching import match_scan
from app.services.risk.service import score_scan
from app.services.scanner.parser import ParsedScan, parse_nmap_xml
from app.services.scanner.profiles import PROFILES, display_command
from app.services.scanner.runner import ScanCancelled, run_nmap
from app.services.scanner.scope import validate_target

log = logging.getLogger(__name__)

# Swappable in tests: the session factory used by the worker, how work is dispatched,
# and the function that actually runs nmap.
session_factory: sessionmaker[Session] = SessionLocal
nmap_runner = run_nmap


def _dispatch_thread(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, name="scan-worker", daemon=True).start()


dispatch: Callable[[Callable[[], None]], None] = _dispatch_thread

_cancel_requested: set[int] = set()
_start_lock = threading.Lock()


class ScanConflict(RuntimeError):
    pass


def start_scan(
    db: Session,
    *,
    target: str,
    profile: str,
    user: User | None,
    triggered_by: str = "user",
    ip_address: str | None = None,
) -> Scan:
    """Validate and queue a scan, then run it in the background. Raises ScopeError,
    ScanConflict."""
    settings = get_settings()
    normalized = validate_target(target, settings.authorized_subnet_list)
    exclude = settings.scan_exclude_list

    with _start_lock:  # two clicks at once must not start two scans
        running = db.scalar(select(Scan).where(Scan.status.in_(ACTIVE_STATUSES)))
        if running:
            raise ScanConflict(f"Scan #{running.id} is still running. Wait or cancel it first.")
        scan = Scan(
            target=normalized,
            profile=profile,
            status="queued",
            phase="Queued",
            triggered_by=triggered_by,
            requested_by_id=user.id if user else None,
            summary={"command": display_command(normalized, PROFILES[profile], exclude)},
        )
        db.add(scan)
        db.flush()
        audit.record(
            db,
            "scan.started",
            user=user,
            actor=None if user else triggered_by,
            entity_type="scan",
            entity_id=scan.id,
            details={"target": normalized, "profile": profile},
            ip_address=ip_address,
        )
        db.commit()

    scan_id = scan.id
    dispatch(lambda: execute_scan(scan_id))
    return scan


def request_cancel(db: Session, scan: Scan, user: User) -> None:
    _cancel_requested.add(scan.id)
    audit.record(db, "scan.cancel_requested", user=user, entity_type="scan", entity_id=scan.id)
    db.commit()


def execute_scan(scan_id: int) -> None:
    """Worker entry point. Never raises: failures are recorded on the scan."""
    with session_factory() as db:
        scan = db.get(Scan, scan_id)
        if scan is None:
            return
        scan.status, scan.started_at, scan.phase = "running", utcnow(), "Starting nmap"
        db.commit()

        def on_progress(percent: int, phase: str) -> None:
            db.execute(update(Scan).where(Scan.id == scan_id).values(progress=percent, phase=phase))
            db.commit()

        try:
            xml = nmap_runner(
                scan.target,
                PROFILES[scan.profile],
                get_settings().scan_exclude_list,
                on_progress,
                lambda: scan_id in _cancel_requested,
            )
            result = parse_nmap_xml(xml)
            _store_results(db, scan, result)
            db.flush()
            match_scan(db, scan)  # link hosts to assets, flag unregistered devices
            score_scan(db, scan)  # rescore every asset this scan observed
            _finish(db, scan, "completed", phase="Completed")
        except ScanCancelled:
            _finish(db, scan, "cancelled", phase="Cancelled")
        except Exception as exc:  # recorded on the scan for the UI
            log.exception("scan %s failed", scan_id)
            db.rollback()
            scan = db.get(Scan, scan_id)
            scan.error = str(exc)[:2000]
            _finish(db, scan, "failed", phase="Failed")
        finally:
            _cancel_requested.discard(scan_id)


def _store_results(db: Session, scan: Scan, result: ParsedScan) -> None:
    for host in result.hosts:
        scan.hosts.append(
            ScanHost(
                ip_address=host.ip,
                mac_address=host.mac,
                mac_vendor=host.vendor,
                hostname=host.hostname,
                os_guess=host.os_guess,
                state="up",
                ports=[
                    ScanPort(
                        port=p.port,
                        protocol=p.protocol,
                        state=p.state,
                        service=p.service,
                        product=p.product,
                        version=p.version,
                        extra_info=p.extra_info,
                        script_output=p.scripts,
                    )
                    for p in host.ports
                ],
            )
        )
    scan.hosts_up = len(result.hosts)
    scan.summary = {
        **scan.summary,
        "open_ports": result.open_ports,
        "nmap_elapsed_seconds": result.elapsed_seconds,
    }


def _finish(db: Session, scan: Scan, status: str, *, phase: str) -> None:
    scan.status, scan.phase, scan.finished_at = status, phase, utcnow()
    if status == "completed":
        scan.progress = 100
    details: dict = {"hosts_up": scan.hosts_up}
    if scan.error:
        details["error"] = scan.error
    audit.record(
        db, f"scan.{status}", actor="system", entity_type="scan", entity_id=scan.id, details=details
    )
    db.commit()


def recover_interrupted(db: Session) -> int:
    """At startup: a scan still 'running' was killed by a restart - mark it failed."""
    stuck = list(db.scalars(select(Scan).where(Scan.status.in_(ACTIVE_STATUSES))))
    for scan in stuck:
        scan.status, scan.phase, scan.finished_at = "failed", "Interrupted", utcnow()
        scan.error = "The backend restarted while this scan was running."
    db.commit()
    return len(stuck)
