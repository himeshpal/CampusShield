def test_health_reports_database_and_nmap(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["database"] == "ok"
    assert body["nmap"] == "ok"
    assert body["status"] == "ok"
