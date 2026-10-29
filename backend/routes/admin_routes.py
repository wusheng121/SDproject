from datetime import datetime

from flask import Blueprint, request
from sqlalchemy import or_

from auth import permission_required, revoke_all_sessions
from extensions import db
from models import ApiKey, OperationLog, Order, Product, Role, User, UserBehavior, UserRole
from utils.audit import log_operation
from utils.response import api_error, api_ok
from utils.serializers import (
    operation_log_public,
    pagination,
    product_public,
    user_public,
)

admin_bp = Blueprint("admin_bp_v1", __name__, url_prefix="/api/v1/admin")


def _page_args():
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(max(1, int(request.args.get("page_size", 20))), 100)
    except ValueError:
        page, page_size = 1, 20
    return page, page_size


def _sync_user_type(user: User):
    names = {ur.role.name for ur in user.user_roles if ur.role}
    if "admin" in names:
        user.user_type = "admin"
    elif "agent_service" in names:
        user.user_type = "agent_service"
    else:
        user.user_type = "normal_user"


@admin_bp.get("/users")
@permission_required("user:manage")
def list_users(admin):
    page, page_size = _page_args()
    q = User.query
    keyword = (request.args.get("keyword") or "").strip()
    if keyword:
        q = q.filter(or_(User.username.ilike(f"%{keyword}%"), User.email.ilike(f"%{keyword}%")))
    role_name = (request.args.get("role") or "").strip()
    if role_name:
        q = q.join(UserRole, UserRole.user_id == User.id).join(
            Role, Role.id == UserRole.role_id
        ).filter(Role.name == role_name)
    status = (request.args.get("status") or "").strip()
    if status == "active":
        q = q.filter(User.is_active.is_(True))
    elif status == "banned":
        q = q.filter(User.is_active.is_(False))
    total = q.count()
    users = q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return api_ok(
        [user_public(user, include_permissions=True) for user in users],
        pagination=pagination(page, page_size, total),
    )


@admin_bp.get("/users/<int:user_id>")
@permission_required("user:manage")
def get_user(admin, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return api_error("NOT_FOUND", "用户不存在", 404)
    return api_ok({"user": user_public(user, include_permissions=True)})


@admin_bp.post("/users/<int:user_id>/ban")
@permission_required("user:manage")
def ban_user(admin, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return api_error("NOT_FOUND", "用户不存在", 404)
    if user.id == admin.id:
        return api_error("VALIDATION_ERROR", "不能封禁自己", 409)
    before = user_public(user)
    user.is_active = False
    revoke_all_sessions(user.id)
    ApiKey.query.filter_by(user_id=user.id, revoked_at=None).update(
        {"revoked_at": datetime.utcnow()}, synchronize_session=False
    )
    log_operation(
        admin,
        "user.ban",
        "user",
        user.id,
        before=before,
        after={"is_active": False, "reason": (request.get_json(silent=True) or {}).get("reason")},
    )
    db.session.commit()
    return api_ok({"user": user_public(user, include_permissions=True)})


@admin_bp.post("/users/<int:user_id>/unban")
@permission_required("user:manage")
def unban_user(admin, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return api_error("NOT_FOUND", "用户不存在", 404)
    before = user_public(user)
    user.is_active = True
    user.failed_login_count = 0
    user.locked_until = None
    log_operation(admin, "user.unban", "user", user.id, before=before, after={"is_active": True})
    db.session.commit()
    return api_ok({"user": user_public(user, include_permissions=True)})


@admin_bp.put("/users/<int:user_id>/roles")
@permission_required("user:manage")
def set_roles(admin, user_id):
    user = db.session.get(User, user_id)
    if not user:
        return api_error("NOT_FOUND", "用户不存在", 404)
    payload = request.get_json(silent=True) or {}
    names = payload.get("roles")
    if not isinstance(names, list) or not names:
        return api_error("VALIDATION_ERROR", "roles 必须是非空数组", 422)
    roles = Role.query.filter(Role.name.in_(names)).all()
    if len(roles) != len(set(names)):
        return api_error("VALIDATION_ERROR", "包含不存在的角色", 422)
    before = user_public(user)
    UserRole.query.filter_by(user_id=user.id).delete()
    for role in roles:
        db.session.add(UserRole(user_id=user.id, role_id=role.id))
    db.session.flush()
    db.session.refresh(user)
    _sync_user_type(user)
    log_operation(
        admin,
        "user.roles.update",
        "user",
        user.id,
        before=before.get("roles"),
        after=names,
    )
    db.session.commit()
    return api_ok({"user": user_public(user, include_permissions=True)})


@admin_bp.get("/products")
@permission_required("product:audit")
def list_products(admin):
    page, page_size = _page_args()
    q = Product.query
    status = (request.args.get("status") or "").strip()
    if status:
        q = q.filter(Product.status == status)
    total = q.count()
    products = (
        q.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return api_ok(
        [product_public(product, include_description=True) for product in products],
        pagination=pagination(page, page_size, total),
    )


def _change_product_status(admin, product_id, action, new_status, reason=None):
    product = db.session.get(Product, product_id)
    if not product:
        return api_error("NOT_FOUND", "商品不存在", 404)
    allowed = {
        "approve": {"pending", "rejected"},
        "reject": {"pending", "approved"},
        "offline": {"approved"},
    }[action]
    if product.status not in allowed:
        return api_error("CONFLICT", f"当前状态 {product.status} 不允许该操作", 409)
    before = product_public(product, include_description=True)
    product.status = new_status
    log_operation(
        admin,
        f"product.{action}",
        "product",
        product.id,
        before=before,
        after={"status": new_status, "reason": reason},
    )
    db.session.commit()
    return api_ok({"product": product_public(product, include_description=True)})


@admin_bp.post("/products/<int:product_id>/approve")
@permission_required("product:audit")
def approve_product(admin, product_id):
    return _change_product_status(admin, product_id, "approve", "approved")


@admin_bp.post("/products/<int:product_id>/reject")
@permission_required("product:audit")
def reject_product(admin, product_id):
    reason = (request.get_json(silent=True) or {}).get("reason")
    if not reason:
        return api_error("VALIDATION_ERROR", "拒绝原因不能为空", 422)
    return _change_product_status(admin, product_id, "reject", "rejected", reason=reason)


@admin_bp.post("/products/<int:product_id>/offline")
@permission_required("product:audit")
def offline_product(admin, product_id):
    reason = (request.get_json(silent=True) or {}).get("reason")
    return _change_product_status(admin, product_id, "offline", "offline", reason=reason)


@admin_bp.get("/operation-logs")
@permission_required("admin:log")
def list_logs(admin):
    page, page_size = _page_args()
    q = OperationLog.query
    action = (request.args.get("action") or "").strip()
    if action:
        q = q.filter(OperationLog.action == action)
    resource_type = (request.args.get("resource_type") or "").strip()
    if resource_type:
        q = q.filter(OperationLog.resource_type == resource_type)
    actor_id = request.args.get("actor_id")
    if actor_id:
        q = q.filter(OperationLog.actor_id == int(actor_id))
    total = q.count()
    logs = (
        q.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return api_ok(
        [operation_log_public(log) for log in logs],
        pagination=pagination(page, page_size, total),
    )


@admin_bp.get("/stats")
@permission_required("admin:log")
def get_stats(admin):
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_products = Product.query.count()
    pending_products = Product.query.filter_by(status="pending").count()
    approved_products = Product.query.filter_by(status="approved").count()
    total_behaviors = UserBehavior.query.count()
    total_orders = Order.query.count()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return api_ok(
        {
            "users": {"total": total_users, "active": active_users},
            "products": {
                "total": total_products,
                "pending": pending_products,
                "approved": approved_products,
            },
            "behaviors": total_behaviors,
            "orders": total_orders,
            "today": {
                "users": User.query.filter(User.created_at >= today).count(),
                "products": Product.query.filter(Product.created_at >= today).count(),
                "behaviors": UserBehavior.query.filter(UserBehavior.created_at >= today).count(),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
    )
