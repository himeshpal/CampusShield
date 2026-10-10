"""Step 0 acceptance: the scanner container can see every lab target."""
import nmap
import pytest

LAB_TARGETS = {
    "172.25.0.10", "172.25.0.11", "172.25.0.12", "172.25.0.20",
    "172.25.0.30", "172.25.0.40", "172.25.0.66",
}


@pytest.mark.lab
def test_ping_sweep_finds_all_seven_lab_hosts():
    scanner = nmap.PortScanner()
    scanner.scan(hosts="172.25.0.0/24", arguments="-sn -T4 --exclude 172.25.0.5,172.25.0.1")
    up = {h for h in scanner.all_hosts() if scanner[h].state() == "up"}
    assert LAB_TARGETS <= up, f"missing: {LAB_TARGETS - up}"
