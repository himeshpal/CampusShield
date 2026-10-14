"""Scan profiles (timing/flag choices after Singh et al., 2024 and the IJNSA 2024 survey).

Timings were measured against the 7-device lab network (172.25.0.0/24):
quick ~2 s, standard ~15 s, deep ~2 min.
"""

from dataclasses import dataclass
from functools import cache

# nmap's "top 1000" misses ports that matter on a campus (Redis 6379, RTSP 8554,
# camera DVR 37777, ...), so the profiles use explicit port lists instead.
QUICK_PORTS = (
    "21,22,23,25,53,80,110,135,139,143,161,443,445,554,993,995,1433,1521,1883,2049,"
    "3306,3389,5432,5900,6379,8000,8080,8443,8554,9000,9200,11211,27017,37777"
)
EXTENDED_PORTS = (
    "1-1024,1433,1521,1883,2049,2375,3306,3389,5000,5432,5601,5900,6379,8000,8008,"
    "8080,8081,8443,8554,8888,9000,9090,9200,11211,27017,37777"
)

# Read-only NSE scripts that enrich a host record without exploiting anything.
SAFE_SCRIPTS = (
    "banner,http-title,http-server-header,ssl-cert,ftp-anon,redis-info,mysql-info,rtsp-methods"
)


@dataclass(frozen=True)
class ScanProfile:
    key: str
    label: str
    description: str
    estimate: str
    args: tuple[str, ...]


PROFILES: dict[str, ScanProfile] = {
    p.key: p
    for p in (
        ScanProfile(
            key="quick",
            label="Quick sweep",
            description="Live hosts and the most important campus ports. For frequent re-checks.",
            estimate="~5 seconds",
            args=("-sS", "-T4", "-p", QUICK_PORTS),
        ),
        ScanProfile(
            key="standard",
            label="Standard audit",
            description=(
                "Ports 1-1024 plus campus services, with software versions for CVE matching."
            ),
            estimate="~20 seconds",
            args=("-sS", "-sV", "--version-light", "-T4", "-p", EXTENDED_PORTS),
        ),
        ScanProfile(
            key="deep",
            label="Deep inspection",
            description=(
                "Standard plus OS fingerprinting and safe NSE scripts "
                "(anonymous FTP, open Redis, TLS certificates)."
            ),
            estimate="~2 minutes",
            args=(
                "-sS",
                "-sV",
                "-O",
                "--osscan-limit",
                "-T4",
                "-p",
                EXTENDED_PORTS,
                "--script",
                SAFE_SCRIPTS,
            ),
        ),
    )
}


@cache
def covered_ports(profile: str) -> frozenset[int]:
    """The TCP ports a scan profile probes (parsed from its nmap -p argument)."""
    args = PROFILES[profile].args
    spec = args[args.index("-p") + 1]
    ports: set[int] = set()
    for part in spec.split(","):
        low, _, high = part.partition("-")
        ports.update(range(int(low), int(high or low) + 1))
    return frozenset(ports)


def build_command(
    target: str, profile: ScanProfile, exclude: list[str], xml_path: str
) -> list[str]:
    """Full nmap argv. `target` must already have passed the scope guard."""
    # -v + --stats-every give phase and percentage lines for the progress bar
    cmd = ["nmap", "-n", "-v", *profile.args, "--stats-every", "1s", "-oX", xml_path]
    if exclude:
        cmd += ["--exclude", ",".join(exclude)]
    return [*cmd, target]


def display_command(target: str, profile: ScanProfile, exclude: list[str]) -> str:
    """Human-readable command shown in the UI (without output/progress plumbing)."""
    parts = ["nmap", "-n", *profile.args]
    if exclude:
        parts += ["--exclude", ",".join(exclude)]
    return " ".join([*parts, target])
