from flask import Blueprint, request

from auth import login_required
from extensions import db
from services.agent_dialogue import converse, recognize_image
from utils.audit import log_operation
from utils.response import api_error, api_ok

assistant_bp = Blueprint("assistant_bp", __name__, url_prefix="/api/v1/assistant")


@assistant_bp.post("/recognize")
@login_required
def recognize(user):
    payload = request.get_json(silent=True) or {}
    filename = (payload.get("filename") or "").strip()
    if not filename:
        return api_error("VALIDATION_ERROR", "请提供图片文件名", 422)
    result = recognize_image(filename)
    log_operation(user, "agent.recognize.mock", "product", after=result)
    db.session.commit()
    return api_ok(result)


@assistant_bp.post("/chat")
@login_required
def chat(user):
    payload = request.get_json(silent=True) or {}
    try:
        result = converse(
            user,
            payload.get("message"),
            payload.get("session_id"),
            payload.get("filename"),
        )
    except ValueError as exc:
        return api_error("VALIDATION_ERROR", str(exc), 422)

    row = result.pop("row")
    db.session.add(row)
    log_operation(
        user,
        "agent.dialogue.refuse" if result["refused"] else "agent.dialogue.query",
        "agent_dialogue",
        resource_id=result["session_id"],
        after={
            "skill": result["skill"],
            "engine": result["engine"],
            "slots": result["slots"],
            "count": len(result["items"]),
        },
    )
    db.session.commit()
    return api_ok(result)
