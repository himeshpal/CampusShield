"""Normalise nmap XML (via python-nmap) into plain dataclasses the rest of the app uses."""

from dataclasses import dataclass, field

import nmap


@dataclass
class ParsedPort:
    port: int
    protocol: str
    state: str
    service: str | None = None
    product: str | None = None
    version: str | None = None
    extra_info: str | None = None
    scripts: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedHost:
    ip: str
    mac: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None
    ports: list[ParsedPort] = field(default_factory=list)


@dataclass
class ParsedScan:
    command_line: str
    elapsed_seconds: float
    hosts: list[ParsedHost]

    @property
    def open_ports(self) -> int:
        return sum(len(h.ports) for h in self.hosts)


def _blank_to_none(value: str | None) -> str | None:
    return value.strip() or None if value else None


def parse_nmap_xml(xml: str) -> ParsedScan:
    data = nmap.PortScanner().analyse_nmap_xml_scan(nmap_xml_output=xml)
    stats = data["nmap"]
    hosts: list[ParsedHost] = []

    for ip, info in data["scan"].items():
        if info.get("status", {}).get("state") != "up":
            continue
        mac = info.get("addresses", {}).get("mac")
        hostnames = [h["name"] for h in info.get("hostnames", []) if h.get("name")]
        os_matches = info.get("osmatch") or []

        ports: list[ParsedPort] = []
        for proto in ("tcp", "udp"):
            for number, port in sorted(info.get(proto, {}).items()):
                if port.get("state") != "open":
                    continue  # only open services matter for exposure
                ports.append(
                    ParsedPort(
                        port=int(number),
                        protocol=proto,
                        state=port["state"],
                        service=_blank_to_none(port.get("name")),
                        product=_blank_to_none(port.get("product")),
                        version=_blank_to_none(port.get("version")),
                        extra_info=_blank_to_none(port.get("extrainfo")),
                        scripts={k: v.strip() for k, v in (port.get("script") or {}).items()},
                    )
                )

        hosts.append(
            ParsedHost(
                ip=ip,
                mac=mac.lower() if mac else None,
                vendor=info.get("vendor", {}).get(mac) if mac else None,
                hostname=hostnames[0] if hostnames else None,
                os_guess=os_matches[0]["name"] if os_matches else None,
                ports=ports,
            )
        )

    hosts.sort(key=lambda h: tuple(int(part) for part in h.ip.split(".")))
    return ParsedScan(
        command_line=stats.get("command_line", ""),
        elapsed_seconds=float(stats.get("scanstats", {}).get("elapsed", 0) or 0),
        hosts=hosts,
    )
