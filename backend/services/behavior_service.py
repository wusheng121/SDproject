from datetime import datetime, timedelta

from extensions import db
from models import BehaviorEvent

RECOMMENDATION_BEHAVIOR_TYPES = ("view", "favorite", "add_cart")
BEHAVIOR_WEIGHTS = BehaviorEvent.WEIGHTS
BEHAVIOR_WINDOW_DAYS = 7
BEHAVIOR_LABELS = {
    "view": "浏览",
    "favorite": "收藏",
    "add_cart": "加入购物车",
}


def behavior_window_start(now=None):
    now = now or datetime.utcnow()
    return now - timedelta(days=BEHAVIOR_WINDOW_DAYS)


def record_behavior_event(user_id, product_id, behavior_type, created_at=None):
    if behavior_type not in BEHAVIOR_WEIGHTS:
        return None
    event = BehaviorEvent(
        user_id=user_id,
        product_id=product_id,
        behavior_type=behavior_type,
        created_at=created_at or datetime.utcnow(),
    )
    db.session.add(event)
    return event


def recent_behavior_query(user_id=None, now=None):
    query = BehaviorEvent.recent(now=now)
    if user_id is not None:
        query = query.filter(BehaviorEvent.user_id == user_id)
    return query


def recent_behavior_rows(user_id, now=None):
    return (
        recent_behavior_query(user_id=user_id, now=now)
        .order_by(BehaviorEvent.created_at.desc(), BehaviorEvent.id.desc())
        .all()
    )


def serialize_behavior_event(event):
    product = event.product
    return {
        "id": event.id,
        "user_id": event.user_id,
        "product_id": event.product_id,
        "product_name": product.name if product else None,
        "behavior_type": event.behavior_type,
        "behavior_label": BEHAVIOR_LABELS.get(event.behavior_type, event.behavior_type),
        "weight": BEHAVIOR_WEIGHTS.get(event.behavior_type, 0),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
