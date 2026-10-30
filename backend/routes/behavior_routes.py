"""用户行为路由 - 收藏、浏览等行为记录"""

from flask import Blueprint, request

from auth import login_required
from extensions import db
from models import Product, UserBehavior
from services.trade_service import (
    TradeError,
    create_review,
    find_reviewable_order_id,
    list_my_reviews,
)
from utils.response import err, ok

behavior_bp = Blueprint("behavior_bp", __name__, url_prefix="/api")


@behavior_bp.post("/behavior/favorite")
@login_required
def toggle_favorite(user):
    """
    POST /api/behavior/favorite
    body: { product_id, favorite: true/false }
    切换收藏状态
    """
    payload = request.get_json(silent=True) or {}
    product_id = payload.get("product_id")
    favorite = bool(payload.get("favorite", True))

    if not product_id:
        return err("product_id 不能为空", code=2001)

    product = Product.query.get(int(product_id))
    if not product:
        return err("商品不存在", code=2002, http_status=404)

    existing = UserBehavior.query.filter_by(
        user_id=user.id, 
        product_id=product.id, 
        behavior_type="favorite"
    ).first()
    
    if favorite:
        if not existing:
            db.session.add(UserBehavior(
                user_id=user.id, 
                product_id=product.id, 
                behavior_type="favorite"
            ))
            db.session.commit()
    else:
        if existing:
            db.session.delete(existing)
            db.session.commit()

    return ok({"product_id": product.id, "favorite": favorite}, "已更新收藏状态")


@behavior_bp.get("/favorites")
@login_required
def list_favorites(user):
    """
    GET /api/favorites
    获取用户收藏的商品列表
    """
    behaviors = UserBehavior.query.filter_by(
        user_id=user.id, 
        behavior_type="favorite"
    ).order_by(UserBehavior.created_at.desc()).all()
    
    items = []
    for b in behaviors:
        p = b.product
        if p and p.status == "approved":
            items.append({
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "condition": p.condition,
                "image_url": p.image_url,
                "favorited_at": b.created_at.isoformat() if b.created_at else None,
            })
    
    return ok({"items": items, "total": len(items)})


@behavior_bp.post("/behavior/review")
@login_required
def add_review(user):
    """
    POST /api/behavior/review
    body: { product_id, score(1-5), comment, order_id? }
    对已支付订单中的商品评价。未传 order_id 时，使用最近一笔可评价订单。
    """
    payload = request.get_json(silent=True) or {}
    try:
        product_id = int(payload.get("product_id"))
        score = int(payload.get("score"))
    except (TypeError, ValueError):
        return err("product_id 和 score 不能为空", code=422, http_status=422)
    try:
        order_id = payload.get("order_id")
        if order_id is None:
            order_id = find_reviewable_order_id(user, product_id)
        review = create_review(user, int(order_id), product_id, score, payload.get("comment"))
    except TradeError as exc:
        return err(exc.message, code=exc.status, http_status=exc.status)
    return ok(review, "评价成功")


@behavior_bp.get("/my-reviews")
@login_required
def list_my_reviews_route(user):
    """
    GET /api/my-reviews
    获取我的评价列表
    """
    try:
        items = list_my_reviews(user)
    except TradeError as exc:
        return err(exc.message, code=exc.status, http_status=exc.status)
    return ok({"items": items, "total": len(items)})
