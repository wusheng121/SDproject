def _login(client, identifier, password):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def test_agent_api_key_is_read_only(client, app):
    from models import OperationLog

    with app.app_context():
        assert OperationLog.query.count() == 0
    headers = _login(client, "agent", "Agent12345")
    created = client.post(
        "/api/v1/users/me/api-keys",
        headers=headers,
        json={"name": "mcp-agent", "scopes": ["product:view", "recommendation:query"]},
    )
    assert created.status_code == 201
    api_key = created.get_json()["data"]["api_key"]

    products = client.get("/api/v1/agent/products", headers={"X-API-Key": api_key})
    assert products.status_code == 200
    assert products.get_json()["pagination"]["total"] >= 1

    recommendations = client.get(
        "/api/v1/agent/recommendations", headers={"X-API-Key": api_key}
    )
    assert recommendations.status_code == 200

    write_attempt = client.post("/api/v1/agent/products", headers={"X-API-Key": api_key})
    assert write_attempt.status_code == 405

    with app.app_context():
        actions = {row.action for row in OperationLog.query.all()}
        assert "agent.products.query" in actions
        assert "agent.recommendations.query" in actions


def test_normal_user_cannot_create_api_key(client):
    headers = _login(client, "testuser", "Test12345")
    response = client.post(
        "/api/v1/users/me/api-keys",
        headers=headers,
        json={"name": "not-allowed", "scopes": ["product:view"]},
    )
    assert response.status_code == 403


def test_invalid_api_key_rejected(client):
    response = client.get(
        "/api/v1/agent/products", headers={"X-API-Key": "cmk_invalid.invalid"}
    )
    assert response.status_code == 401


def test_api_key_scope_is_enforced(client):
    headers = _login(client, "agent", "Agent12345")
    created = client.post(
        "/api/v1/users/me/api-keys",
        headers=headers,
        json={"name": "product-only", "scopes": ["product:view"]},
    )
    api_key = created.get_json()["data"]["api_key"]
    response = client.get(
        "/api/v1/agent/recommendations", headers={"X-API-Key": api_key}
    )
    assert response.status_code == 401
