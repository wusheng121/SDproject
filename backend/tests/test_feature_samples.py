"""两边分支合并后的功能样例。每个样例只验证一件能被用户看出来的事。"""

from io import BytesIO

from extensions import db
from models import Product


def _login(client, identifier="admin", password="Admin12345"):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def _product(app, name):
    with app.app_context():
        product = Product.query.filter_by(name=name, status="approved").one()
        return product.id


def test_sample_seller_cannot_buy_own_product_and_buyer_can_remove_it(client, app):
    product_id = _product(app, "三体全集")
    seller = _login(client, "testuser", "Test12345")
    buyer = _login(client)

    own = client.post("/api/v1/cart", headers=seller, json={"product_id": product_id})
    assert own.status_code == 403

    added = client.post("/api/v1/cart", headers=buyer, json={"product_id": product_id})
    assert added.status_code == 201
    removed = client.delete(f"/api/v1/cart/{product_id}", headers=buyer)
    assert removed.status_code == 200
    assert client.get("/api/v1/cart", headers=buyer).get_json()["data"]["items"] == []


def test_sample_order_stays_after_logout_and_only_the_buyer_sees_it(client, app):
    product_id = _product(app, "三体全集")
    buyer = _login(client)
    client.post("/api/v1/cart", headers=buyer, json={"product_id": product_id})
    created = client.post("/api/v1/orders", headers=buyer, json={})
    assert created.status_code == 201
    order_id = created.get_json()["data"]["id"]

    assert client.post("/api/v1/auth/logout", headers=buyer).status_code == 200
    buyer = _login(client)
    orders = client.get("/api/v1/orders", headers=buyer).get_json()["data"]["items"]
    assert [item["id"] for item in orders] == [order_id]

    seller_orders = client.get("/api/v1/orders", headers=_login(client, "testuser", "Test12345"))
    assert seller_orders.get_json()["data"]["items"] == []


def test_sample_search_filters_keyword_price_and_condition(client):
    cheap = client.get("/api/products/search?category=平板&max_price=1000&min_condition=八成新")
    names = {item["name"] for item in cheap.get_json()["data"]["items"]}
    assert names == {"小米平板 5"}

    better = client.get("/api/products/search?category=平板&min_condition=九成新")
    better_names = {item["name"] for item in better.get_json()["data"]["items"]}
    assert better_names == {"iPad 9 64G"}

    keyword = client.get("/api/products/search?q=iPhone&sort=price_asc")
    assert keyword.get_json()["data"]["items"][0]["name"] == "iPhone 12 128G"


def test_sample_browse_photo_recognition_stays_a_fixed_mock(client):
    response = client.post(
        "/api/ai/recognize",
        data={"image": (BytesIO(b"not-a-real-photo"), "汽车.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["mock"] is True
    assert body["recognition"]["category"] == "数码产品"


def test_sample_favorite_and_seven_day_behavior_reach_admin(client, app):
    product_id = _product(app, "小米 13 256G")
    buyer = _login(client)
    recorded = client.post(
        "/api/v1/behaviors",
        headers=buyer,
        json={"product_id": product_id, "behavior_type": "favorite", "value": 1},
    )
    assert recorded.status_code == 201
    favorites = client.get("/api/v1/users/me/favorites", headers=buyer).get_json()["data"]
    assert any(item["id"] == product_id for item in favorites)

    with app.app_context():
        from models import User

        target_id = User.query.filter_by(username="admin").one().id

    detail = client.get(f"/api/v1/admin/users/{target_id}", headers=buyer)
    events = detail.get_json()["data"]["recent_behaviors"]
    assert detail.get_json()["data"]["behavior_window_days"] == 7
    assert any(event["product_id"] == product_id and event["behavior_type"] == "favorite" for event in events)


def test_sample_favorite_weighs_more_than_a_view(client, app):
    phone_id = _product(app, "小米 13 256G")
    book_id = _product(app, "三体全集")
    buyer = _login(client)
    client.post("/api/v1/behaviors", headers=buyer, json={"product_id": phone_id, "behavior_type": "favorite", "value": 1})
    client.post("/api/v1/behaviors", headers=buyer, json={"product_id": book_id, "behavior_type": "view"})

    preview = client.post(
        "/api/recommendations/preview",
        headers=buyer,
        json={"stage": "D", "categories": [], "behavior_count": 12, "limit": 24},
    )
    items = preview.get_json()["data"]["items"]
    phone = next(item for item in items if "手机" in item["categories"] and item["id"] != phone_id)
    book = next(item for item in items if "书籍" in item["categories"] and item["id"] != book_id)
    assert phone["recommendation_score"] > book["recommendation_score"]


def test_sample_interest_changes_home_recommendations_and_next_batch(client):
    buyer = _login(client)
    saved = client.put("/api/v1/users/me/preferences", headers=buyer, json={"categories": ["手机"]})
    assert saved.get_json()["data"]["preferred_categories"] == ["手机"]

    first = client.get("/api/recommendations?limit=1&offset=0", headers=buyer).get_json()["data"]
    second = client.get("/api/recommendations?limit=1&offset=1", headers=buyer).get_json()["data"]
    assert first["strategy"] == "B"
    assert second["strategy"] == "B"
    assert "手机" in first["items"][0]["categories"]
    assert "手机" in second["items"][0]["categories"]
    assert first["items"][0]["id"] != second["items"][0]["id"]


def test_sample_publish_without_photo_then_admin_approves_and_buyer_adds_cart(client, app):
    seller = _login(client, "testuser", "Test12345")
    published = client.post(
        "/api/products",
        headers=seller,
        json={
            "name": "样例教材",
            "description": "没有拍照，直接填写",
            "price": 15,
            "condition": "九成新",
            "category": "书籍",
            "brand": "样例出版社",
            "has_notes": False,
            "trade_method": "线下当面",
            "trade_location": "图书馆",
        },
    )
    assert published.status_code == 200
    product_id = published.get_json()["data"]["id"]
    assert published.get_json()["data"]["status"] == "pending"

    admin = _login(client)
    approved = client.post(f"/api/v1/admin/products/{product_id}/approve", headers=admin)
    assert approved.status_code == 200
    assert approved.get_json()["data"]["product"]["status"] == "approved"

    added = client.post("/api/v1/cart", headers=admin, json={"product_id": product_id})
    assert added.status_code == 201


def test_sample_listing_photo_does_not_set_the_price(client, app, monkeypatch):
    monkeypatch.setattr(
        "routes.product_routes.recognize_listing",
        lambda image_bytes, mime: {
            "name": "索尼头戴耳机",
            "brand": "索尼",
            "category": "耳机",
            "condition": "九五新",
            "description": "黑色头戴耳机",
            "source": "deepseek",
        },
    )
    headers = _login(client, "testuser", "Test12345")
    recognized = client.post(
        "/api/ai/listing-recognize",
        headers=headers,
        data={"image": (BytesIO(b"photo"), "headphones.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    suggestion = recognized.get_json()["data"]["recognition"]
    assert suggestion["category"] == "耳机"
    assert "price" not in suggestion

    reference = client.get("/api/products/price-reference?category=耳机")
    assert reference.status_code == 200
    assert reference.get_json()["data"]["sample_count"] == 0

    published = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "我改成的耳机名",
            "description": suggestion["description"],
            "price": 66,
            "condition": "八成新",
            "category": "耳机",
            "ai_category": suggestion["category"],
            "ai_condition": suggestion["condition"],
        },
    )
    product_id = published.get_json()["data"]["id"]
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.name == "我改成的耳机名"
        assert product.condition == "八成新"
        assert float(product.price) == 66
        assert product.ai_category == "耳机"
        assert product.ai_condition == "九五新"


def test_sample_assistant_follow_up_refuses_orders_and_reads_a_photo(client, monkeypatch):
    buyer = _login(client, "testuser", "Test12345")
    first = client.post("/api/v1/assistant/chat", headers=buyer, json={"message": "平板"})
    session_id = first.get_json()["data"]["session_id"]
    assert any(item["name"] == "iPad 9 64G" for item in first.get_json()["data"]["items"])

    narrowed = client.post(
        "/api/v1/assistant/chat",
        headers=buyer,
        json={"message": "只要九成新", "session_id": session_id},
    )
    assert all(item["condition"] == "九成新" for item in narrowed.get_json()["data"]["items"])

    refused = client.post(
        "/api/v1/assistant/chat",
        headers=buyer,
        json={"message": "帮我下单", "session_id": session_id},
    )
    assert refused.get_json()["data"]["refused"] is True
    assert client.get("/api/v1/orders", headers=buyer).get_json()["data"]["items"] == []

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(
        "services.agent_dialogue.recognize_photo",
        lambda _data_url: {
            "category": "耳机",
            "seen": "耳机",
            "brand": "索尼",
            "condition": "九成新",
            "description": "一副头戴耳机",
            "source": "deepseek",
            "matched": True,
        },
    )
    monkeypatch.setattr("services.agent_dialogue.complete", lambda _messages: "按图片找到耳机，成色没有拿来筛选。")
    photo = client.post(
        "/api/v1/assistant/chat",
        headers=buyer,
        json={
            "message": "",
            "filename": "headphones.jpg",
            "image_data_url": "data:image/jpeg;base64,cccc",
        },
    )
    body = photo.get_json()["data"]
    assert body["slots"]["category"] == "耳机"
    assert body["slots"]["condition"] is None
    assert {item["condition"] for item in body["items"]} >= {"全新", "九五新"}
    assert "耳机" in body["reply"]


def test_sample_cheaper_follow_up_and_filename_photo(client):
    buyer = _login(client, "testuser", "Test12345")
    first = client.post("/api/v1/assistant/chat", headers=buyer, json={"message": "1000元以内的平板"})
    session_id = first.get_json()["data"]["session_id"]
    cheaper = client.post(
        "/api/v1/assistant/chat",
        headers=buyer,
        json={"message": "便宜一点", "session_id": session_id},
    )
    assert cheaper.get_json()["data"]["slots"]["max_price"] == 800
    assert all(item["price"] <= 800 for item in cheaper.get_json()["data"]["items"])

    named = client.post(
        "/api/v1/assistant/chat",
        headers=buyer,
        json={"message": "", "filename": "耳机.jpg"},
    )
    body = named.get_json()["data"]
    assert body["recognition"]["source"] == "mock"
    assert body["recognition"]["category"] == "耳机"
    assert body["slots"]["condition"] is None
    assert all("耳机" in item["categories"] for item in body["items"])


def test_sample_car_photo_does_not_return_phones(client, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setattr(
        "services.agent_dialogue.recognize_photo",
        lambda _data_url: {
            "category": None,
            "seen": "汽车",
            "brand": "",
            "condition": None,
            "description": "一辆汽车",
            "source": "deepseek",
            "matched": False,
        },
    )
    monkeypatch.setattr("services.agent_dialogue.complete", lambda _messages: "商品库里没有汽车。")
    buyer = _login(client, "testuser", "Test12345")
    first = client.post("/api/v1/assistant/chat", headers=buyer, json={"message": "手机"})
    photo = client.post(
        "/api/v1/assistant/chat",
        headers=buyer,
        json={
            "message": "",
            "session_id": first.get_json()["data"]["session_id"],
            "filename": "汽车.jpg",
            "image_data_url": "data:image/jpeg;base64,dddd",
        },
    )
    body = photo.get_json()["data"]
    assert body["slots"]["category"] is None
    assert body["items"] == []
    assert "汽车" in body["reply"]


def test_sample_listing_failure_keeps_the_form_empty(client, monkeypatch):
    from services.listing_vision import ListingVisionError

    headers = _login(client, "testuser", "Test12345")
    missing = client.post("/api/ai/listing-recognize", headers=headers, data={})
    assert missing.status_code == 400

    def fail(_image_bytes, _mime):
        raise ListingVisionError("识图暂时不可用，请直接填写")

    monkeypatch.setattr("routes.product_routes.recognize_listing", fail)
    failed = client.post(
        "/api/ai/listing-recognize",
        headers=headers,
        data={"image": (BytesIO(b"photo"), "lamp.webp", "image/webp")},
        content_type="multipart/form-data",
    )
    assert failed.status_code == 200
    assert failed.get_json()["data"]["recognition"] is None


def test_sample_pay_then_review_and_cancel_returns_the_item(client, app):
    book_id = _product(app, "三体全集")
    phone_id = _product(app, "小米 13 256G")
    buyer = _login(client)

    client.post("/api/v1/cart", headers=buyer, json={"product_id": book_id})
    order = client.post("/api/v1/orders", headers=buyer, json={}).get_json()["data"]
    paid = client.post(f"/api/v1/orders/{order['id']}/pay", headers=buyer)
    assert paid.status_code == 200
    assert paid.get_json()["data"]["status"] == "paid"
    sold = client.post("/api/v1/cart", headers=buyer, json={"product_id": book_id})
    assert sold.status_code == 409
    review = client.post(
        f"/api/v1/orders/{order['id']}/reviews",
        headers=buyer,
        json={"product_id": book_id, "score": 5, "comment": "书很完整"},
    )
    assert review.status_code == 201

    client.post("/api/v1/cart", headers=buyer, json={"product_id": phone_id})
    pending = client.post("/api/v1/orders", headers=buyer, json={}).get_json()["data"]
    cancelled = client.post(f"/api/v1/orders/{pending['id']}/cancel", headers=buyer)
    assert cancelled.status_code == 200
    cart = client.get("/api/v1/cart", headers=buyer).get_json()["data"]["items"]
    assert [item["product_id"] for item in cart] == [phone_id]
