from models import Product


def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def test_favorite_is_visible_in_favorites_list(client, app):
    headers = _login(client)
    with app.app_context():
        product = Product.query.filter_by(status="approved").first()
        product_id = product.id
        product_name = product.name

    added = client.post(
        "/api/v1/behaviors",
        headers=headers,
        json={"product_id": product_id, "behavior_type": "favorite", "value": 1},
    )
    assert added.status_code == 201

    favorites = client.get("/api/v1/users/me/favorites", headers=headers)
    assert favorites.status_code == 200
    items = favorites.get_json()["data"]
    assert any(item["id"] == product_id and item["name"] == product_name for item in items)

    removed = client.post(
        "/api/v1/behaviors",
        headers=headers,
        json={"product_id": product_id, "behavior_type": "favorite", "value": 0},
    )
    assert removed.status_code == 201
    after_remove = client.get("/api/v1/users/me/favorites", headers=headers)
    assert all(item["id"] != product_id for item in after_remove.get_json()["data"])
