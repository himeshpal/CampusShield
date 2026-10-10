"""Live checks against the running Docker lab (run inside the backend container)."""

import pytest

from app.services.scanner.parser import parse_nmap_xml
from app.services.scanner.profiles import PROFILES
from app.services.scanner.runner import ScanCancelled, run_nmap

LAB_TARGETS = [
    "172.25.0.10",
    "172.25.0.11",
    "172.25.0.12",
    "172.25.0.20",
    "172.25.0.30",
    "172.25.0.40",
    "172.25.0.66",
]
EXCLUDE = ["172.25.0.5", "172.25.0.1"]


@pytest.mark.lab
def test_quick_profile_finds_all_seven_lab_hosts_with_progress():
    updates = []
    xml = run_nmap(
        "172.25.0.0/24",
        PROFILES["quick"],
        EXCLUDE,
        lambda percent, phase: updates.append((percent, phase)),
        lambda: False,
    )
    result = parse_nmap_xml(xml)
    assert [h.ip for h in result.hosts] == LAB_TARGETS
    assert any(p.port == 6379 for h in result.hosts for p in h.ports)  # rogue Redis
    assert updates and updates[-1][0] > 0


@pytest.mark.lab
def test_cancel_terminates_nmap():
    with pytest.raises(ScanCancelled):
        run_nmap("172.25.0.0/24", PROFILES["deep"], EXCLUDE, lambda *_: None, lambda: True)
