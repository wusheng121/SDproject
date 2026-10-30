from models import Product, UserBehavior


def _login(client, identifier="admin", password="Admin12345"):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def _approved_product(app):
    with app.app_context():
        product = Product.query.filter_by(status="approved").first()
        return product.id, product.name


def test_cart_order_pay_and_review(client, app):
    headers = _login(client)
    product_id, product_name = _approved_product(app)

    own = client.post(
        "/api/v1/cart",
        headers=_login(client, "testuser", "Test12345"),
        json={"product_id": product_id},
    )
    assert own.status_code == 403

    added = client.post("/api/v1/cart", headers=headers, json={"product_id": product_id})
    assert added.status_code == 201
    assert added.get_json()["data"]["created"] is True

    again = client.post("/api/v1/cart", headers=headers, json={"product_id": product_id})
    assert again.status_code == 200
    assert again.get_json()["data"]["created"] is False

    cart = client.get("/api/v1/cart", headers=headers)
    assert cart.status_code == 200
    assert cart.get_json()["data"]["items"][0]["name"] == product_name

    created = client.post("/api/v1/orders", headers=headers, json={})
    assert created.status_code == 201
    order = created.get_json()["data"]
    assert order["status"] == "pending"
    assert order["items"][0]["product_id"] == product_id

    empty_cart = client.get("/api/v1/cart", headers=headers)
    assert empty_cart.get_json()["data"]["items"] == []

    blocked = client.post("/api/v1/cart", headers=headers, json={"product_id": product_id})
    assert blocked.status_code == 409

    unpaid_review = client.post(
        f"/api/v1/orders/{order['id']}/reviews",
        headers=headers,
        json={"product_id": product_id, "score": 5, "comment": "太早了"},
    )
    assert unpaid_review.status_code == 409

    paid = client.post(f"/api/v1/orders/{order['id']}/pay", headers=headers)
    assert paid.status_code == 200
    assert paid.get_json()["data"]["status"] == "paid"

    with app.app_context():
        product = Product.query.get(product_id)
        assert product.status == "sold"
        behavior = UserBehavior.query.filter_by(
            product_id=product_id, behavior_type="order"
        ).first()
        assert behavior is not None

    sold = client.post("/api/v1/cart", headers=headers, json={"product_id": product_id})
    assert sold.status_code == 409

    bad_score = client.post(
        f"/api/v1/orders/{order['id']}/reviews",
        headers=headers,
        json={"product_id": product_id, "score": 6, "comment": "超分"},
    )
    assert bad_score.status_code == 422

    review = client.post(
        f"/api/v1/orders/{order['id']}/reviews",
        headers=headers,
        json={"product_id": product_id, "score": 5, "comment": "成色很好"},
    )
    assert review.status_code == 201

    duplicate = client.post(
        f"/api/v1/orders/{order['id']}/reviews",
        headers=headers,
        json={"product_id": product_id, "score": 4, "comment": "再评一次"},
    )
    assert duplicate.status_code == 409

    public_reviews = client.get(f"/api/v1/products/{product_id}/reviews")
    assert public_reviews.status_code == 200
    assert public_reviews.get_json()["data"]["items"][0]["comment"] == "成色很好"

    with app.app_context():
        review_behavior = UserBehavior.query.filter_by(
            product_id=product_id, behavior_type="review"
        ).first()
        assert review_behavior is not None
        assert review_behavior.value == 5


def test_cancel_pending_order_returns_item_to_cart(client, app):
    headers = _login(client)
    product_id, _ = _approved_product(app)
    added = client.post("/api/v1/cart", headers=headers, json={"product_id": product_id})
    assert added.status_code == 201
    created = client.post("/api/v1/orders", headers=headers, json={})
    order_id = created.get_json()["data"]["id"]

    cancelled = client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.get_json()["data"]["status"] == "cancelled"

    cart = client.get("/api/v1/cart", headers=headers)
    assert cart.get_json()["data"]["items"][0]["product_id"] == product_id

    paid = client.post(f"/api/v1/orders/{order_id}/pay", headers=headers)
    assert paid.status_code == 409


def test_trade_requires_login(client):
    response = client.get("/api/v1/cart")
    assert response.status_code == 401
