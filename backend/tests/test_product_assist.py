from io import BytesIO

from extensions import db
from models import Category, Product, ProductCategory, User


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


def test_price_reference_aggregates_approved_products(client, app):
    with app.app_context():
        category = Category.query.filter_by(name="手机").first()
        seller = User.query.filter_by(username="testuser").first()
        for price in (1000, 2000, 3000):
            product = Product(
                name=f"价格参考商品-{price}",
                price=price,
                condition="九成新",
                status="approved",
                seller_id=seller.id,
            )
            product.categories.append(ProductCategory(category=category))
            db.session.add(product)
        db.session.commit()
        existing_prices = [
            price for (price,) in Product.query.join(ProductCategory).join(Category)
            .filter(
                Product.status == "approved",
                Category.name == "手机",
                Product.condition.in_(["九成新", "九五新", "全新"]),
            )
            .with_entities(Product.price)
            .all()
        ]

    response = client.get("/api/products/price-reference?category=手机&condition=九成新")
    assert response.status_code == 200
    data = response.get_json()["data"]
    prices = sorted(existing_prices)
    middle = len(prices) // 2
    expected_median = prices[middle] if len(prices) % 2 else (prices[middle - 1] + prices[middle]) / 2
    assert data["sample_count"] == len(prices)
    assert data["min_price"] == prices[0]
    assert data["median_price"] == expected_median
    assert data["max_price"] == prices[-1]


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
