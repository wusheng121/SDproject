import json

from flask import g, has_request_context, request

from extensions import db
from models import OperationLog

_SENSITIVE_KEYS = {"password", "password_hash", "token", "refresh_token", "phone", "authorization"}


def _sanitize(value):
    if isinstance(value, dict):
        return {
            key: ("***" if key.lower() in _SENSITIVE_KEYS else _sanitize(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _dumps(value):
    if value is None:
        return None
    return json.dumps(_sanitize(value), ensure_ascii=False, default=str)


def log_operation(
    actor,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    before=None,
    after=None,
    commit: bool = False,
):
    entry = OperationLog(
        actor_id=getattr(actor, "id", None),
        actor_snapshot=getattr(actor, "username", None),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        before_json=_dumps(before),
        after_json=_dumps(after),
        ip=(request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
        if has_request_context()
        else None,
        user_agent=(request.headers.get("User-Agent") or "")[:255]
        if has_request_context()
        else None,
        trace_id=getattr(g, "trace_id", None),
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry
