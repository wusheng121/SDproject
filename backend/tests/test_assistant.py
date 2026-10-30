def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def _chat(client, headers, message, session_id=None, filename=None):
    return client.post(
        "/api/v1/assistant/chat",
        headers=headers,
        json={"message": message, "session_id": session_id, "filename": filename},
    )


def test_follow_up_keeps_category_and_can_refuse_writes(client, app):
    from models import Product

    headers = _login(client)
    first = _chat(client, headers, "平板")
    assert first.status_code == 200
    body = first.get_json()["data"]
    assert body["skill"] == "search"
    assert "已为您找到" in body["reply"]
    assert len(body["items"]) >= 2
    session_id = body["session_id"]

    second = _chat(client, headers, "只要九成新", session_id)
    assert second.status_code == 200
    narrowed = second.get_json()["data"]
    assert narrowed["slots"]["category"] == "平板"
    assert narrowed["slots"]["condition"] == "九成新"
    assert narrowed["items"]
    assert all(item["condition"] == "九成新" for item in narrowed["items"])

    refused = _chat(client, headers, "帮我删掉这个商品", session_id)
    assert refused.status_code == 200
    assert refused.get_json()["data"]["refused"] is True
    assert refused.get_json()["data"]["items"] == []

    with app.app_context():
        assert Product.query.filter_by(status="approved").count() >= 1


def test_image_name_is_enough_to_recognize_without_model_api(client):
    headers = _login(client)
    response = _chat(client, headers, "", filename="耳机.jpg")
    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["recognition"]["category"] == "耳机"
    assert body["recognition"]["source"] == "mock"
    assert body["items"]
    assert all("耳机" in item["categories"] for item in body["items"])


def test_price_follow_up_lowers_the_previous_cap(client):
    headers = _login(client)
    first = _chat(client, headers, "1000元以内的平板")
    assert first.status_code == 200
    body = first.get_json()["data"]
    assert body["slots"]["max_price"] == 1000
    assert all(item["price"] <= 1000 for item in body["items"])

    second = _chat(client, headers, "便宜一点", body["session_id"])
    assert second.status_code == 200
    assert second.get_json()["data"]["slots"]["max_price"] == 800


def test_assistant_requires_login(client):
    response = client.post("/api/v1/assistant/chat", json={"message": "耳机"})
    assert response.status_code == 401
