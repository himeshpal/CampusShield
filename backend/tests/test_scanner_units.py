"""Scope guard, command building, progress tracking and XML parsing (no network)."""

import pytest

from app.services.scanner.parser import parse_nmap_xml
from app.services.scanner.profiles import PROFILES, build_command
from app.services.scanner.progress import ProgressTracker
from app.services.scanner.scope import ScopeError, validate_target
from tests.conftest import FIXTURES

SCOPE = ["172.25.0.0/24"]


# ---------------------------------------------------------------- scope guard
@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("172.25.0.0/24", "172.25.0.0/24"),
        (" 172.25.0.0/24 ", "172.25.0.0/24"),
        ("172.25.0.64/26", "172.25.0.64/26"),
        ("172.25.0.11", "172.25.0.11"),
        ("172.25.0.11/32", "172.25.0.11"),
        ("172.25.0.5/24", "172.25.0.0/24"),  # host bits are normalised away
    ],
)
def test_targets_inside_scope_are_accepted(target, expected):
    assert validate_target(target, SCOPE) == expected


@pytest.mark.parametrize(
    "target",
    [
        "8.8.8.8",  # someone else's network
        "172.25.1.0/24",  # neighbouring subnet
        "172.25.0.0/16",  # supernet of the authorised range
        "0.0.0.0/0",
        "erp.campus.local",  # hostnames are not resolved
        "172.25.0.1-50",  # nmap range syntax
        "172.25.0.0/24 --script=exploit",  # argument injection
        "-iL /etc/passwd",
        "fe80::1",  # IPv6
        "",
    ],
)
def test_targets_outside_scope_or_malformed_are_rejected(target):
    with pytest.raises(ScopeError):
        validate_target(target, SCOPE)


def test_empty_scope_rejects_everything():
    with pytest.raises(ScopeError, match="outside the authorised scan scope"):
        validate_target("172.25.0.10", [])


# ---------------------------------------------------------------- profiles
def test_command_has_target_last_and_excludes_scanner():
    cmd = build_command("172.25.0.0/24", PROFILES["standard"], ["172.25.0.5"], "/tmp/x.xml")
    assert cmd[0] == "nmap" and cmd[-1] == "172.25.0.0/24"
    assert cmd[cmd.index("--exclude") + 1] == "172.25.0.5"
    assert cmd[cmd.index("-oX") + 1] == "/tmp/x.xml"
    assert "--version-light" in cmd


def test_profiles_cover_campus_ports_outside_nmap_top_1000():
    for key in PROFILES:
        ports = PROFILES[key].args[PROFILES[key].args.index("-p") + 1]
        assert "6379" in ports and "554" in ports  # Redis, RTSP
    assert "--script" not in PROFILES["standard"].args
    assert "-O" in PROFILES["deep"].args


# ---------------------------------------------------------------- progress
def test_progress_from_recorded_deep_scan_is_monotonic_and_ordered():
    tracker = ProgressTracker()
    history = []
    for line in (FIXTURES / "lab_deep_progress.txt").read_text().splitlines():
        if tracker.feed(line):
            history.append((tracker.percent, tracker.phase))

    percents = [p for p, _ in history]
    assert percents == sorted(percents)  # never goes backwards
    phases = list(dict.fromkeys(phase for _, phase in history))
    assert phases == [
        "Discovering live hosts",
        "Scanning ports",
        "Detecting services and versions",
        "Fingerprinting operating systems",
        "Running safe NSE scripts",
    ]
    assert 90 <= percents[-1] <= 98


def test_progress_ignores_nse_prescan_and_noise():
    tracker = ProgressTracker()
    assert not tracker.feed("Initiating NSE at 12:16")  # pre-scan before discovery
    assert not tracker.feed("Nmap scan report for 172.25.0.10")
    assert tracker.feed("Initiating ARP Ping Scan at 12:16")
    assert tracker.feed("Service scan Timing: About 50.00% done; ETC: 12:17 (0:00:10 remaining)")
    assert tracker.percent == 60 and tracker.phase == "Detecting services and versions"


# ---------------------------------------------------------------- parser
def test_parser_reads_recorded_standard_scan():
    result = parse_nmap_xml((FIXTURES / "lab_standard.xml").read_text())
    by_ip = {h.ip: h for h in result.hosts}

    assert list(by_ip) == [
        "172.25.0.10", "172.25.0.11", "172.25.0.12", "172.25.0.20",
        "172.25.0.30", "172.25.0.40", "172.25.0.66",
    ]  # fmt: skip
    assert result.open_ports == 13

    apache = by_ip["172.25.0.11"].ports[0]
    assert (apache.port, apache.service, apache.product, apache.version) == (
        80, "http", "Apache httpd", "2.4.49",
    )  # fmt: skip
    rogue = by_ip["172.25.0.66"]
    assert rogue.mac == "b8:27:eb:66:00:66"
    assert rogue.vendor == "Raspberry Pi Foundation"
    assert {p.port for p in rogue.ports} == {6379, 8080}


def test_parser_keeps_nse_script_output_from_deep_scan():
    result = parse_nmap_xml((FIXTURES / "lab_deep.xml").read_text())
    ports = {(h.ip, p.port): p for h in result.hosts for p in h.ports}
    assert "ftp-anon" in ports[("172.25.0.20", 21)].scripts
    assert "redis-info" in ports[("172.25.0.66", 6379)].scripts
    assert all(h.os_guess for h in result.hosts if h.ports)


def test_parser_skips_non_open_ports():
    result = parse_nmap_xml((FIXTURES / "lab_quick.xml").read_text())
    assert all(p.state == "open" for h in result.hosts for p in h.ports)
