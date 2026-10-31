"""DeepSeek 对话。密钥只从环境变量读取，不写进仓库。"""

import json
import os
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
    model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-flash").strip()
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    try:
        return _parse(_post(base, key, payload))
    except DeepSeekError as exc:
        if "返回 400" not in str(exc):
            raise
        payload.pop("thinking", None)
        return _parse(_post(base, key, payload))


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
    # 空代理表示直连，不走本机 VPN。拉下代码的人同样直连 api.deepseek.com。
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:240]
        raise DeepSeekError(f"DeepSeek 返回 {exc.code}：{detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DeepSeekError("DeepSeek 连接失败") from exc


def _parse(body: dict) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekError("DeepSeek 响应里没有回复文本") from exc
    text = (content or "").strip()
    if not text:
        raise DeepSeekError("DeepSeek 回复为空")
    return text
