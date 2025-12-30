from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User

user_bp = Blueprint("user_bp", __name__, url_prefix="/api")


def _ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data})


def _err(message="error", code=1, http_status=400):
    return jsonify({"code": code, "message": message, "data": None}), http_status


def _create_token(user_id: int):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=current_app.config["JWT_EXPIRE_SECONDS"])).timestamp()),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=current_app.config["JWT_ALG"])
    return token


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
        return _err("username/email/password 不能为空", code=1001)

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return _err("用户名或邮箱已存在", code=1002)

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    return _ok({"user": {"id": user.id, "username": user.username, "email": user.email}}, "注册成功")


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
        return _err("identifier/password 不能为空", code=1101)

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if not user or not check_password_hash(user.password_hash, password):
        return _err("用户名/邮箱或密码错误", code=1102, http_status=401)

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    token = _create_token(user.id)
    return _ok(
        {
            "token": token,
            "remember": remember,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        },
        "登录成功",
    )


@user_bp.get("/user/profile")
def profile():
    """
    GET /api/user/profile
    课程项目：这里先返回 mock（或从 token 中解析 user_id 后查库）
    """
    # 为了便于前端联调，先给一个固定结构
    return _ok(
        {
            "id": 1,
            "username": "demo_user",
            "email": "demo@example.com",
        }
    )



