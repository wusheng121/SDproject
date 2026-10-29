import json
import logging
import re
from datetime import datetime, timezone

from flask import g, has_request_context

_PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = getattr(g, "trace_id", "-") if has_request_context() else "-"
        record.route = getattr(g, "route", "-") if has_request_context() else "-"
        if isinstance(record.msg, str):
            record.msg = _PHONE_RE.sub(lambda m: f"{m.group(0)[:3]}****{m.group(0)[-4:]}", record.msg)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
            "route": getattr(record, "route", "-"),
        }
        for key in ("method", "path", "status", "latency_ms", "user_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    if app.config.get("APP_ENV") == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(trace_id)s] %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(app.config.get("LOG_LEVEL", "INFO"))
