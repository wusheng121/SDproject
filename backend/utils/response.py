from flask import g, jsonify


def ok(data=None, message="ok"):
    """Legacy envelope kept for existing routes."""
    return jsonify({"code": 0, "message": message, "data": data})


def err(message="error", code=1, http_status=400):
    """Legacy envelope kept for existing routes."""
    return jsonify({"code": code, "message": message, "data": None}), http_status


def api_ok(data=None, status=200, pagination=None):
    body = {"data": data}
    if pagination is not None:
        body["pagination"] = pagination
    return jsonify(body), status


def api_error(code, message, status=400, details=None):
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "trace_id": getattr(g, "trace_id", None),
        }
    }
    return jsonify(body), status
