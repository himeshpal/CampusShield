def test_health_reports_database_and_nmap(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["database"] == "ok"
    assert body["nmap"] == "ok"
    assert body["status"] == "ok"


def test_security_headers_on_every_response(client):
    for path in ("/api/v1/health", "/api/v1/auth/me", "/api/v1/does-not-exist"):
        headers = client.get(path).headers
        assert headers["x-frame-options"] == "DENY", path
        assert headers["x-content-type-options"] == "nosniff", path
        assert "frame-ancestors 'none'" in headers["content-security-policy"], path
