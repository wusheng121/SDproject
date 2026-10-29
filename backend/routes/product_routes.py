"""商品相关路由 - 从 movie_routes.py 改造而来"""
from flask import Blueprint, request
from sqlalchemy import func

from auth import current_user, login_required
from extensions import db
from models import Category, Product, ProductCategory, UserBehavior
from utils.response import err, ok

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
    if q_text:
        q = q.filter(Product.name.ilike(f"%{q_text}%"))

    # 筛选条件
    if category:
        q = q.join(ProductCategory, ProductCategory.product_id == Product.id).join(
            Category, Category.id == ProductCategory.category_id
        ).filter(Category.name == category)

    if condition:
        q = q.filter(Product.condition == condition)

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
    
    if not q_text and not category:
        return ok({"items": []})

    q = db.session.query(Product).filter(Product.status == "approved")

    # 商品名称模糊搜索
    if q_text:
        q = q.filter(Product.name.ilike(f"%{q_text}%"))

    # 品类筛选
    if category:
        q = q.join(ProductCategory, ProductCategory.product_id == Product.id).join(
            Category, Category.id == ProductCategory.category_id
        ).filter(Category.name.ilike(f"%{category}%"))

    q = q.distinct().order_by(Product.created_at.desc()).limit(50)

    items = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "condition": p.condition,
            "image_url": p.image_url,
        }
        for p in q.all()
    ]
    
    return ok({"items": items})


@product_bp.get("/categories")
def list_categories():
    """
    GET /api/categories
    返回所有品类名称列表
    """
    names = [c.name for c in Category.query.order_by(Category.name.asc()).all()]
    return ok({"items": names})


# TODO: 商品发布、编辑、删除接口留给组员实现
@product_bp.post("/products")
@login_required
def publish_product(user):
    """
    POST /api/products
    发布商品（TODO: 待完善）
    """
    return err("商品发布功能待实现", code=50001)
