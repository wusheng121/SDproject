from flask import Blueprint, request

from auth import login_required
from extensions import db
from models import Product, UserBehavior
from services.behavior_service import record_behavior_event
from utils.response import api_error, api_ok
from utils.serializers import product_public

behavior_v1_bp = Blueprint("behavior_v1_bp", __name__, url_prefix="/api/v1")

ALLOWED_TYPES = {"view", "favorite", "add_cart", "order", "review"}


@behavior_v1_bp.post("/behaviors")
@login_required
def record_behavior(user):
    payload = request.get_json(silent=True) or {}
    try:
        product_id = int(payload.get("product_id"))
    except (TypeError, ValueError):
        return api_error("VALIDATION_ERROR", "product_id 无效", 422)
    behavior_type = (payload.get("behavior_type") or "").strip()
    if behavior_type not in ALLOWED_TYPES:
        return api_error("VALIDATION_ERROR", "behavior_type 无效", 422)
    product = db.session.get(Product, product_id)
    if not product or product.status != "approved":
        return api_error("NOT_FOUND", "商品不存在或未上架", 404)
    value = payload.get("value")
    existing = UserBehavior.query.filter_by(
        user_id=user.id, product_id=product.id, behavior_type=behavior_type
    ).first()
    if behavior_type == "favorite":
        if value == 0:
            if existing:
                db.session.delete(existing)
        elif not existing:
            db.session.add(
                UserBehavior(
                    user_id=user.id,
                    product_id=product.id,
                    behavior_type=behavior_type,
                    value=1,
                )
            )
    else:
        db.session.add(
            UserBehavior(
                user_id=user.id,
                product_id=product.id,
                behavior_type=behavior_type,
                value=value,
            )
        )
    
    if behavior_type in {"view", "favorite", "add_cart"}:
        record_behavior_event(user.id, product.id, behavior_type)
    
    db.session.commit()
    return api_ok({"recorded": True}, status=201)


@behavior_v1_bp.get("/users/me/favorites")
@login_required
def list_favorites(user):
    rows = (
        UserBehavior.query.filter_by(user_id=user.id, behavior_type="favorite")
        .order_by(UserBehavior.created_at.desc())
        .all()
    )
    items = [
        product_public(row.product)
        for row in rows
        if row.product and row.product.status == "approved"
    ]
    return api_ok(items)


@behavior_v1_bp.get("/users/me/behaviors")
@login_required
def list_behaviors(user):
    rows = (
        UserBehavior.query.filter_by(user_id=user.id)
        .order_by(UserBehavior.created_at.desc())
        .limit(200)
        .all()
    )
    return api_ok(
        [
            {
                "id": row.id,
                "product_id": row.product_id,
                "behavior_type": row.behavior_type,
                "value": row.value,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    )
