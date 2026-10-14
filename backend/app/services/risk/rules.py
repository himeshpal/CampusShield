"""The risk model as data. Everything a score is made of is defined here, so the model
can be shown, reviewed and changed in one place (bump MODEL_VERSION when you do: stored
scores are recomputed on the next start).

score = min(100, (exposure + vulnerabilities + drift + controls + inventory) * multiplier)
"""

# v2: the controls cap grows with the number of controls (v1 capped at 20, so with six
#     controls the first one confirmed changed nothing)
MODEL_VERSION = 2

# component caps (points)
EXPOSURE_CAP = 40
VULNERABILITY_CAP = 40
DRIFT_CAP = 10
INVENTORY_POINTS = 20  # device nobody registered

DRIFT_POINTS_PER_PORT = 5
# each checklist control that is not confirmed; the component's cap is
# CONTROL_POINTS x number of controls, so every confirmed control lowers the score
CONTROL_POINTS = 4

BANDS = [(75, "critical"), (50, "high"), (25, "medium"), (0, "low")]


def band_for(score: float) -> str:
    return next(name for floor, name in BANDS if score >= floor)


def multiplier_for(criticality_total: int) -> float:
    """4 criteria x 1-3 = 4..12, mapped linearly onto 0.8x..1.5x."""
    return round(0.8 + (criticality_total - 4) * 0.7 / 8, 2)


# ---------------------------------------------------------------- exposure
# Points for a reachable service, by nmap service name. Cleartext remote admin and
# directly exposed data stores weigh most; encrypted web traffic adds nothing.
SERVICE_WEIGHTS: dict[str, tuple[int, str]] = {
    "telnet": (15, "Telnet: cleartext remote login"),
    "docker": (15, "Docker API exposed"),
    "microsoft-ds": (12, "SMB file sharing exposed"),
    "ms-wbt-server": (12, "Remote Desktop (RDP) exposed"),
    "vnc": (12, "VNC remote desktop exposed"),
    "mongodb": (12, "MongoDB database reachable"),
    "ftp": (10, "FTP: cleartext file transfer"),
    "mysql": (10, "MySQL database reachable from the network"),
    "postgresql": (10, "PostgreSQL database reachable from the network"),
    "ms-sql-s": (10, "SQL Server database reachable from the network"),
    "oracle-tns": (10, "Oracle database reachable from the network"),
    "redis": (10, "Redis data store reachable from the network"),
    "memcache": (10, "Memcached reachable from the network"),
    "elasticsearch": (10, "Elasticsearch reachable from the network"),
    "netbios-ssn": (8, "NetBIOS session service exposed"),
    "mqtt": (8, "MQTT IoT broker exposed"),
    "snmp": (8, "SNMP management exposed"),
    "rtsp": (6, "RTSP camera stream exposed"),
    "http": (4, "Web interface without TLS"),
    "http-proxy": (4, "Web interface without TLS"),
    "ssh": (2, "SSH remote administration exposed"),
    "https": (0, "Web interface over TLS"),
}
# fallback by port when nmap could not name the service
PORT_WEIGHTS: dict[int, str] = {
    23: "telnet", 2375: "docker", 445: "microsoft-ds", 3389: "ms-wbt-server", 5900: "vnc",
    27017: "mongodb", 21: "ftp", 3306: "mysql", 5432: "postgresql", 1433: "ms-sql-s",
    1521: "oracle-tns", 6379: "redis", 11211: "memcache", 9200: "elasticsearch",
    139: "netbios-ssn", 1883: "mqtt", 161: "snmp", 554: "rtsp", 8554: "rtsp", 80: "http",
    8080: "http", 8000: "http", 8081: "http", 8888: "http", 22: "ssh", 443: "https",
    8443: "https",
}  # fmt: skip
OTHER_PORT_POINTS = 2  # any other open port

# ---------------------------------------------------------------- vulnerabilities
CVSS_POINTS = [(9.0, 30), (7.0, 20), (4.0, 10), (0.0, 5)]


def cvss_points(cvss: float) -> int:
    return next(points for floor, points in CVSS_POINTS if cvss >= floor)


def cvss_severity(cvss: float) -> str:
    return "critical" if cvss >= 9 else "high" if cvss >= 7 else "medium" if cvss >= 4 else "low"


# Static reference list. Scores and descriptions verified against NIST NVD (Oct 2026).
# `product` is matched against nmap's product string; `version_spec` is a comma-separated
# list of conditions on the detected version.
CVE_REFERENCE = [
    dict(cve_id="CVE-2021-41773", product="Apache httpd", version_spec="==2.4.49", cvss=9.8,
         summary="Path traversal and file disclosure (RCE with mod_cgi) in Apache 2.4.49."),
    dict(cve_id="CVE-2021-42013", product="Apache httpd", version_spec=">=2.4.49,<=2.4.50",
         cvss=9.8, summary="Incomplete fix for CVE-2021-41773: path traversal / RCE."),
    dict(cve_id="CVE-2021-44790", product="Apache httpd", version_spec="<=2.4.51", cvss=9.8,
         summary="Buffer overflow in the mod_lua multipart parser."),
    dict(cve_id="CVE-2022-22720", product="Apache httpd", version_spec="<=2.4.52", cvss=9.8,
         summary="HTTP request smuggling: connection not closed after body errors."),
    dict(cve_id="CVE-2023-25690", product="Apache httpd", version_spec=">=2.4.0,<=2.4.55",
         cvss=9.8, summary="HTTP request smuggling in some mod_proxy configurations."),
    dict(cve_id="CVE-2024-38476", product="Apache httpd", version_spec="<=2.4.59", cvss=9.8,
         summary="Information disclosure, SSRF or script execution via backend responses."),
    dict(cve_id="CVE-2021-23017", product="nginx", version_spec=">=0.6.18,<=1.20.0", cvss=7.7,
         summary="1-byte memory overwrite in the nginx DNS resolver."),
    dict(cve_id="CVE-2024-6387", product="OpenSSH", version_spec=">=8.5,<9.8", cvss=8.1,
         summary="regreSSHion: signal-handler race condition in sshd."),
    dict(cve_id="CVE-2018-15473", product="OpenSSH", version_spec="<=7.7", cvss=5.3,
         summary="Username enumeration."),
    dict(cve_id="CVE-2011-2523", product="vsftpd", version_spec="==2.3.4", cvss=9.8,
         summary="Backdoored vsftpd 2.3.4 opens a root shell on port 6200."),
    dict(cve_id="CVE-2015-3306", product="ProFTPD", version_spec="==1.3.5", cvss=10.0,
         summary="mod_copy allows unauthenticated arbitrary file read/write."),
    dict(cve_id="CVE-2017-7494", product="Samba smbd", version_spec=">=3.5.0,<4.4.14", cvss=9.8,
         summary="SambaCry: remote code execution via an uploaded shared library."),
    dict(cve_id="CVE-2017-7269", product="Microsoft IIS httpd", version_spec="==6.0", cvss=9.8,
         summary="WebDAV buffer overflow in IIS 6.0 (remote code execution)."),
    dict(cve_id="CVE-2019-15107", product="MiniServ", version_spec="<=1.920", cvss=9.8,
         summary="Webmin password_change.cgi command injection."),
]  # fmt: skip

# Software that no longer receives security fixes.
END_OF_LIFE = [
    dict(product="MySQL", version_spec="<8.0", points=20,
         title="MySQL 5.x is end-of-life", detail="No security updates since Oct 2023 (5.7)."),
    dict(product="Apache httpd", version_spec="<2.4", points=20,
         title="Apache httpd 2.2 is end-of-life", detail="No security updates since 2017."),
]  # fmt: skip

# Findings from the read-only NSE scripts of the deep profile.
SCRIPT_FINDINGS = [
    dict(script="ftp-anon", contains="Anonymous FTP login allowed", points=15,
         title="Anonymous FTP login allowed", detail="Anyone can log in and list files."),
    dict(script="redis-info", contains="Version", points=15,
         title="Redis answers without authentication",
         detail="The server returned its configuration to an unauthenticated client."),
]  # fmt: skip

# Stated in Settings -> Risk model and in every PDF report.
LIMITATIONS = [
    "Versions come from service banners: vendor backports (e.g. Ubuntu patching "
    "OpenSSH without changing its version) are invisible, so a matched CVE can be "
    "a false positive and should be confirmed on the host.",
    "Only TCP services in the scan profile are assessed; UDP (e.g. SNMP) is not scanned.",
    "Controls a scan cannot see come from the manual checklist and are only as good "
    "as the answers recorded there.",
]

# ---------------------------------------------------------------- remediation
# What to do about each finding, used for the report's recommendations.
SERVICE_REMEDIATION: dict[str, str] = {
    "telnet": "Disable Telnet and administer the device over SSH",
    "docker": "Close the Docker API port or protect it with TLS client certificates",
    "microsoft-ds": "Restrict SMB file sharing to the networks that need it",
    "ms-wbt-server": "Put Remote Desktop behind the VPN with Network Level Authentication",
    "vnc": "Remove direct VNC access; tunnel it over SSH or the VPN",
    "mongodb": "Restrict MongoDB to the application servers (firewall or bind address)",
    "ftp": "Replace FTP with SFTP so credentials and files are encrypted",
    "mysql": "Restrict MySQL to the application servers (firewall or bind address)",
    "postgresql": "Restrict PostgreSQL to the application servers (pg_hba / firewall)",
    "ms-sql-s": "Restrict SQL Server to the application servers (firewall)",
    "oracle-tns": "Restrict the Oracle listener to the application servers (firewall)",
    "redis": "Bind Redis to localhost or a private VLAN and require a password",
    "memcache": "Bind Memcached to localhost or a private VLAN",
    "elasticsearch": "Restrict Elasticsearch to internal clients and enable authentication",
    "netbios-ssn": "Disable NetBIOS over TCP/IP where it is not needed",
    "mqtt": "Require authentication and TLS on the MQTT broker",
    "snmp": "Disable SNMP v1/v2c or move to SNMPv3",
    "rtsp": "Move cameras to an isolated CCTV VLAN and require RTSP authentication",
    "http": "Serve the web interface over HTTPS and redirect plain HTTP",
    "http-proxy": "Serve the web interface over HTTPS and redirect plain HTTP",
}
SCRIPT_REMEDIATION: dict[str, str] = {
    "Anonymous FTP login allowed": "Disable anonymous FTP login",
    "Redis answers without authentication": "Enable Redis authentication (requirepass / ACL)",
}
