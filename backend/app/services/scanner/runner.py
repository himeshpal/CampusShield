"""Runs nmap as a subprocess, streaming progress and supporting cancellation.

nmap only prints its "Timing: About NN% done" lines when attached to a terminal, so the
process gets a pseudo-terminal (pty) instead of plain pipes.
"""

import os
import pty
import subprocess
import tempfile
from collections import deque
from collections.abc import Callable, Iterator
from pathlib import Path

from app.services.scanner.profiles import ScanProfile, build_command
from app.services.scanner.progress import ProgressTracker


class ScanFailed(RuntimeError):
    pass


class ScanCancelled(RuntimeError):
    pass


def _read_lines(fd: int) -> Iterator[str]:
    """Yield complete lines from a pty master until the child closes it."""
    buffer = b""
    while True:
        try:
            chunk = os.read(fd, 4096)
        except OSError:  # EIO: child exited and the pty closed
            chunk = b""
        if not chunk:
            break
        buffer += chunk
        *lines, buffer = buffer.replace(b"\r\n", b"\n").split(b"\n")
        for line in lines:
            yield line.decode(errors="replace")
    if buffer:
        yield buffer.decode(errors="replace")


def run_nmap(
    target: str,
    profile: ScanProfile,
    exclude: list[str],
    on_progress: Callable[[int, str], None],
    should_cancel: Callable[[], bool],
) -> str:
    """Run one scan and return nmap's XML report."""
    with tempfile.TemporaryDirectory(prefix="cs-scan-") as tmp:
        xml_path = Path(tmp) / "scan.xml"
        cmd = build_command(target, profile, exclude, str(xml_path))
        tracker = ProgressTracker()
        tail: deque[str] = deque(maxlen=8)  # last lines, for error messages

        master, slave = pty.openpty()
        # nmap's periodic stats need the pty as its *controlling* terminal: `setsid --ctty`
        # starts a new session and claims it (thread-safe, unlike Popen's preexec_fn).
        proc = subprocess.Popen(["setsid", "--ctty", *cmd], stdout=slave, stderr=slave, stdin=slave)
        os.close(slave)  # the child holds its own copy
        try:
            for line in _read_lines(master):  # --stats-every keeps lines coming
                if line.strip():
                    tail.append(line.strip())
                if should_cancel():
                    proc.terminate()
                    proc.wait(timeout=10)
                    raise ScanCancelled("Scan cancelled by user")
                if tracker.feed(line):
                    on_progress(tracker.percent, tracker.phase)
        finally:
            os.close(master)

        if proc.wait() != 0:
            raise ScanFailed(f"nmap exited with code {proc.returncode}: {' | '.join(tail)}")
        if not xml_path.exists():
            raise ScanFailed("nmap produced no report")
        return xml_path.read_text(encoding="utf-8")
