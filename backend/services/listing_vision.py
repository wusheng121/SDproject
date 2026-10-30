"""识图发单。只给发布页预填名称、品类和成色，不搜索商品，也不给出售价。"""

import base64
import json
import re

from models import Category
from services.deepseek_client import DeepSeekError, api_key, complete

CONDITIONS = ("全新", "九五新", "九成新", "八成新", "七成新")
MAX_IMAGE_BYTES = 4 * 1024 * 1024
_MIME_FORMATS = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


class ListingVisionError(Exception):
    pass


def recognize_listing(image_bytes: bytes, mime: str) -> dict:
    if not api_key():
        raise ListingVisionError("识图暂时不可用，请直接填写")
    image_format = _image_format(image_bytes, mime)
    if not image_format:
        raise ListingVisionError("图片只支持 JPEG、PNG、GIF、WebP")
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise ListingVisionError("图片请小于 4MB")

    names = [row.name for row in Category.query.order_by(Category.name.asc()).all() if row.name]
    if not names:
        raise ListingVisionError("还没有可选品类，请直接填写")
    prompt = (
        "这是一张准备发布的二手商品照片。请识别物品名称、品牌、品类和成色。"
        f"品类只能从这里选：{'、'.join(names)}。"
        "成色只能是：全新、九五新、九成新、八成新、七成新。看不清成色就写九成新。"
        "名称写成买家能看懂的短标题。品牌看不清就留空。用一句中文描述看到的物品。"
        "不要编造价格。"
        '只返回 JSON：{"name":"","brand":"","category":"","condition":"","description":""}'
    )
    data_url = f"data:image/{image_format};base64," + base64.b64encode(image_bytes).decode("ascii")
    try:
        raw = complete(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                    ],
                }
            ]
        )
        parsed = _json_object(raw)
    except DeepSeekError as exc:
        raise ListingVisionError("没看清这张照片，请直接填写") from exc

    mentioned = str(parsed.get("category") or "")
    category = mentioned if mentioned in names else None
    if category is None:
        category = next((name for name in sorted(names, key=len, reverse=True) if name and name in mentioned), None)
    if category is None:
        raise ListingVisionError("没识别出可选品类，请直接填写")

    condition = parsed.get("condition")
    if condition not in CONDITIONS:
        condition = "九成新"
    name = str(parsed.get("name") or "").strip()
    description = str(parsed.get("description") or "").strip()
    if not name:
        name = description[:40]
    if not name:
        raise ListingVisionError("没识别出商品名称，请直接填写")
    brand = str(parsed.get("brand") or "").strip()
    if brand in {"未知", "未知品牌", "无", "无品牌"}:
        brand = ""
    return {
        "name": name[:80],
        "brand": brand[:40],
        "category": category,
        "condition": condition,
        "description": description[:200],
        "source": "deepseek",
    }


def _image_format(image_bytes: bytes, mime: str) -> str | None:
    declared = _MIME_FORMATS.get((mime or "").split(";")[0].strip().lower())
    sniffed = _sniff(image_bytes)
    if declared and sniffed and declared != sniffed:
        return sniffed
    return declared or sniffed


def _sniff(image_bytes: bytes) -> str | None:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def _json_object(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = raw.removesuffix("```").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise DeepSeekError("识图结果不是 JSON")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise DeepSeekError("识图结果不是 JSON") from exc
    if not isinstance(data, dict):
        raise DeepSeekError("识图结果不是 JSON")
    return data
