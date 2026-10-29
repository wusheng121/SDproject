from extensions import db
from models import OperationLog, Product, User


def _admin_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": "Admin12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def _make_product(app, status="pending"):
    with app.app_context():
        seller = User.query.filter_by(username="testuser").first()
        product = Product(
            name=f"测试商品-{status}",
            description="用于管理后台测试",
            price=99.0,
            condition="九成新",
            status=status,
            seller_id=seller.id,
        )
        db.session.add(product)
        db.session.commit()
        return product.id


def test_admin_lists_users_and_stats(client, app):
    headers = _admin_headers(client)
    users = client.get("/api/v1/admin/users", headers=headers)
    assert users.status_code == 200
    assert users.get_json()["pagination"]["total"] >= 3

    stats = client.get("/api/v1/admin/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.get_json()["data"]["users"]["total"] >= 3
    assert "today" in stats.get_json()["data"]


def test_product_audit_flow_and_logs(client, app):
    headers = _admin_headers(client)
    product_id = _make_product(app)

    pending = client.get("/api/v1/admin/products?status=pending", headers=headers)
    assert pending.status_code == 200
    assert any(item["id"] == product_id for item in pending.get_json()["data"])

    approved = client.post(f"/api/v1/admin/products/{product_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.get_json()["data"]["product"]["status"] == "approved"

    offline = client.post(
        f"/api/v1/admin/products/{product_id}/offline",
        headers=headers,
        json={"reason": "违规"},
    )
    assert offline.status_code == 200
    assert offline.get_json()["data"]["product"]["status"] == "offline"

    logs = client.get("/api/v1/admin/operation-logs", headers=headers)
    assert logs.status_code == 200
    actions = [item["action"] for item in logs.get_json()["data"]]
    assert "product.approve" in actions
    assert "product.offline" in actions

    with app.app_context():
        assert OperationLog.query.filter_by(action="product.approve").count() == 1


def test_reject_requires_reason_and_guards_state(client, app):
    headers = _admin_headers(client)
    product_id = _make_product(app)
    rejected = client.post(
        f"/api/v1/admin/products/{product_id}/reject",
        headers=headers,
        json={},
    )
    assert rejected.status_code == 422

    rejected = client.post(
        f"/api/v1/admin/products/{product_id}/reject",
        headers=headers,
        json={"reason": "信息不完整"},
    )
    assert rejected.status_code == 200
    assert rejected.get_json()["data"]["product"]["status"] == "rejected"

    invalid = client.post(f"/api/v1/admin/products/{product_id}/offline", headers=headers)
    assert invalid.status_code == 409


def test_role_assignment_and_user_type_sync(client, app):
    headers = _admin_headers(client)
    with app.app_context():
        user_id = User.query.filter_by(username="testuser").first().id

    response = client.put(
        f"/api/v1/admin/users/{user_id}/roles",
        headers=headers,
        json={"roles": ["admin"]},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["user"]["user_type"] == "admin"
    assert "admin" in response.get_json()["data"]["user"]["roles"]
