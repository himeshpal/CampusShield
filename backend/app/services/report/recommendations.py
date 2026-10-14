"""Turn score breakdowns into a prioritised, de-duplicated list of actions.

Rule-based like the scoring itself: each finding kind maps to a fixed remediation, the
same action on several assets is merged into one line (all CVEs of one software version
become one upgrade), and the order is priority first, then the risk points the action
addresses: per asset the points of its findings, capped like the score component they
belong to, times the asset's criticality multiplier.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from app.services.risk import rules

PRIORITIES = ("critical", "high", "medium", "low")
MIN_EXPOSURE_POINTS = 4  # SSH (2) or HTTPS (0) alone are not worth an action
_SERVICE_BY_LABEL = {label: service for service, (_, label) in rules.SERVICE_WEIGHTS.items()}
_TRAILING_PORT = re.compile(r" \(\d+/\w+\)$")
_CVE_LABEL = re.compile(r"^(?P<cve>\S+) in (?P<software>.+) \(CVSS (?P<cvss>[\d.]+)\)$")


class ScoredAsset(Protocol):
    tag: str
    label: str
    ip: str | None
    status: str
    band: str
    multiplier: float
    components: list[dict]


@dataclass
class Recommendation:
    priority: str
    action: str
    reason: str
    kind: str
    assets: list[str] = field(default_factory=list)
    points: float = 0

    @property
    def rank(self) -> tuple[int, float]:
        return PRIORITIES.index(self.priority), -self.points


@dataclass
class _Match:
    key: tuple
    priority: str
    action: str
    reason: str
    where: str = ""  # e.g. "port 80", shown next to the asset


def _cut(text: str | None, marker: str) -> str:
    return (text or "").split(marker)[0].strip()


def _classify(item: dict, asset: ScoredAsset) -> _Match | None:
    kind, label, severity = item["kind"], item["label"], item.get("severity", "low")
    port = f"port {item['port']}" if item.get("port") else ""
    if kind == "cve":
        parsed = _CVE_LABEL.match(label)
        software = parsed["software"] if parsed else label
        return _Match(
            ("cve", software),
            severity,
            f"Upgrade {software} to a supported, patched release",
            "",  # filled in from all CVEs of this software, see _cve_reason
            port,
        )
    if kind == "end_of_life":
        return _Match(
            ("eol", label),
            "high",
            f"Replace end-of-life software: {label}",
            _cut(item.get("detail"), " (identified in scan"),
            port,
        )
    if kind == "misconfiguration":
        title = _TRAILING_PORT.sub("", label)
        return _Match(
            ("misconfiguration", title),
            "high",
            rules.SCRIPT_REMEDIATION.get(title, f"Fix: {title}"),
            _cut(item.get("detail"), " (NSE"),
            port,
        )
    if kind == "risky_port":
        if item["points"] < MIN_EXPOSURE_POINTS:
            return None
        title = _TRAILING_PORT.sub("", label)
        service = _SERVICE_BY_LABEL.get(title)
        action = rules.SERVICE_REMEDIATION.get(service or "", f"Close or firewall: {title}")
        return _Match(("service", action), severity, action, title, port)
    if kind == "baseline_drift":
        return _Match(
            ("drift",),
            "medium",
            "Review open ports outside the approved baseline: close them or approve them",
            "Services nobody approved are often forgotten test setups or misconfigurations.",
            port,
        )
    if kind == "unregistered":
        return _Match(
            ("unregistered", asset.tag),
            "critical" if asset.band == "critical" else "high",
            f"Identify the unregistered device at {asset.ip or 'an unknown address'}: "
            "register it with an owner or remove it from the network",
            "Nobody is accountable for an unknown device and it has no approved services.",
        )
    if kind == "control_gap":
        if asset.status != "registered":
            return None  # registering the device comes first (see "unregistered")
        control, _, state = label.rpartition(": ")
        if state == "not in place":
            return _Match(
                ("control", control),
                "medium",
                f"Implement: {control}",
                "Recorded as missing in the security checklist.",
            )
        return _Match(
            ("confirm",),
            "low",
            "Confirm the unverified controls in the security checklist",
            "Unanswered controls count as missing until someone verifies them.",
            control,
        )
    return None


def _cve_reason(labels: list[str]) -> str:
    found = sorted(
        {(m["cve"], float(m["cvss"])) for m in map(_CVE_LABEL.match, labels) if m},
        key=lambda c: (-c[1], c[0]),
    )
    if not found:
        return ""
    ids = ", ".join(cve for cve, _ in found)
    n = len(found)
    return (
        f"Fixes {n} known vulnerabilit{'ies' if n != 1 else 'y'} ({ids}); "
        f"highest CVSS {found[0][1]:g}."
    )


def _where(label: str, details: list[str], *, count_only: bool) -> str:
    if not details:
        return label
    if count_only:
        n = len(details)
        return f"{label} ({n} control{'s' if n != 1 else ''})"
    return f"{label} ({', '.join(details)})"


def recommend(assets: Sequence[ScoredAsset]) -> list[Recommendation]:
    groups: dict[tuple, Recommendation] = {}
    labels: dict[tuple, list[str]] = {}  # the items behind each group (for CVE reasons)
    where: dict[tuple, dict[str, list[str]]] = {}
    for asset in assets:
        # points per (group, component) on this asset, so caps apply like in the score
        local: dict[tuple, dict[str, int]] = {}
        caps = {c["key"]: c["cap"] for c in asset.components}
        for component in asset.components:
            for item in component["items"]:
                match = _classify(item, asset)
                if match is None:
                    continue
                rec = groups.get(match.key)
                if rec is None:
                    rec = Recommendation(match.priority, match.action, match.reason, match.key[0])
                    groups[match.key] = rec
                if PRIORITIES.index(match.priority) < PRIORITIES.index(rec.priority):
                    rec.priority = match.priority  # the worst instance sets the priority
                labels.setdefault(match.key, []).append(item["label"])
                per_component = local.setdefault(match.key, {})
                key = component["key"]
                per_component[key] = per_component.get(key, 0) + item["points"]
                details = where.setdefault(match.key, {}).setdefault(asset.label, [])
                if match.where and match.where not in details:
                    details.append(match.where)
        for key, per_component in local.items():
            capped = sum(min(points, caps[c]) for c, points in per_component.items())
            groups[key].points += capped * asset.multiplier

    for key, rec in groups.items():
        rec.points = round(rec.points, 1)
        if rec.kind == "cve":
            rec.reason = _cve_reason(labels[key])
        rec.assets = [
            _where(label, details, count_only=key == ("confirm",))
            for label, details in where[key].items()
        ]
    return sorted(groups.values(), key=lambda r: r.rank)
