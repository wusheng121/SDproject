"""管理员路由 - 占位实现，留给组员完善"""
from flask import Blueprint, request

from auth import login_required
from utils.response import ok, err

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")


# TODO: 需要实现 RBAC 权限检查装饰器，验证用户是否有 admin 角色


@admin_bp.get("/users")
@login_required
def list_users(user):
    """
    GET /api/admin/users
    用户管理 - 查看所有用户（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 查询用户列表，支持分页和搜索
    return ok({"items": [], "total": 0, "message": "用户管理功能待实现"})


@admin_bp.post("/users/<int:user_id>/ban")
@login_required
def ban_user(user, user_id):
    """
    POST /api/admin/users/:id/ban
    封禁用户（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 封禁指定用户
    return err("封禁功能待实现", code=50001)


@admin_bp.get("/products/pending")
@login_required
def list_pending_products(user):
    """
    GET /api/admin/products/pending
    待审核商品列表（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 查询状态为 pending 的商品
    return ok({"items": [], "total": 0, "message": "商品审核列表待实现"})


@admin_bp.post("/products/<int:product_id>/approve")
@login_required
def approve_product(user, product_id):
    """
    POST /api/admin/products/:id/approve
    审核通过商品（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 将商品状态改为 approved
    return ok({"message": "审核功能待实现"})


@admin_bp.post("/products/<int:product_id>/reject")
@login_required
def reject_product(user, product_id):
    """
    POST /api/admin/products/:id/reject
    审核拒绝商品（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 将商品状态改为 rejected
    return ok({"message": "审核功能待实现"})


@admin_bp.get("/logs")
@login_required
def list_operation_logs(user):
    """
    GET /api/admin/logs
    操作日志查看（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 查询操作日志表（需要先创建日志表）
    return ok({"items": [], "total": 0, "message": "操作日志功能待实现"})


@admin_bp.get("/stats")
@login_required
def get_statistics(user):
    """
    GET /api/admin/stats
    平台统计数据（TODO: 待实现）
    """
    # TODO: 检查是否为管理员
    # TODO: 统计用户数、商品数、订单数等
    return ok({
        "total_users": 0,
        "total_products": 0,
        "pending_products": 0,
        "message": "统计功能待实现"
    })
