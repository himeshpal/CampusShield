"""Pure risk-engine tests: the formula, caps, bands and every component, checked against
hand-calculated scores for the lab devices."""

import pytest

from app.services.risk import rules
from app.services.risk.engine import AssetContext, PortEvidence, score_asset
from app.services.risk.versions import parse_version, version_matches


class Cve:  # duck-typed CveRef
    def __init__(self, cve_id, product, version_spec, cvss, summary="test"):
        self.cve_id, self.product, self.version_spec = cve_id, product, version_spec
        self.cvss, self.summary = cvss, summary


CVES = [Cve(**{k: r[k] for k in ("cve_id", "product", "version_spec", "cvss")})
        for r in rules.CVE_REFERENCE]  # fmt: skip
ALL_UNKNOWN = {label: "unknown" for label in "ABCDEF"}  # six controls, none confirmed


def ctx(status="registered", criteria=(2, 2, 2, 2), baseline=(), controls=None):
    return AssetContext(status, criteria, baseline, ALL_UNKNOWN if controls is None else controls)


def component(result, key):
    return next(c for c in result.components if c.key == key)


# ------------------------------------------------------------------ lab devices
# (ports, context, expected score) - worked out by hand from rules.py
LAB = {
    "ERP portal (nginx, HTTP + HTTPS)": (
        [PortEvidence(80, service="http", product="nginx", version="1.30.5"),
         PortEvidence(443, service="ssl/http", product="nginx", version="1.30.5")],
        ctx(criteria=(3, 3, 3, 2), baseline=(80, 443)),
        # (4 + 0 + 0 + 20 + 0) x 1.41
        33.8,
    ),
    "Department website (Apache 2.4.49)": (
        [PortEvidence(80, service="http", product="Apache httpd", version="2.4.49")],
        ctx(criteria=(2, 2, 2, 1), baseline=(80,)),
        # (4 + 40[6 critical CVEs, capped] + 0 + 20 + 0) x 1.06
        67.8,
    ),
    "Student records DB (MySQL 5.7)": (
        [PortEvidence(3306, service="mysql", product="MySQL", version="5.7.44")],
        ctx(criteria=(3, 3, 2, 2), baseline=(3306,)),
        # (10 + 20[end-of-life] + 0 + 20 + 0) x 1.32
        66.0,
    ),
    "Lab PC (anonymous FTP, FTP not in baseline)": (
        [PortEvidence(21, service="ftp", product="BusyBox ftpd",
                      scripts={"ftp-anon": "Anonymous FTP login allowed (FTP code 230)"}),
         PortEvidence(22, service="ssh", product="Dropbear sshd", version="2025.88")],
        ctx(criteria=(1, 1, 1, 1), baseline=(22,)),
        # (12 + 15 + 5 + 20 + 0) x 0.8
        41.6,
    ),
    "CCTV camera (Telnet not in baseline)": (
        [PortEvidence(23, service="telnet"), PortEvidence(80, service="http"),
         PortEvidence(554, service="rtsp")],
        ctx(criteria=(2, 2, 1, 1), baseline=(80, 554)),
        # (25 + 0 + 5 + 20 + 0) x 0.98
        49.0,
    ),
    "Rogue Raspberry Pi (open Redis, unregistered)": (
        [PortEvidence(6379, service="redis", product="Redis key-value store", version="8.0.4",
                      scripts={"redis-info": "Version: 8.0.4"}),
         PortEvidence(8080, service="http", product="SimpleHTTPServer", version="0.6")],
        ctx(status="unregistered"),
        # (14 + 15 + 0[no baseline] + 20 + 20) x 1.15
        79.3,
    ),
}  # fmt: skip


@pytest.mark.parametrize("name", LAB)
def test_lab_device_scores_match_hand_calculation(name):
    ports, context, expected = LAB[name]
    assert score_asset(ports, context, CVES).score == expected


def test_lab_bands():
    bands = {n: score_asset(p, c, CVES).band for n, (p, c, _) in LAB.items()}
    assert bands["Rogue Raspberry Pi (open Redis, unregistered)"] == "critical"
    assert bands["Department website (Apache 2.4.49)"] == "high"
    assert bands["ERP portal (nginx, HTTP + HTTPS)"] == "medium"


# ------------------------------------------------------------------ formula pieces
@pytest.mark.parametrize(("total", "expected"), [(4, 0.8), (8, 1.15), (12, 1.5), (11, 1.41)])
def test_criticality_multiplier(total, expected):
    assert rules.multiplier_for(total) == expected


@pytest.mark.parametrize(
    ("score", "band"),
    [(0, "low"), (24.9, "low"), (25, "medium"), (49.9, "medium"), (50, "high"),
     (74.9, "high"), (75, "critical"), (100, "critical")],
)  # fmt: skip
def test_band_boundaries(score, band):
    assert rules.band_for(score) == band


@pytest.mark.parametrize(("cvss", "points"), [(10.0, 30), (9.0, 30), (8.9, 20), (7.0, 20),
                                              (6.9, 10), (4.0, 10), (3.9, 5)])  # fmt: skip
def test_cvss_points(cvss, points):
    assert rules.cvss_points(cvss) == points


def test_score_never_exceeds_100():
    ports = [PortEvidence(p, service="telnet") for p in range(23, 40)]
    ports.append(PortEvidence(80, product="Apache httpd", version="2.4.49"))
    result = score_asset(ports, ctx(status="unregistered", criteria=(3, 3, 3, 3)), CVES)
    assert result.score == 100.0
    assert component(result, "exposure").points == rules.EXPOSURE_CAP  # capped
    assert component(result, "exposure").uncapped > rules.EXPOSURE_CAP


def test_vulnerability_cap_and_all_cves_listed():
    result = score_asset([PortEvidence(80, product="Apache httpd", version="2.4.49")], ctx(), CVES)
    vulns = component(result, "vulnerabilities")
    assert {i.cve_id for i in vulns.items} >= {"CVE-2021-41773", "CVE-2021-42013"}
    assert len(vulns.items) == 6 and vulns.uncapped == 180 and vulns.points == 40


def test_patched_apache_has_no_cves():
    result = score_asset([PortEvidence(80, product="Apache httpd", version="2.4.62")], ctx(), CVES)
    assert component(result, "vulnerabilities").items == []


def test_controls_yes_and_na_count_as_covered():
    controls = {"Firewall": "yes", "MFA": "no", "Antivirus": "unknown", "Encryption": "na"}
    result = score_asset([], ctx(controls=controls), CVES)
    items = component(result, "controls").items
    assert [i.label for i in items] == ["MFA: not in place", "Antivirus: not confirmed"]
    assert component(result, "controls").points == 8


def test_all_controls_confirmed_removes_control_points():
    result = score_asset([], ctx(controls={c: "yes" for c in "ABCDEF"}), CVES)
    assert component(result, "controls").points == 0
    assert result.score == 0 and result.band == "low"


def test_drift_only_for_registered_assets():
    ports = [PortEvidence(21, service="ftp"), PortEvidence(22, service="ssh")]
    registered = score_asset(ports, ctx(baseline=(22,)), CVES)
    assert component(registered, "drift").points == 5
    unknown = score_asset(ports, ctx(status="unregistered", baseline=(22,)), CVES)
    assert component(unknown, "drift").points == 0


def test_drift_is_capped():
    ports = [PortEvidence(p) for p in (1, 2, 3, 4)]
    assert component(score_asset(ports, ctx(), CVES), "drift").points == rules.DRIFT_CAP


def test_https_scores_zero_and_unknown_ports_score_two():
    result = score_asset([PortEvidence(443, service="ssl/http"), PortEvidence(9999)], ctx(), CVES)
    points = {i.port: i.points for i in component(result, "exposure").items}
    assert points == {443: 0, 9999: rules.OTHER_PORT_POINTS}


def test_service_falls_back_to_port_number():
    result = score_asset([PortEvidence(23)], ctx(), CVES)  # nmap gave no service name
    assert component(result, "exposure").points == 15


def test_breakdown_is_explainable():
    ports, context, expected = LAB["Department website (Apache 2.4.49)"]
    breakdown = score_asset(ports, context, CVES).breakdown()
    assert breakdown["formula"] == "min(100, (4 + 40 + 0 + 20 + 0) x 1.06) = 67.8"
    assert breakdown["model_version"] == rules.MODEL_VERSION
    assert [c["key"] for c in breakdown["components"]] == [
        "exposure", "vulnerabilities", "drift", "controls", "inventory",
    ]  # fmt: skip
    cve = breakdown["components"][1]["items"][0]
    assert cve["cve_id"].startswith("CVE-") and cve["severity"] == "critical"


def test_findings_exclude_control_gaps_and_zero_point_items():
    ports = [PortEvidence(443, service="ssl/http"), PortEvidence(23, service="telnet")]
    findings = score_asset(ports, ctx(baseline=(23, 443)), CVES).findings
    assert [f.kind for f in findings] == ["risky_port"]


# ------------------------------------------------------------------ version matching
@pytest.mark.parametrize(
    ("text", "parsed"),
    [("2.4.49", (2, 4, 49)), ("5.7.44", (5, 7, 44)), ("8.9p1 Ubuntu 3ubuntu0.6", (8, 9, 1)),
     ("2025.88", (2025, 88)), ("", None), (None, None), ("unknown", None)],
)  # fmt: skip
def test_parse_version(text, parsed):
    assert parse_version(text) == parsed


@pytest.mark.parametrize(
    ("version", "spec", "matches"),
    [
        ("2.4.49", "==2.4.49", True),
        ("2.4.50", "==2.4.49", False),
        ("2.4.50", ">=2.4.49,<=2.4.50", True),
        ("2.4.51", ">=2.4.49,<=2.4.50", False),
        ("2.4", "==2.4.0", True),  # padding
        ("8.9p1", ">=8.5,<9.8", True),
        ("9.8p1", ">=8.5,<9.8", False),  # 9.8p1 is the fixed release
        ("8.4p1", ">=8.5,<9.8", False),
        ("5.7.44", "<8.0", True),
        ("8.0.36", "<8.0", False),
        (None, "<8.0", False),
    ],
)
def test_version_matches(version, spec, matches):
    assert version_matches(version, spec) is matches


def test_bad_version_spec_is_rejected():
    with pytest.raises(ValueError):
        version_matches("1.0", "~1.0")


def test_reference_list_is_well_formed():
    for ref in rules.CVE_REFERENCE:
        assert ref["cve_id"].startswith("CVE-")
        assert 0 < ref["cvss"] <= 10
        version_matches("1.0", ref["version_spec"])  # spec parses
