"""Version comparison for CVE / end-of-life matching on nmap version banners.

Banners look like "2.4.49", "5.7.44", "8.9p1 Ubuntu 3ubuntu0.6" or "2025.88". Only the
leading dotted number (plus a trailing pN patch level) is compared. Limitation, shared
by every banner-based scanner: distribution backports are invisible, so a patched
"8.9p1 Ubuntu" can still match an OpenSSH CVE.
"""

import operator
import re

_LEADING = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:p(\d+))?")
_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
}
_CONDITION = re.compile(r"^(==|!=|>=|<=|>|<)\s*(.+)$")


def parse_version(text: str | None) -> tuple[int, ...] | None:
    if not text:
        return None
    match = _LEADING.match(text)
    if not match:
        return None
    parts = tuple(int(p) for p in match.group(1).split("."))
    return parts + (int(match.group(2)),) if match.group(2) else parts


def _compare(op, left: tuple[int, ...], right: tuple[int, ...]) -> bool:
    # pad so that 2.4 == 2.4.0, but 8.9p1 (8,9,1) > 8.9 (8,9,0)
    width = max(len(left), len(right))
    return op(left + (0,) * (width - len(left)), right + (0,) * (width - len(right)))


def version_matches(version: str | None, spec: str) -> bool:
    """True if `version` satisfies every comma-separated condition in `spec`."""
    detected = parse_version(version)
    if detected is None:
        return False
    for condition in spec.split(","):
        match = _CONDITION.match(condition.strip())
        if not match:
            raise ValueError(f"bad version condition: {condition!r}")
        bound = parse_version(match.group(2))
        if bound is None or not _compare(_OPS[match.group(1)], detected, bound):
            return False
    return True


def product_matches(detected: str | None, reference: str) -> bool:
    """nmap product strings vary slightly ("Apache httpd", "Samba smbd 3.X - 4.X")."""
    return bool(detected) and detected.lower().startswith(reference.lower())
