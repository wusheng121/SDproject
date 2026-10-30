"""商品相关路由 - 从 movie_routes.py 改造而来"""
from flask import Blueprint, request
from sqlalchemy import func, or_

from auth import current_user, login_required
from extensions import db
from models import Category, Product, ProductCategory, UserBehavior
from services.listing_vision import ListingVisionError, recognize_listing
from services.market_signals import price_reference as deal_price_reference
from utils.response import err, ok

CONDITION_RANKS = {
    "七成新": 70,
    "八成新": 80,
    "九成新": 90,
    "九五新": 95,
    "全新": 100,
}


def _condition_rank(value):
    return CONDITION_RANKS.get(value, 0)


def _condition_filter(query, minimum):
    if minimum not in CONDITION_RANKS:
        return query
    return query.filter(
        or_(*[
            Product.condition == condition
            for condition, rank in CONDITION_RANKS.items()
            if rank >= CONDITION_RANKS[minimum]
        ])
    )

product_bp = Blueprint("product_bp", __name__, url_prefix="/api")


@product_bp.get("/products")
def list_products():
    """
    GET /api/products
    query: page, page_size, category, condition, sort, min_price, max_price
    """
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 12))
    category = request.args.get("category")
    condition = request.args.get("condition")
    min_condition = request.args.get("min_condition")
    sort = request.args.get("sort", "hot")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    page = max(1, page)
    page_size = min(max(1, page_size), 50)

    # 聚合用户行为（收藏、评价）作为热度指标
    behavior_agg = (
        db.session.query(
            UserBehavior.product_id.label("product_id"),
            func.count(UserBehavior.id).label("behavior_count"),
        )
        .filter(UserBehavior.behavior_type.in_(["favorite", "review"]))
        .group_by(UserBehavior.product_id)
        .subquery()
    )

    q = db.session.query(Product, behavior_agg.c.behavior_count).outerjoin(
        behavior_agg, behavior_agg.c.product_id == Product.id
    )

    # 只显示已审核通过的商品
    q = q.filter(Product.status == "approved")

    q_text = (request.args.get("q") or request.args.get("keyword") or "").strip()
    min_condition = request.args.get("min_condition")
    if q_text:
        q = q.filter(Product.name.ilike(f"%{q_text}%"))

    # 筛选条件
    if category:
        q = q.join(ProductCategory, ProductCategory.product_id == Product.id).join(
            Category, Category.id == ProductCategory.category_id
        ).filter(Category.name == category)

    if condition:
        q = q.filter(Product.condition == condition)
    if min_condition:
        q = _condition_filter(q, min_condition)

    if min_price:
        try:
            q = q.filter(Product.price >= float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            q = q.filter(Product.price <= float(max_price))
        except ValueError:
            pass

    # 排序
    if sort == "new":
        q = q.order_by(Product.created_at.desc())
    elif sort == "price_asc":
        q = q.order_by(Product.price.asc())
    elif sort == "price_desc":
        q = q.order_by(Product.price.desc())
    else:  # hot
        q = q.order_by(
            func.coalesce(behavior_agg.c.behavior_count, 0).desc(),
            Product.created_at.desc()
        )

    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    # 批量获取品类
    product_ids = [r[0].id for r in rows]
    category_map = {pid: [] for pid in product_ids}
    if product_ids:
        cats = (
            db.session.query(ProductCategory.product_id, Category.name)
            .join(Category, Category.id == ProductCategory.category_id)
            .filter(ProductCategory.product_id.in_(product_ids))
            .all()
        )
        for pid, cname in cats:
            category_map.setdefault(pid, []).append(cname)

    items = []
    for p, behavior_count in rows:
        items.append(
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "condition": p.condition,
                "brand": p.brand,
                "has_notes": p.has_notes,
                "defect_description": p.defect_description,
                "trade_method": p.trade_method,
                "trade_location": p.trade_location,
                "image_url": p.image_url,
                "categories": category_map.get(p.id, []),
                "behavior_count": int(behavior_count or 0),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    return ok(
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "filters": {
                "category": category,
                "condition": condition,
                "min_condition": min_condition,
                "sort": sort,
                "min_price": min_price,
                "max_price": max_price,
            },
            "items": items,
        }
    )


@product_bp.get("/products/<int:product_id>")
def product_detail(product_id: int):
    """
    GET /api/products/:id
    """
    p = Product.query.get(product_id)
    if not p:
        return err("商品不存在", code=40401, http_status=404)

    # 获取品类
    categories = (
        db.session.query(Category.name)
        .join(ProductCategory, ProductCategory.category_id == Category.id)
        .filter(ProductCategory.product_id == product_id)
        .all()
    )

    # 获取卖家信息
    seller = p.seller
    seller_info = {
        "id": seller.id,
        "username": seller.username,
    } if seller else None

    # 如果用户已登录，返回是否收藏
    user = current_user()
    is_favorited = None
    if user:
        is_favorited = UserBehavior.query.filter_by(
            user_id=user.id, product_id=p.id, behavior_type="favorite"
        ).first() is not None

    return ok(
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "condition": p.condition,
            "brand": p.brand,
            "has_notes": p.has_notes,
            "defect_description": p.defect_description,
            "trade_method": p.trade_method,
            "trade_location": p.trade_location,
            "image_url": p.image_url,
            "status": p.status,
            "categories": [x[0] for x in categories],
            "seller": seller_info,
            "is_favorited": is_favorited,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
    )


@product_bp.get("/products/search")
def search_products():
    """
    GET /api/products/search
    query: q, category, min_price, max_price
    """
    q_text = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    min_condition = (request.args.get("min_condition") or "").strip()
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    sort = request.args.get("sort", "new")
    if not q_text and not category:
        return ok({"items": [], "total": 0})

    q = db.session.query(Product).filter(Product.status == "approved")

    if q_text:
        q = q.filter(Product.name.ilike(f"%{q_text}%"))

    # 品类筛选
    if category:
        q = q.join(ProductCategory, ProductCategory.product_id == Product.id).join(
            Category, Category.id == ProductCategory.category_id
        ).filter(Category.name.ilike(f"%{category}%"))
    if min_condition:
        q = _condition_filter(q, min_condition)
    if min_price:
        try:
            q = q.filter(Product.price >= float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            q = q.filter(Product.price <= float(max_price))
        except ValueError:
            pass

    total = q.distinct().count()
    if sort == "price_asc":
        q = q.order_by(Product.price.asc())
    elif sort == "price_desc":
        q = q.order_by(Product.price.desc())
    elif sort == "hot":
        q = q.outerjoin(UserBehavior, UserBehavior.product_id == Product.id).group_by(Product.id).order_by(
            func.count(UserBehavior.id).desc(), Product.created_at.desc()
        )
    else:
        q = q.order_by(Product.created_at.desc())
    q = q.distinct().limit(50)

    items = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "condition": p.condition,
            "brand": p.brand,
            "has_notes": p.has_notes,
            "defect_description": p.defect_description,
            "trade_method": p.trade_method,
            "trade_location": p.trade_location,
            "image_url": p.image_url,
        }
        for p in q.all()
    ]
    return ok({"items": items, "total": total})


@product_bp.get("/categories")
def list_categories():
    """
    GET /api/categories
    返回所有品类名称列表
    """
    names = [c.name for c in Category.query.order_by(Category.name.asc()).all()]
    return ok({"items": names})




@product_bp.post("/ai/recognize")
def recognize_product_image():
    if not request.files.get("image"):
        return err("请先选择一张商品图片", code=40001, http_status=400)
    result = {
        "name": "二手商品",
        "brand": "",
        "category": "数码产品",
        "condition": "九成新",
        "keywords": ["数码产品"],
    }
    return ok({"recognition": result, "mock": True})


@product_bp.post("/ai/listing-recognize")
@login_required
def recognize_listing_image(user):
    """识图发单。失败时不返回猜测结果，发布页保持空白。"""
    image = request.files.get("image")
    if image is None:
        return err("请先选择一张商品图片", code=40001, http_status=400)
    try:
        result = recognize_listing(image.read(4 * 1024 * 1024 + 1), image.mimetype or "")
    except ListingVisionError as exc:
        return ok({"recognition": None, "message": str(exc)})
    return ok({"recognition": result})


@product_bp.get("/products/price-reference")
def price_reference():
    category_name = (request.args.get("category") or "").strip()
    if not category_name:
        return err("请选择品类", code=40001, http_status=400)
    if not Category.query.filter_by(name=category_name).first():
        return err("商品品类不存在", code=40001, http_status=400)
    return ok(deal_price_reference(category_name))


def _optional_text(data, key, max_length):
    value = data.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value[:max_length] or None


@product_bp.post("/products")
@login_required
def publish_product(user):
    data = request.get_json(silent=True) or {}
    name = _optional_text(data, "name", 200)
    condition = _optional_text(data, "condition", 20)
    category_name = _optional_text(data, "category", 50)
    try:
        price = float(data.get("price"))
    except (TypeError, ValueError):
        price = 0
    if not name or not category_name or condition not in CONDITION_RANKS or price <= 0:
        return err("请填写商品名称、品类、有效价格和成色", code=40001, http_status=400)

    category = Category.query.filter_by(name=category_name).first()
    if not category:
        return err("商品品类不存在", code=40001, http_status=400)

    ai_category = _optional_text(data, "ai_category", 50)
    ai_condition = _optional_text(data, "ai_condition", 20)
    if ai_category and not Category.query.filter_by(name=ai_category).first():
        ai_category = None
    if ai_condition not in CONDITION_RANKS:
        ai_condition = None

    product = Product(
        name=name,
        description=_optional_text(data, "description", 4000),
        price=price,
        condition=condition,
        brand=_optional_text(data, "brand", 100),
        has_notes=bool(data.get("has_notes", False)),
        defect_description=_optional_text(data, "defect_description", 500),
        trade_method=_optional_text(data, "trade_method", 30),
        trade_location=_optional_text(data, "trade_location", 200),
        image_url=_optional_text(data, "image_url", 500),
        ai_category=ai_category,
        ai_condition=ai_condition,
        status="pending",
        seller_id=user.id,
    )
    product.categories.append(ProductCategory(category=category))
    db.session.add(product)
    db.session.commit()
    return ok({"id": product.id, "status": product.status}, message="商品已提交审核")
