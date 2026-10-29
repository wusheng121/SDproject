from flask import Blueprint, request

from auth import api_key_required
from extensions import db
from models import Product
from utils.audit import log_operation
from utils.response import api_ok
from utils.serializers import pagination, product_public

agent_bp = Blueprint("agent_bp", __name__, url_prefix="/api/v1/agent")


@agent_bp.get("/products")
@api_key_required("product:view")
def agent_products(service_user):
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
    except ValueError:
        page, page_size = 1, 20
    q = Product.query.filter_by(status="approved")
    total = q.count()
    products = (
        q.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    log_operation(
        service_user,
        "agent.products.query",
        "product",
        after={"page": page, "page_size": page_size, "total": total},
    )
    db.session.commit()
    return api_ok(
        [product_public(product) for product in products],
        pagination=pagination(page, page_size, total),
    )


@agent_bp.get("/recommendations")
@api_key_required("recommendation:query")
def agent_recommendations(service_user):
    # The recommendation owner can replace this with the real strategy implementation.
    log_operation(service_user, "agent.recommendations.query", "recommendation")
    db.session.commit()
    return api_ok({"items": [], "strategy": "not_configured"})
