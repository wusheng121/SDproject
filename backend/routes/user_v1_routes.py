from datetime import datetime, timedelta

from flask import Blueprint, request

from auth import login_required
from extensions import db
from models import ApiKey, EmailVerificationToken, Product, User, UserBehavior
from utils.mail import send_verification_email
from utils.response import api_error, api_ok
from utils.security import (
    encrypt_phone,
    generate_api_key,
    hash_phone,
    hash_token,
    normalize_email,
    opaque_token,
)
from utils.serializers import user_public
from utils.validators import valid_email, valid_phone

user_v1_bp = Blueprint("user_v1_bp", __name__, url_prefix="/api/v1/users")


@user_v1_bp.get("/me")
@login_required
def get_me(user):
    return api_ok({"user": user_public(user, include_permissions=True)})


@user_v1_bp.patch("/me")
@login_required
def update_me(user):
    payload = request.get_json(silent=True) or {}

    if "username" in payload:
        username = (payload.get("username") or "").strip()
        if not 3 <= len(username) <= 50:
            return api_error("VALIDATION_ERROR", "用户名长度必须为 3-50 位", 422)
        exists = db.session.query(User).filter(
            User.username == username, User.id != user.id
        ).first()
        if exists:
            return api_error("AUTH_USERNAME_EXISTS", "用户名已存在", 409)
        user.username = username

    if "email" in payload:
        email = normalize_email(payload.get("email") or "")
        normalized = valid_email(email)
        if not normalized:
            return api_error("VALIDATION_ERROR", "邮箱格式不正确", 422)
        exists = db.session.query(User).filter(
            User.email_normalized == normalized, User.id != user.id
        ).first()
        if exists:
            return api_error("AUTH_EMAIL_EXISTS", "邮箱已存在", 409)
        if normalized != user.email_normalized:
            user.email = normalized
            user.email_normalized = normalized
            user.email_verified_at = None
            raw_token = opaque_token()
            db.session.add(
                EmailVerificationToken(
                    user_id=user.id,
                    token_hash=hash_token(raw_token),
                    expires_at=datetime.utcnow() + timedelta(hours=24),
                )
            )
            db.session.flush()
            send_verification_email(normalized, raw_token)

    if "phone" in payload:
        raw_phone = payload.get("phone")
        phone = valid_phone(raw_phone) if raw_phone else None
        if raw_phone and not phone:
            return api_error("VALIDATION_ERROR", "手机号格式不正确", 422)
        phone_digest = hash_phone(phone)
        if phone_digest:
            exists = db.session.query(User).filter(
                User.phone_hash == phone_digest, User.id != user.id
            ).first()
            if exists:
                return api_error("AUTH_PHONE_EXISTS", "手机号已被使用", 409)
        user.phone_ciphertext = encrypt_phone(phone)
        user.phone_hash = phone_digest

    user.version = (user.version or 0) + 1
    db.session.commit()
    return api_ok({"user": user_public(user, include_permissions=True)})


@user_v1_bp.get("/me/preferences")
@login_required
def get_preferences(user):
    categories = user.get_preferred_categories_list()
    return api_ok(
        {
            "preferred_categories": categories,
            "has_preference": user.preferred_categories is not None,
        }
    )


@user_v1_bp.put("/me/preferences")
@login_required
def save_preferences(user):
    categories = (request.get_json(silent=True) or {}).get("categories")
    if not isinstance(categories, list):
        return api_error("VALIDATION_ERROR", "categories 必须是数组", 422)
    user.set_preferred_categories_list([str(item) for item in categories])
    db.session.commit()
    return api_ok({"preferred_categories": user.get_preferred_categories_list()})


@user_v1_bp.get("/me/stats")
@login_required
def stats(user):
    favorites = UserBehavior.query.filter_by(user_id=user.id, behavior_type="favorite").count()
    behaviors = UserBehavior.query.filter_by(user_id=user.id).count()
    products = Product.query.filter_by(seller_id=user.id).count()
    return api_ok(
        {
            "favorites": favorites,
            "behaviors": behaviors,
            "products": products,
            "categories": len(user.get_preferred_categories_list()),
        }
    )


@user_v1_bp.get("/me/api-keys")
@login_required
def list_api_keys(user):
    keys = ApiKey.query.filter_by(user_id=user.id, revoked_at=None).order_by(ApiKey.id.desc()).all()
    return api_ok(
        {
            "items": [
                {
                    "id": key.id,
                    "name": key.name,
                    "prefix": key.key_prefix,
                    "scopes": sorted(key.scope_set()),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                }
                for key in keys
            ]
        }
    )


@user_v1_bp.post("/me/api-keys")
@login_required
def create_api_key(user):
    if user.user_type not in {"agent_service", "admin"}:
        return api_error("AUTH_FORBIDDEN", "只有服务账号可以创建 API Key", 403)
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "default").strip()[:100]
    scopes = payload.get("scopes") or ["product:view", "recommendation:query"]
    if not isinstance(scopes, list):
        return api_error("VALIDATION_ERROR", "scopes 必须是数组", 422)
    allowed = {"product:view", "recommendation:query"}
    if any(scope not in allowed for scope in scopes):
        return api_error("VALIDATION_ERROR", "包含不支持的 scope", 422)
    full, prefix, digest = generate_api_key()
    key = ApiKey(
        user_id=user.id,
        name=name,
        key_prefix=prefix,
        key_hash=digest,
        scopes=",".join(scopes),
    )
    db.session.add(key)
    db.session.commit()
    return api_ok({"id": key.id, "api_key": full, "prefix": prefix, "scopes": scopes}, status=201)


@user_v1_bp.delete("/me/api-keys/<int:key_id>")
@login_required
def revoke_api_key(user, key_id):
    key = ApiKey.query.filter_by(id=key_id, user_id=user.id).first()
    if not key:
        return api_error("NOT_FOUND", "API Key 不存在", 404)
    key.revoked_at = datetime.utcnow()
    db.session.commit()
    return api_ok({"revoked": True})
