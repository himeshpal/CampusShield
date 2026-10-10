"""Suggest an asset type for a discovered device from its MAC vendor and open ports.

Deliberately simple, ordered rules (first match wins) so the suggestion is explainable;
an administrator confirms or corrects it when registering the device.
"""

_VENDOR_RULES: list[tuple[tuple[str, ...], str]] = [
    (("hikvision", "dahua", "axis communications", "hanwha", "cp plus", "uniview"), "iot_cctv"),
    (("zkteco", "essl", "suprema", "realtime biometrics", "matrix comsec"), "iot_biometric"),
    (("ubiquiti", "aruba", "ruckus", "meraki", "tp-link", "tenda", "d-link"), "wifi_ap"),
    (("cisco", "juniper", "mikrotik", "fortinet", "sophos", "netgear"), "network_device"),
    (("canon", "epson", "brother", "kyocera", "ricoh", "xerox", "konica"), "printer"),
]

CCTV_PORTS = {554, 8554, 37777}
PRINTER_PORTS = {515, 631, 9100}
SERVER_PORTS = {25, 53, 443, 1433, 1521, 3306, 5432, 6379, 8080, 8443, 9200, 27017}
WORKSTATION_PORTS = {135, 139, 445, 3389, 5900}


def suggest_asset_type(vendor: str | None, ports: set[int]) -> str:
    name = (vendor or "").lower()
    for keywords, asset_type in _VENDOR_RULES:
        if any(k in name for k in keywords):
            return asset_type
    if ports & CCTV_PORTS:
        return "iot_cctv"
    if ports & PRINTER_PORTS:
        return "printer"
    if ports & WORKSTATION_PORTS:
        return "workstation"
    if ports & SERVER_PORTS:
        return "server"
    return "other"
