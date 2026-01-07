from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, request

from models import User
from utils.response import err


def create_token(user_id: int, remember: bool = False) -> str:
    now = datetime.now(timezone.utc)
    expire_seconds = int(current_app.config["JWT_EXPIRE_SECONDS"])
    if remember:
        # “记住我”：默认延长到 30 天（课程项目常用做法）
        expire_seconds = max(expire_seconds, 30 * 24 * 3600)

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expire_seconds)).timestamp()),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=current_app.config["JWT_ALG"])


def _get_bearer_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0].strip(), parts[1].strip()
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def current_user() -> User | None:
    token = _get_bearer_token()
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALG"]],
        )
        user_id = int(payload.get("sub"))
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None

    return User.query.get(user_id)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return err("未登录或 token 已过期", code=40101, http_status=401)
        return fn(user, *args, **kwargs)

    return wrapper
















