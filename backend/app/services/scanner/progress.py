"""Turns nmap's verbose/stats output into one 0-100 progress value and a phase label.

nmap (run with -v and --stats-every, on a pty) prints two kinds of useful lines:
  "Initiating Service scan at 12:14"                     -> a phase starts
  "Service scan Timing: About 40.00% done; ETC: ..."     -> progress inside a phase
Each phase is mapped onto a slice of the overall bar.
"""

import re

# "Initiating Service scan at 12:14", "Initiating OS detection (try #1) against 7 hosts"
_INITIATING = re.compile(r"^Initiating (?P<phase>.+)")
_TIMING = re.compile(r"^(?P<phase>.+?) Timing: About (?P<pct>\d+(?:\.\d+)?)% done")

# (substring of nmap's phase name, overall start, overall end, label for the UI)
_PHASES = [
    ("Ping Scan", 0, 10, "Discovering live hosts"),
    ("Stealth Scan", 10, 40, "Scanning ports"),
    ("Connect Scan", 10, 40, "Scanning ports"),
    ("Service scan", 40, 80, "Detecting services and versions"),
    ("OS detection", 80, 88, "Fingerprinting operating systems"),
    ("NSE", 88, 98, "Running safe NSE scripts"),
]


def _phase(name: str) -> tuple[int, int, str] | None:
    for needle, start, end, label in _PHASES:
        if needle.lower() in name.lower():
            return start, end, label
    return None


class ProgressTracker:
    def __init__(self) -> None:
        self.percent = 0
        self.phase = "Starting nmap"

    def _update(self, value: int, label: str) -> bool:
        value = max(self.percent, value)  # never move backwards
        if value == self.percent and label == self.phase:
            return False
        self.percent, self.phase = value, label
        return True

    def feed(self, line: str) -> bool:
        """Consume one line of nmap output. Returns True if progress changed."""
        line = line.strip()
        if match := _TIMING.match(line):
            name, pct = match["phase"], float(match["pct"])
        elif match := _INITIATING.match(line):
            name, pct = match["phase"], 0.0
        else:
            return False

        phase = _phase(name)
        if phase is None:
            return False
        start, end, label = phase
        # nmap also runs an NSE "pre-scan" before discovery; only count NSE once
        # service detection has started, or the bar would jump to 88% immediately.
        if start >= 88 and self.percent < 40:
            return False
        return self._update(int(start + (end - start) * pct / 100), label)
