"""Scope guard: CampusShield only scans networks the institution has authorised.

Follows the ethical/legal scanning discussion in the IJNSA (2024) survey. Parsing the
target with `ipaddress` also guarantees nothing but an address reaches the nmap argv,
so a target like "--script=..." can never be injected.
"""

import ipaddress


class ScopeError(ValueError):
    pass


def validate_target(target: str, authorized_subnets: list[str]) -> str:
    """Return the normalised IPv4 target (CIDR or single address) or raise ScopeError."""
    raw = target.strip()
    try:
        network = ipaddress.ip_network(raw, strict=False)
    except ValueError:
        raise ScopeError(
            "Enter an IPv4 address or network in CIDR form, e.g. 172.25.0.0/24"
        ) from None

    if network.version != 4:
        raise ScopeError("Only IPv4 targets are supported")

    allowed = [ipaddress.ip_network(s, strict=False) for s in authorized_subnets]
    if not any(network.subnet_of(a) for a in allowed if a.version == 4):
        scope = ", ".join(authorized_subnets) or "none configured"
        raise ScopeError(f"{network} is outside the authorised scan scope ({scope})")

    # single hosts are passed as a plain address, networks in CIDR form
    return str(network.network_address) if network.prefixlen == 32 else str(network)
