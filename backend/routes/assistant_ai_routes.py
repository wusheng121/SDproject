"""Internal stateless assistant endpoint.

The Java main service owns conversations; Python only produces AI replies.
"""
import hmac

from flask import Blueprint, current_app, request

from extensions import db
from models import User
from services.agent_dialogue import converse
from utils.response import api_error, api_ok

assistant_ai_bp = Blueprint("assistant_ai_bp", __name__, url_prefix="/api/ai")


@assistant_ai_bp.post("/assistant-reply")
def assistant_reply():
    supplied = request.headers.get("X-Internal-Token", "")
    expected = current_app.config["SECRET_KEY"]
    if not supplied or not hmac.compare_digest(supplied, expected):
        return api_error("AUTH_FORBIDDEN", "无权访问内部助手接口", 403)

    payload = request.get_json(silent=True) or {}
    try:
        user_id = int(payload.get("user_id"))
    except (TypeError, ValueError):
        return api_error("VALIDATION_ERROR", "user_id 无效", 422)
    user = db.session.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        return api_error("AUTH_REQUIRED", "用户不存在或已禁用", 401)

    history = payload.get("history")
    slots = payload.get("slots")
    if history is not None and not isinstance(history, list):
        return api_error("VALIDATION_ERROR", "history 必须是数组", 422)
    if slots is not None and not isinstance(slots, dict):
        return api_error("VALIDATION_ERROR", "slots 必须是对象", 422)

    try:
        result = converse(
            user,
            payload.get("message"),
            filename=payload.get("filename"),
            image_data_url=payload.get("image_data_url"),
            history=history,
            slots=slots,
        )
    except ValueError as exc:
        return api_error("VALIDATION_ERROR", str(exc), 422)

    result.pop("row", None)
    result.pop("session_id", None)
    return api_ok(result)
