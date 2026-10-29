def test_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_ready_checks_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.get_json()
    assert body["checks"]["database"] is True


def test_unknown_route_returns_error_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"]
