from collections import Counter

from flask import Blueprint, request

from auth import login_required
from extensions import db
from models import Category, Product, ProductCategory
from services.behavior_service import BEHAVIOR_WEIGHTS, recent_behavior_rows
from services.market_signals import recent_behavior_counts
from utils.response import api_error, api_ok

recommendation_bp = Blueprint("recommendation_bp", __name__, url_prefix="/api")

STAGE_LABELS = {
    "A": "全局热门",
    "B": "兴趣内容推荐",
    "C": "内容与行为轻量混合",
    "D": "协同行为推荐",
}


def _recommend(user_id, categories, behavior_count, limit, offset, forced_stage=None):
    categories = list(dict.fromkeys(str(value).strip() for value in categories if str(value).strip()))
    history = recent_behavior_rows(user_id)
    actual_behavior_count = len(history)
    stage_behavior_count = actual_behavior_count if forced_stage is None else int(behavior_count)
    stage = forced_stage or (
        "A"
        if not categories
        else "B"
        if stage_behavior_count == 0
        else "C"
        if stage_behavior_count < 10
        else "D"
    )
    limit = min(max(int(limit), 1), 24)
    offset = max(0, int(offset))

    category_by_product = {}
    rows = (
        db.session.query(ProductCategory.product_id, Category.name)
        .join(Category, Category.id == ProductCategory.category_id)
        .all()
    )
    for product_id, category_name in rows:
        category_by_product.setdefault(product_id, []).append(category_name)

    popularity = recent_behavior_counts()
    seen_ids = {row.product_id for row in history}
    products = Product.query.filter_by(status="approved").all()
    user_category_scores = Counter()
    for event in history:
        weight = BEHAVIOR_WEIGHTS.get(event.behavior_type, 0)
        if weight <= 0:
            continue
        user_category_scores.update({name: weight for name in category_by_product.get(event.product_id, [])})

    preferred = set(categories)
    scored = []
    for product in products:
        product_categories = category_by_product.get(product.id, [])
        if product.id in seen_ids:
            continue
        preference_match = sum(1 for name in product_categories if name in preferred)
        behavior_match = sum(user_category_scores[name] for name in product_categories)
        popularity_score = int(popularity.get(product.id, 0))
        ai_name = (product.ai_category or "").strip()
        ai_bonus = 0
        if ai_name and ai_name not in product_categories and (ai_name in preferred or user_category_scores.get(ai_name)):
            ai_bonus = 5

        if stage == "A":
            score = popularity_score + ai_bonus
            reason = "校园热门"
        elif stage == "B":
            if not preference_match:
                continue
            score = preference_match * 100 + popularity_score + ai_bonus
            reason = f"符合兴趣：{', '.join(name for name in product_categories if name in preferred)}"
        elif stage == "C":
            score = preference_match * 70 + behavior_match * 30 + popularity_score + ai_bonus
            reason = "兴趣偏好与近7天行为共同匹配" if behavior_match else "根据兴趣偏好推荐"
        else:
            score = behavior_match * 100 + preference_match * 10 + popularity_score + ai_bonus
            reason = "与你近7天互动过的同类商品相似" if behavior_match else "协同行为热度补充"
        if ai_bonus and preference_match:
            reason = f"{reason}，识图标签补充"

        scored.append((score, popularity_score, product.created_at, product, reason, product_categories))

    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    candidates = scored[offset : offset + limit]
    items = [
        {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "condition": product.condition,
            "image_url": product.image_url,
            "categories": product_categories,
            "behavior_count": popularity_score,
            "reason": reason,
            "recommendation_score": round(float(score), 2),
        }
        for score, popularity_score, _, product, reason, product_categories in candidates
    ]
    return {
        "items": items,
        "strategy": stage,
        "strategy_name": STAGE_LABELS[stage],
        "preferences": categories,
        "behavior_count": int(behavior_count),
        "recorded_behavior_count": actual_behavior_count,
        "behavior_window_days": 7,
        "candidate_count": len(scored),
        "offset": offset,
        "limit": limit,
        "excluded_seen_products": len(seen_ids),
        "message": f"{STAGE_LABELS[stage]}：{len(items)} 件商品，近7天行为与兴趣偏好参与排序。",
    }


@recommendation_bp.get("/recommendations")
@login_required
def get_recommendations(user):
    try:
        limit = min(max(int(request.args.get("limit", 6)), 1), 24)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return api_error("VALIDATION_ERROR", "limit 或 offset 格式错误", 422)
    categories = user.get_preferred_categories_list()
    behavior_count = len(recent_behavior_rows(user.id))
    result = _recommend(user.id, categories, behavior_count, limit, offset)
    result["behavior_count"] = behavior_count
    return api_ok(result)


@recommendation_bp.post("/recommendations/preview")
@login_required
def preview_recommendations(user):
    payload = request.get_json(silent=True) or {}
    categories = payload.get("categories", [])
    if not isinstance(categories, list):
        return api_error("VALIDATION_ERROR", "categories 必须是数组", 422)
    try:
        behavior_count = min(max(int(payload.get("behavior_count", 0)), 0), 10000)
        offset = min(max(int(payload.get("offset", 0)), 0), 100)
        limit = min(max(int(payload.get("limit", 6)), 1), 24)
    except (TypeError, ValueError):
        return api_error("VALIDATION_ERROR", "推荐参数格式错误", 422)
    forced_stage = payload.get("stage")
    if forced_stage and forced_stage not in STAGE_LABELS:
        return api_error("VALIDATION_ERROR", "stage 必须为 A、B、C 或 D", 422)
    return api_ok(_recommend(user.id, categories, behavior_count, limit, offset, forced_stage))


@recommendation_bp.get("/recommendations/similar/<int:product_id>")
def get_similar_products(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return api_error("NOT_FOUND", "商品不存在", 404)
    confirmed_names = [link.category.name for link in product.categories if link.category]
    if not confirmed_names and not product.ai_category:
        return api_ok({"product_id": product_id, "items": []})
    category_ids = [row.category_id for row in product.categories]
    primary = []
    if category_ids:
        primary = (
            Product.query.join(ProductCategory, ProductCategory.product_id == Product.id)
            .filter(ProductCategory.category_id.in_(category_ids), Product.status == "approved", Product.id != product_id)
            .limit(6)
            .all()
        )
    seen_ids = {product_id, *(item.id for item in primary)}
    supplement_tags = [name for name in confirmed_names if name]
    if product.ai_category and product.ai_category not in supplement_tags:
        supplement_tags.append(product.ai_category)
    extras = []
    if supplement_tags and len(primary) < 6:
        extras = (
            Product.query.filter(
                Product.status == "approved",
                Product.id.notin_(seen_ids),
                Product.ai_category.in_(supplement_tags),
            )
            .limit(6 - len(primary))
            .all()
        )
    items = [_similar_item(item, "同品类商品") for item in primary]
    items.extend(_similar_item(item, "识图标签补充") for item in extras)
    return api_ok({"product_id": product_id, "items": items})


def _similar_item(item: Product, reason: str) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "condition": item.condition,
        "image_url": item.image_url,
        "categories": [link.category.name for link in item.categories if link.category],
        "ai_category": item.ai_category,
        "reason": reason,
    }
