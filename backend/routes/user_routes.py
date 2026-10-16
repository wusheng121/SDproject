from datetime import datetime

from flask import Blueprint, request
from werkzeug.security import check_password_hash, generate_password_hash

from auth import create_token, login_required
from extensions import db
from models import User
from utils.response import err, ok

user_bp = Blueprint("user_bp", __name__, url_prefix="/api")


@user_bp.post("/register")
def register():
    """
    POST /api/register
    body: { username, email, password }
    """
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not username or not email or not password:
        return err("username/email/password 不能为空", code=1001)

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return err("用户名或邮箱已存在", code=1002)

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    return ok({"user": {"id": user.id, "username": user.username, "email": user.email}}, "注册成功")


@user_bp.post("/login")
def login():
    """
    POST /api/login
    body: { identifier: username_or_email, password }
    """
    payload = request.get_json(silent=True) or {}
    identifier = (payload.get("identifier") or "").strip()
    password = payload.get("password") or ""
    remember = bool(payload.get("remember", False))

    if not identifier or not password:
        return err("identifier/password 不能为空", code=1101)

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if not user or not check_password_hash(user.password_hash, password):
        return err("用户名/邮箱或密码错误", code=1102, http_status=401)

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    token = create_token(user.id, remember=remember)
    return ok(
        {
            "token": token,
            "remember": remember,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        },
        "登录成功",
    )


@user_bp.get("/user/profile")
@login_required
def profile(user: User):
    """
    GET /api/user/profile
    """
    return ok(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )


@user_bp.get("/user/favorites")
@login_required
def list_favorites(user: User):
    """
    GET /api/user/favorites
    返回当前用户的收藏商品（已迁移到 /api/favorites，此接口保留兼容）
    TODO: 前端改用 /api/favorites 后可删除
    """
    return ok({"items": [], "message": "请使用 /api/favorites 接口"})


@user_bp.get("/user/ratings")
@login_required
def list_my_ratings(user: User):
    """
    GET /api/user/ratings
    返回当前用户的评价列表（已迁移到 /api/my-reviews）
    TODO: 前端改用 /api/my-reviews 后可删除
    """
    return ok({"items": [], "message": "请使用 /api/my-reviews 接口"})


@user_bp.get("/user/preferences")
@login_required
def get_preferences(user: User):
    """
    GET /api/user/preferences
    获取用户的兴趣标签（品类偏好）
    """
    categories = user.get_preferred_categories_list()
    # has_preference: True 表示用户已经操作过（选择了品类或主动跳过）
    # NULL = 从未设置, "" = 主动跳过, "xxx,yyy" = 已选择
    has_preference = user.preferred_categories is not None
    return ok({"preferred_categories": categories, "has_preference": has_preference})


@user_bp.post("/user/preferences")
@login_required
def save_preferences(user: User):
    """
    POST /api/user/preferences
    保存/更新用户的兴趣标签
    body: { categories: ["保温杯", "运动鞋", ...] }
    """
    payload = request.get_json(silent=True) or {}
    categories = payload.get("categories") or []

    if not isinstance(categories, list):
        return err("categories 必须是数组", code=1201)

    # 允许用户清空偏好（传空数组）或设置偏好
    user.set_preferred_categories_list(categories)
    db.session.commit()

    return ok({"preferred_categories": user.get_preferred_categories_list()}, "偏好已保存")




