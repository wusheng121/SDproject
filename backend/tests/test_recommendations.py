from extensions import db
from models import Product, User


def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def test_preferences_change_stage_b_recommendation_results(client, app):
    headers = _login(client)
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        user_id = user.id
        user.set_preferred_categories_list(["手机"])
        db.session.commit()

    response = client.get("/api/recommendations?limit=8", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["strategy"] == "B"
    assert payload["preferences"] == ["手机"]
    assert payload["items"]
    assert all("手机" in item["categories"] for item in payload["items"])

    with app.app_context():
        user = db.session.get(User, user_id)
        user.set_preferred_categories_list(["书籍"])
        db.session.commit()

    changed = client.get("/api/recommendations?limit=8", headers=headers).get_json()["data"]
    assert changed["preferences"] == ["书籍"]
    assert changed["items"]
    assert all("书籍" in item["categories"] for item in changed["items"])


def test_recommendation_preview_selects_all_four_stages(client):
    headers = _login(client)
    cases = [
        ({"stage": "A", "categories": [], "behavior_count": 0}, "A"),
        ({"stage": "B", "categories": ["手机"], "behavior_count": 0}, "B"),
        ({"stage": "C", "categories": ["手机"], "behavior_count": 3}, "C"),
        ({"stage": "D", "categories": ["手机"], "behavior_count": 12}, "D"),
    ]
    for request_body, expected_stage in cases:
        response = client.post("/api/recommendations/preview", headers=headers, json=request_body)
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["strategy"] == expected_stage
        assert data["strategy_name"]
        assert all("recommendation_score" in item and "reason" in item for item in data["items"])


def test_recommendation_offset_returns_next_batch(client, app):
    headers = _login(client)
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        user.set_preferred_categories_list([])
        db.session.commit()

    first = client.get("/api/recommendations?limit=3&offset=0", headers=headers).get_json()["data"]
    second = client.get("/api/recommendations?limit=3&offset=3", headers=headers).get_json()["data"]
    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids
    assert second_ids
    assert first_ids.isdisjoint(second_ids)


def test_actual_behavior_count_controls_stage(client, app):
    headers = _login(client)
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        user_id = user.id
        user.set_preferred_categories_list(["手机"])
        products = Product.query.filter_by(status="approved").limit(10).all()
        from models import BehaviorEvent
        db.session.add_all(
            BehaviorEvent(user_id=user_id, product_id=product.id, behavior_type="view")
            for product in products
        )
        db.session.commit()

    response = client.get("/api/recommendations?limit=6", headers=headers)
    payload = response.get_json()["data"]
    assert payload["strategy"] == "D"
    assert payload["recorded_behavior_count"] == 10
