from datetime import datetime, timedelta

from flask import Blueprint, current_app, request

from auth import (
    assign_role,
    clear_refresh_cookie,
    create_access_token,
    create_session,
    login_required,
    record_login_failure,
    reset_login_failures,
    revoke_all_sessions,
    revoke_session,
    rotate_session,
    set_refresh_cookie,
    user_is_locked,
    validate_refresh_origin,
)
from extensions import db, limiter
from models import EmailVerificationToken, PasswordResetToken, User
from utils.mail import send_password_reset_email, send_verification_email
from utils.response import api_error, api_ok
from utils.security import (
    encrypt_phone,
    hash_password,
    hash_phone,
    hash_token,
    normalize_email,
    opaque_token,
    verify_password,
)
from utils.serializers import user_public
from utils.validators import password_errors, valid_email, valid_phone

auth_bp = Blueprint("auth_bp_v1", __name__, url_prefix="/api/v1/auth")


def _json():
    return request.get_json(silent=True) or {}


def _issue_session_response(user, remember=False, status=200):
    access = create_access_token(user)
    refresh, _ = create_session(user, remember=remember)
    db.session.commit()
    response, status_code = api_ok(
        {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": int(current_app.config["JWT_ACCESS_TTL_SECONDS"]),
            "user": user_public(user, include_permissions=True),
        },
        status=status,
    )
    set_refresh_cookie(response, refresh)
    return response, status_code


def _token_row(model, raw: str):
    return model.query.filter_by(token_hash=hash_token(raw), used_at=None).first()


@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    payload = _json()
    username = (payload.get("username") or "").strip()
    email = normalize_email(payload.get("email") or "")
    password = payload.get("password") or ""
    phone = valid_phone(payload.get("phone"))

    if not 3 <= len(username) <= 50:
        return api_error("VALIDATION_ERROR", "用户名长度必须为 3-50 位", 422)
    normalized_email = valid_email(email)
    if not normalized_email:
        return api_error("VALIDATION_ERROR", "邮箱格式不正确", 422)
    errors = password_errors(password)
    if errors:
        return api_error("VALIDATION_ERROR", "密码不符合要求", 422, errors)
    if payload.get("phone") and not phone:
        return api_error("VALIDATION_ERROR", "手机号格式不正确", 422)

    if User.query.filter(
        db.or_(User.username == username, User.email_normalized == normalized_email)
    ).first():
        return api_error("AUTH_ACCOUNT_EXISTS", "用户名或邮箱已存在", 409)
    if phone and User.query.filter_by(phone_hash=hash_phone(phone)).first():
        return api_error("AUTH_PHONE_EXISTS", "手机号已被使用", 409)

    user = User(
        username=username,
        email=normalized_email,
        email_normalized=normalized_email,
        password_hash=hash_password(password),
        user_type="normal_user",
        phone_ciphertext=encrypt_phone(phone),
        phone_hash=hash_phone(phone),
    )
    db.session.add(user)
    db.session.flush()
    assign_role(user, "normal_user")

    raw_token = opaque_token()
    db.session.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
    )
    db.session.commit()
    send_verification_email(user.email, raw_token)
    return api_ok({"user": user_public(user)}, status=201)


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    payload = _json()
    identifier = (payload.get("identifier") or "").strip()
    password = payload.get("password") or ""
    remember = bool(payload.get("remember", False))
    if not identifier or not password:
        return api_error("VALIDATION_ERROR", "账号和密码不能为空", 422)

    user = User.query.filter(
        db.or_(User.username == identifier, User.email_normalized == normalize_email(identifier))
    ).first()
    if user and user_is_locked(user):
        return api_error("AUTH_LOCKED", "登录失败次数过多，请稍后再试", 429)
    if not user or not verify_password(password, user.password_hash):
        record_login_failure(user)
        return api_error("AUTH_INVALID_CREDENTIALS", "用户名或密码错误", 401)
    if not user.is_active or user.deleted_at is not None:
        return api_error("AUTH_ACCOUNT_DISABLED", "账号已被禁用", 403)

    reset_login_failures(user)
    return _issue_session_response(user, remember=remember)


@auth_bp.post("/refresh")
@limiter.limit("30 per minute")
def refresh():
    if not validate_refresh_origin():
        return api_error("AUTH_INVALID_ORIGIN", "请求来源不受信任", 403)
    raw = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    if not raw:
        return api_error("AUTH_REFRESH_MISSING", "缺少刷新令牌", 401)
    rotated = rotate_session(raw)
    if not rotated:
        response, status = api_error("AUTH_REFRESH_INVALID", "刷新令牌无效或已过期", 401)
        clear_refresh_cookie(response)
        db.session.commit()
        return response, status
    new_raw, session = rotated
    user = db.session.get(User, session.user_id)
    db.session.commit()
    response, status = api_ok(
        {
            "access_token": create_access_token(user),
            "token_type": "Bearer",
            "expires_in": int(current_app.config["JWT_ACCESS_TTL_SECONDS"]),
            "user": user_public(user, include_permissions=True),
        }
    )
    set_refresh_cookie(response, new_raw)
    return response, status


@auth_bp.post("/logout")
def logout():
    raw = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    if raw:
        revoke_session(raw)
        db.session.commit()
    response, status = api_ok({"logged_out": True})
    clear_refresh_cookie(response)
    return response, status


@auth_bp.post("/logout-all")
@login_required
def logout_all(user):
    revoked = revoke_all_sessions(user.id)
    db.session.commit()
    response, status = api_ok({"revoked_sessions": revoked})
    clear_refresh_cookie(response)
    return response, status


@auth_bp.post("/verify-email")
@limiter.limit("10 per minute")
def verify_email():
    raw = _json().get("token") or ""
    row = _token_row(EmailVerificationToken, raw)
    if not row or row.expires_at <= datetime.utcnow():
        return api_error("AUTH_TOKEN_INVALID", "验证链接无效或已过期", 400)
    user = db.session.get(User, row.user_id)
    if not user:
        return api_error("AUTH_TOKEN_INVALID", "验证链接无效或已过期", 400)
    row.used_at = datetime.utcnow()
    user.email_verified_at = datetime.utcnow()
    db.session.commit()
    return api_ok({"verified": True})


@auth_bp.post("/resend-verification")
@login_required
@limiter.limit("3 per minute")
def resend_verification(user):
    if user.is_email_verified:
        return api_ok({"sent": False, "message": "邮箱已验证"})
    raw_token = opaque_token()
    db.session.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
    )
    db.session.commit()
    send_verification_email(user.email, raw_token)
    return api_ok({"sent": True})


@auth_bp.post("/forgot-password")
@limiter.limit("5 per minute")
def forgot_password():
    email = normalize_email(_json().get("email") or "")
    user = User.query.filter_by(email_normalized=email).first()
    if user and user.is_active:
        raw_token = opaque_token()
        db.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
        )
        db.session.commit()
        send_password_reset_email(user.email, raw_token)
    return api_ok({"sent": True})


@auth_bp.post("/reset-password")
@limiter.limit("5 per minute")
def reset_password():
    payload = _json()
    raw = payload.get("token") or ""
    password = payload.get("new_password") or ""
    errors = password_errors(password)
    if errors:
        return api_error("VALIDATION_ERROR", "密码不符合要求", 422, errors)
    row = _token_row(PasswordResetToken, raw)
    if not row or row.expires_at <= datetime.utcnow():
        return api_error("AUTH_TOKEN_INVALID", "重置链接无效或已过期", 400)
    user = db.session.get(User, row.user_id)
    if not user:
        return api_error("AUTH_TOKEN_INVALID", "重置链接无效或已过期", 400)
    row.used_at = datetime.utcnow()
    user.password_hash = hash_password(password)
    user.password_changed_at = datetime.utcnow()
    revoke_all_sessions(user.id)
    db.session.commit()
    return api_ok({"reset": True})


@auth_bp.get("/me")
@login_required
def me(user):
    return api_ok({"user": user_public(user, include_permissions=True)})
