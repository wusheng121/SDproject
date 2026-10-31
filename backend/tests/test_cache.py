import time

from models import Product
from services.cache_store import LocalCache, RedisCache, TwoLevelCache


class FakeRedis:
    def __init__(self, broken=False):
        self.store = {}
        self.gets = 0
        self.broken = broken

    def get(self, key):
        self.gets += 1
        if self.broken:
            raise RuntimeError("redis down")
        item = self.store.get(key)
        if item is None:
            return None
        raw, expires_at = item
        if expires_at <= time.time():
            return None
        return raw

    def set(self, key, value, ex):
        if self.broken:
            raise RuntimeError("redis down")
        self.store[key] = (value, time.time() + ex)

    def delete(self, key):
        if self.broken:
            raise RuntimeError("redis down")
        self.store.pop(key, None)


def _login(client, identifier="admin", password="Admin12345"):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['data']['access_token']}"}


def test_local_cache_expires_and_evicts_the_least_recently_used():
    cache = LocalCache(max_items=2)
    cache.set("gone", {"n": 1}, 0)
    assert cache.get("gone") is None

    cache.set("a", {"n": 1}, 30)
    cache.set("b", {"n": 2}, 30)
    assert cache.get("a")["n"] == 1
    cache.set("c", {"n": 3}, 30)
    assert cache.get("b") is None
    assert cache.get("a")["n"] == 1
    assert cache.get("c")["n"] == 3


def test_two_level_reads_local_before_redis_and_invalidate_clears_both():
    fake = FakeRedis()
    cache = TwoLevelCache(LocalCache(8), RedisCache(fake), local_ttl=30, remote_ttl=60)
    assert cache.get("product:1")[1] == "miss"
    cache.set("product:1", {"status": "approved"})
    assert fake.gets == 1

    value, source = cache.get("product:1")
    assert source == "local"
    assert value["status"] == "approved"
    assert fake.gets == 1

    cache.local.clear()
    value, source = cache.get("product:1")
    assert source == "redis"
    assert value["status"] == "approved"
    assert fake.gets == 2

    cache.invalidate("product:1")
    assert cache.get("product:1")[1] == "miss"
    assert fake.store == {}


def test_redis_outage_still_serves_the_local_copy():
    fake = FakeRedis(broken=True)
    cache = TwoLevelCache(LocalCache(8), RedisCache(fake), local_ttl=30, remote_ttl=60)
    cache.set("categories", ["书籍"])
    value, source = cache.get("categories")
    assert source == "local"
    assert value == ["书籍"]
    cache.local.clear()
    assert cache.get("categories")[1] == "miss"


def test_category_and_price_reference_hit_the_local_cache(client):
    first = client.get("/api/categories")
    second = client.get("/api/categories")
    assert first.status_code == 200
    assert first.headers["X-Cache"] == "miss"
    assert second.headers["X-Cache"] == "local"
    assert first.get_json()["data"]["items"] == second.get_json()["data"]["items"]

    price = client.get("/api/products/price-reference?category=耳机")
    again = client.get("/api/products/price-reference?category=耳机")
    assert price.headers["X-Cache"] == "miss"
    assert again.headers["X-Cache"] == "local"
    assert price.get_json()["data"] == again.get_json()["data"]

    missing = client.get("/api/products/price-reference?category=没有这个品类")
    assert missing.status_code == 400
    assert "X-Cache" not in missing.headers

    ready = client.get("/health/ready")
    assert ready.get_json()["checks"]["cache"] == "local"


def test_product_detail_cache_keeps_favorite_state_fresh(client, app):
    with app.app_context():
        product_id = Product.query.filter_by(name="三体全集").one().id
    first = client.get(f"/api/products/{product_id}")
    assert first.headers["X-Cache"] == "miss"
    assert first.get_json()["data"]["is_favorited"] is None

    headers = _login(client)
    client.post(
        "/api/v1/behaviors",
        headers=headers,
        json={"product_id": product_id, "behavior_type": "favorite", "value": 1},
    )
    second = client.get(f"/api/products/{product_id}", headers=headers)
    assert second.headers["X-Cache"] == "local"
    assert second.get_json()["data"]["name"] == "三体全集"
    assert second.get_json()["data"]["is_favorited"] is True

    missing = client.get("/api/products/999999")
    assert missing.status_code == 404
    assert "X-Cache" not in missing.headers


def test_product_detail_falls_back_to_redis_after_the_local_copy_is_gone(client, app):
    with app.app_context():
        product_id = Product.query.filter_by(name="三体全集").one().id
        cache = app.extensions["catalog_cache"]
        original = cache.remote
        fake = FakeRedis()
        cache.remote = RedisCache(fake)
    try:
        first = client.get(f"/api/products/{product_id}")
        assert first.headers["X-Cache"] == "miss"
        cache.local.clear()
        second = client.get(f"/api/products/{product_id}")
        assert second.headers["X-Cache"] == "redis"
        assert second.get_json()["data"]["id"] == product_id
        assert second.get_json()["data"]["status"] == "approved"
    finally:
        cache.remote = original
        cache.clear()


def test_payment_refreshes_product_status_and_deal_price(client, app):
    with app.app_context():
        product_id = Product.query.filter_by(name="三体全集").one().id
    assert client.get(f"/api/products/{product_id}").headers["X-Cache"] == "miss"
    assert client.get("/api/products/price-reference?category=书籍").headers["X-Cache"] == "miss"
    assert client.get(f"/api/products/{product_id}").headers["X-Cache"] == "local"

    headers = _login(client)
    assert client.post("/api/v1/cart", headers=headers, json={"product_id": product_id}).status_code == 201
    order = client.post("/api/v1/orders", headers=headers, json={})
    paid = client.post(f"/api/v1/orders/{order.get_json()['data']['id']}/pay", headers=headers)
    assert paid.status_code == 200

    detail = client.get(f"/api/products/{product_id}")
    assert detail.headers["X-Cache"] == "miss"
    assert detail.get_json()["data"]["status"] == "sold"
    price = client.get("/api/products/price-reference?category=书籍")
    assert price.headers["X-Cache"] == "miss"
    assert price.get_json()["data"]["sample_count"] == 1
    assert price.get_json()["data"]["min_price"] == 60
