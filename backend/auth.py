from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request

from extensions import db
from models import ApiKey, AuthSession, Role, User, UserRole
from utils.response import api_error
from utils.security import hash_token, parse_api_key
from utils.serializers import user_permissions


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.remote_addr) or ""


def _user_agent() -> str:
    return (request.headers.get("User-Agent") or "")[:255]


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    ttl = int(current_app.config["JWT_ACCESS_TTL_SECONDS"])
    payload = {
        "sub": str(user.id),
        "type": "access",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "iss": current_app.config["JWT_ISSUER"],
        "aud": current_app.config["JWT_AUDIENCE"],
        "user_type": user.user_type,
    }
    headers = {"kid": current_app.config.get("JWT_KEY_ID", "v1")}
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALG"],
        headers=headers,
    )


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALG"]],
            audience=current_app.config["JWT_AUDIENCE"],
            issuer=current_app.config["JWT_ISSUER"],
        )
    except jwt.PyJWTError:
        return None


def _bearer_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


def current_user() -> User | None:
    token = _bearer_token()
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    user = db.session.get(User, user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        return None
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return api_error("AUTH_REQUIRED", "未登录或会话已过期", 401)
        return fn(user, *args, **kwargs)

    return wrapper


def _has_permission(user: User, permission: str) -> bool:
    return permission in user_permissions(user)


def permission_required(*permissions: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return api_error("AUTH_REQUIRED", "未登录或会话已过期", 401)
            if not all(_has_permission(user, p) for p in permissions):
                return api_error("AUTH_FORBIDDEN", "没有执行该操作的权限", 403)
            return fn(user, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(fn):
    return permission_required("user:manage")(fn)


def create_session(user: User, remember: bool = False) -> tuple[str, AuthSession]:
    raw = secrets.token_urlsafe(32)
    ttl = int(current_app.config["JWT_REFRESH_TTL_SECONDS"])
    if remember:
        ttl = max(ttl, 30 * 24 * 3600)
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_token(raw),
        family_id=secrets.token_hex(16),
        expires_at=_now() + timedelta(seconds=ttl),
        ip=_client_ip(),
        user_agent=_user_agent(),
    )
    db.session.add(session)
    return raw, session


def rotate_session(raw_token: str) -> tuple[str, AuthSession] | None:
    token_hash = hash_token(raw_token or "")
    session = AuthSession.query.filter_by(refresh_token_hash=token_hash).with_for_update().first()
    if not session:
        return None
    if session.revoked_at is not None:
        AuthSession.query.filter_by(family_id=session.family_id, revoked_at=None).update(
            {"revoked_at": _now()}, synchronize_session=False
        )
        db.session.commit()
        return None
    if session.expires_at <= _now():
        session.revoked_at = _now()
        db.session.commit()
        return None
    user = db.session.get(User, session.user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        return None
    session.revoked_at = _now()
    session.last_used_at = _now()
    raw, new_session = create_session(user)
    new_session.family_id = session.family_id
    return raw, new_session


def revoke_session(raw_token: str) -> None:
    session = AuthSession.query.filter_by(refresh_token_hash=hash_token(raw_token or "")).first()
    if session and session.revoked_at is None:
        session.revoked_at = _now()


def revoke_all_sessions(user_id: int) -> int:
    return AuthSession.query.filter_by(user_id=user_id, revoked_at=None).update(
        {"revoked_at": _now()}, synchronize_session=False
    )


def set_refresh_cookie(response, token: str):
    response.set_cookie(
        current_app.config["REFRESH_COOKIE_NAME"],
        token,
        max_age=int(current_app.config["JWT_REFRESH_TTL_SECONDS"]),
        httponly=True,
        secure=bool(current_app.config["REFRESH_COOKIE_SECURE"]),
        samesite=current_app.config["REFRESH_COOKIE_SAMESITE"],
        path=current_app.config["REFRESH_COOKIE_PATH"],
    )
    return response


def clear_refresh_cookie(response):
    response.delete_cookie(
        current_app.config["REFRESH_COOKIE_NAME"],
        path=current_app.config["REFRESH_COOKIE_PATH"],
    )
    return response


def validate_refresh_origin() -> bool:
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return True
    allowed = set(current_app.config.get("CORS_ORIGINS", []))
    allowed.add(current_app.config.get("FRONTEND_URL", ""))
    return any(origin == item or origin.startswith(item.rstrip("/") + "/") for item in allowed if item)


def record_login_failure(user: User | None) -> None:
    if not user:
        return
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= 5:
        user.locked_until = _now() + timedelta(minutes=15)
    db.session.commit()


def reset_login_failures(user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _now()


def user_is_locked(user: User) -> bool:
    return bool(user.locked_until and user.locked_until > _now())


def assign_role(user: User, role_name: str) -> None:
    role = Role.query.filter_by(name=role_name).first()
    if role and not UserRole.query.filter_by(user_id=user.id, role_id=role.id).first():
        db.session.add(UserRole(user_id=user.id, role_id=role.id))


def api_key_user(required_scope: str | None = None) -> User | None:
    value = request.headers.get("X-API-Key", "")
    parsed = parse_api_key(value)
    if not parsed:
        return None
    prefix, full = parsed
    key = ApiKey.query.filter_by(key_prefix=prefix).first()
    if not key or key.revoked_at is not None:
        return None
    if not hmac.compare_digest(key.key_hash, hash_token(full)):
        return None
    now = _now()
    if key.expires_at and key.expires_at <= now:
        return None
    user = db.session.get(User, key.user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        return None
    if required_scope and required_scope not in key.scope_set():
        return None
    key.last_used_at = now
    db.session.commit()
    g.api_key = key
    return user


def api_key_required(required_scope: str | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = api_key_user(required_scope)
            if not user:
                return api_error("AUTH_INVALID_API_KEY", "API Key 无效或权限不足", 401)
            return fn(user, *args, **kwargs)

        return wrapper

    return decorator
