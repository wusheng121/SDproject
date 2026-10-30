import struct
import zlib
from io import BytesIO

import pytest

from extensions import db
from models import BehaviorEvent, Category, Order, OrderItem, Product, ProductCategory, User
from services.listing_vision import ListingVisionError, recognize_listing


def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def test_image_recognition_mock_requires_uploaded_image(client):
    response = client.post("/api/ai/recognize", data={})
    assert response.status_code == 400

    response = client.post(
        "/api/ai/recognize",
        data={"image": (BytesIO(b"mock-image"), "item.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    recognition = response.get_json()["data"]["recognition"]
    assert recognition["category"]
    assert recognition["condition"]


def _png() -> bytes:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"\x00" + bytes([20, 40, 80])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _upload(client, headers, content=None, mime="image/png"):
    return client.post(
        "/api/ai/listing-recognize",
        headers=headers,
        data={"image": (BytesIO(content or _png()), "item.png", mime)},
        content_type="multipart/form-data",
    )


def test_listing_recognize_requires_login_and_image(client):
    assert client.post("/api/ai/listing-recognize", data={}).status_code == 401
    headers = _login(client)
    response = client.post("/api/ai/listing-recognize", headers=headers, data={})
    assert response.status_code == 400


def test_listing_recognize_failure_does_not_invent_fields(client):
    response = _upload(client, _login(client))
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["recognition"] is None
    assert "填写" in data["message"]


def test_listing_recognize_returns_suggestion_without_price(client, monkeypatch):
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
    response = _upload(client, _login(client))
    assert response.status_code == 200
    recognition = response.get_json()["data"]["recognition"]
    assert recognition["category"] == "耳机"
    assert recognition["name"] == "索尼头戴耳机"
    assert "price" not in recognition


def test_listing_vision_reads_photo_and_keeps_catalog_category(app, monkeypatch):
    seen = {}

    def fake_complete(messages):
        seen["content"] = messages[0]["content"]
        return '{"name":"黑色头戴耳机","brand":"未知品牌","category":"耳机","condition":"看不清","description":"一副黑色头戴耳机"}'

    monkeypatch.setattr("services.listing_vision.api_key", lambda: "sk-test")
    monkeypatch.setattr("services.listing_vision.complete", fake_complete)
    with app.app_context():
        result = recognize_listing(_png(), "image/png")
    assert result == {
        "name": "黑色头戴耳机",
        "brand": "",
        "category": "耳机",
        "condition": "九成新",
        "description": "一副黑色头戴耳机",
        "source": "deepseek",
    }
    assert any(part.get("type") == "image_url" for part in seen["content"])


def test_listing_vision_rejects_category_outside_catalog(app, monkeypatch):
    monkeypatch.setattr("services.listing_vision.api_key", lambda: "sk-test")
    monkeypatch.setattr(
        "services.listing_vision.complete",
        lambda messages: '{"name":"杯子","brand":"","category":"数码产品","condition":"九成新","description":"一个杯子"}',
    )
    with app.app_context():
        with pytest.raises(ListingVisionError):
            recognize_listing(_png(), "image/png")


def test_price_reference_uses_paid_deals_not_listing_prices(client, app):
    with app.app_context():
        category = Category.query.filter_by(name="手机").first()
        seller = User.query.filter_by(username="testuser").first()
        buyer = User.query.filter_by(username="admin").first()
        deals = []
        for price in (1000, 3000):
            product = Product(
                name=f"成交手机-{price}",
                price=9999,
                condition="九成新",
                status="approved",
                seller_id=seller.id,
            )
            product.categories.append(ProductCategory(category=category))
            db.session.add(product)
            db.session.flush()
            deals.append(product)
            db.session.add(BehaviorEvent(user_id=buyer.id, product_id=product.id, behavior_type="view"))
        listed_only = Product(
            name="只标价未成交",
            price=50,
            condition="九成新",
            status="approved",
            seller_id=seller.id,
        )
        listed_only.categories.append(ProductCategory(category=category))
        db.session.add(listed_only)
        order = Order(buyer_id=buyer.id, status="paid", total_amount=4000)
        db.session.add(order)
        db.session.flush()
        for product, price in zip(deals, (1000, 3000)):
            db.session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1, price=price))
        pending = Order(buyer_id=buyer.id, status="pending", total_amount=20)
        db.session.add(pending)
        db.session.flush()
        db.session.add(OrderItem(order_id=pending.id, product_id=listed_only.id, quantity=1, price=20))
        db.session.commit()

    response = client.get("/api/products/price-reference?category=手机")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["source"] == "paid_orders"
    assert data["sample_count"] == 2
    assert data["min_price"] == 1000
    assert data["max_price"] == 3000
    assert data["median_price"] == 2000
    assert data["behavior_product_count"] >= 2


def test_publish_product_saves_listing_details_as_pending(client, app):
    headers = _login(client)
    response = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "带描述的二手教材",
            "description": "书内有少量笔记",
            "price": 20,
            "condition": "九成新",
            "category": "书籍",
            "brand": "测试出版社",
            "has_notes": True,
            "defect_description": "封面轻微折痕",
            "trade_method": "线下当面",
            "trade_location": "图书馆门口",
        },
    )
    assert response.status_code == 200
    product_id = response.get_json()["data"]["id"]
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.status == "pending"
        assert product.has_notes is True
        assert product.trade_location == "图书馆门口"
        assert product.ai_category is None


def test_publish_keeps_user_edits_ahead_of_ai_tags(client, app):
    headers = _login(client)
    response = client.post(
        "/api/products",
        headers=headers,
        json={
            "name": "用户改成了书籍",
            "description": "识图认成耳机，发布时改成书籍",
            "price": 18,
            "condition": "八成新",
            "category": "书籍",
            "ai_category": "耳机",
            "ai_condition": "全新",
        },
    )
    assert response.status_code == 200
    product_id = response.get_json()["data"]["id"]
    with app.app_context():
        product = db.session.get(Product, product_id)
        product.status = "approved"
        db.session.commit()
        assert product.condition == "八成新"
        assert [link.category.name for link in product.categories] == ["书籍"]
        assert product.ai_category == "耳机"
        assert product.ai_condition == "全新"
        user = User.query.filter_by(username="testuser").first()
        user.set_preferred_categories_list(["手机"])
        db.session.commit()
        headphone_id = (
            Product.query.join(ProductCategory, ProductCategory.product_id == Product.id)
            .join(Category, Category.id == ProductCategory.category_id)
            .filter(Category.name == "耳机", Product.status == "approved", Product.id != product_id)
            .first()
            .id
        )

    headers = _login(client)
    recommended = client.get("/api/recommendations?limit=8", headers=headers).get_json()["data"]
    assert recommended["strategy"] == "B"
    assert all("手机" in item["categories"] for item in recommended["items"])
    assert product_id not in {item["id"] for item in recommended["items"]}

    similar = client.get(f"/api/recommendations/similar/{headphone_id}").get_json()["data"]["items"]
    matched = [item for item in similar if item["id"] == product_id]
    assert matched
    assert matched[0]["reason"] == "识图标签补充"


def test_minimum_condition_includes_better_grades_for_list_and_search(client, app):
    with app.app_context():
        category = Category.query.filter_by(name="书籍").first()
        seller = User.query.filter_by(username="testuser").first()
        for grade in ("七成新", "八成新", "九成新", "九五新", "全新"):
            product = Product(
                name=f"成色筛选-{grade}",
                price=10,
                condition=grade,
                status="approved",
                seller_id=seller.id,
            )
            product.categories.append(ProductCategory(category=category))
            db.session.add(product)
        db.session.commit()

    listed = client.get("/api/products?category=书籍&min_condition=八成新&page_size=50").get_json()["data"]
    assert all(item["condition"] != "七成新" for item in listed["items"])
    assert {"八成新", "九成新", "九五新", "全新"}.issubset({item["condition"] for item in listed["items"]})

    searched = client.get("/api/products/search?q=成色筛选&min_condition=八成新").get_json()["data"]
    assert all(item["condition"] != "七成新" for item in searched["items"])
    assert searched["total"] == 4
