from services.nl_filter import parse_nl


def test_parse_price_condition_and_category():
    slots = parse_nl("300元以内九成新手机", ["书籍", "手机"])
    assert slots["category"] == "手机"
    assert slots["min_condition"] == "九成新"
    assert slots["max_price"] == 300
    assert slots["keyword"] == ""


def test_parse_price_range():
    slots = parse_nl("100到200元的保温杯", ["保温杯"])
    assert slots["category"] == "保温杯"
    assert slots["min_price"] == 100
    assert slots["max_price"] == 200


def test_nl_filter_endpoint_returns_matching_filters(client):
    response = client.post("/api/ai/filter/nl", json={"text": "300元以内九成新手机"})
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["filters"]["category"] == "手机"
    assert data["filters"]["max_price"] == 300
    assert all(item["price"] <= 300 for item in data["items"])
    assert all(item["condition"] in {"九成新", "九五新", "全新"} for item in data["items"])


def test_search_keeps_sql_text_out_of_the_query(client):
    attack = client.get("/api/products/search", query_string={"q": "' OR 1=1 --"})
    assert attack.status_code == 200
    assert attack.is_json
    assert attack.get_json()["data"]["total"] == 0


def test_script_in_product_name_stays_inside_json(client, app):
    from extensions import db
    from models import Product

    with app.app_context():
        product = Product.query.filter_by(status="approved").first()
        original = product.name
        product.name = "<script>alert(1)</script>"
        db.session.commit()
        product_id = product.id
    response = client.get(f"/api/products/{product_id}")
    body = response.get_data(as_text=True)
    assert response.is_json
    assert "<script>alert(1)</script>" in body
    assert response.get_json()["data"]["name"] == "<script>alert(1)</script>"
    with app.app_context():
        product = db.session.get(Product, product_id)
        product.name = original
        db.session.commit()


def test_recognize_query_requires_an_image(client):
    response = client.post("/api/ai/recognize-query", json={})
    assert response.status_code == 400


def test_recommendation_quality_uses_behavior_rows(client, app):
    from extensions import db
    from models import BehaviorEvent, Product, User

    login = client.post("/api/v1/auth/login", json={"identifier": "testuser", "password": "Test12345"})
    headers = {"Authorization": f"Bearer {login.get_json()['data']['access_token']}"}
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        user.set_preferred_categories_list(["手机"])
        products = Product.query.filter_by(status="approved").limit(10).all()
        db.session.add_all(
            BehaviorEvent(user_id=user.id, product_id=product.id, behavior_type="view")
            for product in products
        )
        db.session.commit()
    response = client.get("/api/recommendations/quality", headers=headers)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["sample_users"] >= 1
    assert 0 <= data["precision"] <= 1
    assert 0 <= data["recall"] <= 1
    assert 0 <= data["coverage"] <= 1
    assert 0 <= data["diversity"] <= 1
    home = client.get("/api/recommendations?limit=6", headers=headers).get_json()["data"]
    assert home["strategy"] == "D"
    assert "ALS" in home["strategy_name"]
