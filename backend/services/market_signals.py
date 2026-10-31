"""推荐和行为、成交用的是同一套表。价格参考只读这些记录，不另建表。"""

from sqlalchemy import func

from extensions import db
from models import BehaviorEvent, Category, Order, OrderItem, Product, ProductCategory


def recent_behavior_counts() -> dict[int, int]:
    """近 7 天浏览、收藏、加购次数。推荐热度用的就是这份统计。"""
    return dict(
        BehaviorEvent.recent()
        .with_entities(BehaviorEvent.product_id, func.count(BehaviorEvent.id))
        .group_by(BehaviorEvent.product_id)
        .all()
    )


def paid_deal_prices(category_name: str) -> list[float]:
    """该品类已支付订单里的成交价。未支付订单和在售标价不算。"""
    rows = (
        db.session.query(OrderItem.price)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .join(ProductCategory, ProductCategory.product_id == Product.id)
        .join(Category, Category.id == ProductCategory.category_id)
        .filter(Order.status == "paid", Category.name == category_name)
        .all()
    )
    return sorted(float(price) for (price,) in rows)


def recent_behavior_product_count(category_name: str) -> int:
    counts = recent_behavior_counts()
    if not counts:
        return 0
    product_ids = {
        product_id
        for (product_id,) in db.session.query(ProductCategory.product_id)
        .join(Category, Category.id == ProductCategory.category_id)
        .filter(Category.name == category_name)
        .all()
    }
    return sum(1 for product_id in product_ids if counts.get(product_id))


def price_reference(category_name: str) -> dict:
    prices = paid_deal_prices(category_name)
    payload = {
        "category": category_name,
        "sample_count": len(prices),
        "behavior_product_count": recent_behavior_product_count(category_name),
        "source": "paid_orders",
        "min_price": None,
        "median_price": None,
        "max_price": None,
    }
    if not prices:
        return payload
    middle = len(prices) // 2
    median = prices[middle] if len(prices) % 2 else (prices[middle - 1] + prices[middle]) / 2
    payload.update(
        {
            "min_price": round(prices[0], 2),
            "median_price": round(median, 2),
            "max_price": round(prices[-1], 2),
        }
    )
    return payload
