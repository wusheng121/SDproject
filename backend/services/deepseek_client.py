"""DeepSeek client with retry and fallback model support."""
import json
import os
import time
import urllib.error
import urllib.request


class DeepSeekError(Exception):
    pass


def api_key() -> str:
    return (os.getenv("DEEPSEEK_API_KEY") or "").strip()


def complete(messages: list[dict]) -> str:
    key = api_key()
    if not key:
        raise DeepSeekError("未配置 DEEPSEEK_API_KEY")
    base = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    primary = (os.getenv("DEEPSEEK_MODEL") or "deepseek-flash").strip()
    fallback = (os.getenv("DEEPSEEK_FALLBACK_MODEL") or "").strip()

    models = [primary]
    if fallback and fallback != primary:
        models.append(fallback)

    last_error = None
    for model in models:
        for attempt in range(3):
            try:
                return _complete_once(base, key, model, messages)
            except DeepSeekError as exc:
                last_error = exc
                if not _retryable(exc) or attempt == 2:
                    break
                time.sleep(1.5 * (attempt + 1))
    raise last_error or DeepSeekError("DeepSeek 请求失败")


def _complete_once(base: str, key: str, model: str, messages: list[dict]) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    try:
        return _parse(_post(base, key, payload))
    except DeepSeekError as exc:
        if "400" not in str(exc):
            raise
        payload.pop("thinking", None)
        return _parse(_post(base, key, payload))


def _retryable(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in ("429", "500", "502", "503", "504", "too busy", "繁忙"))


def _post(base: str, key: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:240]
        raise DeepSeekError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DeepSeekError("DeepSeek network error") from exc


def _parse(body: dict) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekError("DeepSeek response has no text") from exc
    text = (content or "").strip()
    if not text:
        raise DeepSeekError("DeepSeek response is empty")
    return text
