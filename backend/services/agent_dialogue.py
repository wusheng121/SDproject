"""只读购物对话。多轮条件记在会话里；配置了 DeepSeek 密钥时由模型组织回答，商品仍从数据库查出。"""

import json
import logging
import re
import secrets

from models import AgentDialogue, Category, Product, ProductCategory
from services.deepseek_client import DeepSeekError, api_key, complete
from utils.serializers import product_public

logger = logging.getLogger(__name__)

WRITE_WORDS = (
    "删除",
    "删掉",
    "下架",
    "改价",
    "修改价格",
    "支付",
    "封禁",
    "退款",
    "取消订单",
    "上架",
    "下单",
    "帮我买",
    "改成已支付",
)
CHEAPER_WORDS = ("便宜一点", "再便宜", "便宜点", "价格低一点", "低一点")
RECOMMEND_WORDS = ("推荐", "猜我喜欢", "有什么推荐")
CONDITIONS = ("九五新", "九成新", "八成新", "七成新", "全新")
IMAGE_CATEGORIES = ("保温杯", "运动鞋", "手机", "耳机", "T恤", "鼠标")
BRANDS = ("耐克", "iPhone", "AirPods", "罗技", "优衣库", "索尼", "小米", "佳能", "JBL")


_IMAGE_DATA_RE = re.compile(r"^data:image/(?:jpeg|jpg|png|gif|webp);base64,[A-Za-z0-9+/=\r\n]+$", re.IGNORECASE)
_MAX_IMAGE_CHARS = 6_000_000


def valid_image_data_url(value: str) -> bool:
    return bool(value) and len(value) <= _MAX_IMAGE_CHARS and _IMAGE_DATA_RE.match(value) is not None


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


def recognize_photo(data_url: str) -> dict:
    """把图片发给 DeepSeek。只采纳品类表里的名称，成色不参与筛选。"""
    names = [row.name for row in Category.query.all() if row.name]
    allowed = list(dict.fromkeys([*names, *IMAGE_CATEGORIES]))
    prompt = (
        "看这张照片，用日常物品名写出你看到的东西，例如汽车、耳机。"
        f"如果它属于这些品类，category 就填品类名：{'、'.join(allowed)}。"
        "对不上就让 category 留空，不要硬凑成别的品类。"
        "成色只能是：全新、九五新、九成新、八成新、七成新。看不清成色就写九成新。"
        "品牌看不清就写未知品牌。用一句中文描述看到的物品。"
        '只返回 JSON：{"seen":"","category":"","brand":"","condition":"","description":""}'
    )
    data_url = re.sub(r"^data:image/jpg;", "data:image/jpeg;", data_url, count=1, flags=re.IGNORECASE)
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
    mentioned = str(parsed.get("category") or "").strip()
    seen = str(parsed.get("seen") or mentioned or "").strip()[:40]
    category = mentioned if mentioned in allowed else None
    if category is None:
        category = next((name for name in sorted(allowed, key=len, reverse=True) if name and name in mentioned), None)
    condition = parsed.get("condition")
    if condition not in CONDITIONS:
        condition = "九成新"
    description = str(parsed.get("description") or "")[:200]
    brand = str(parsed.get("brand") or "未知品牌")[:40]
    if category is None:
        if not seen and not description:
            raise DeepSeekError("识图结果里没有可用品类")
        return {
            "category": None,
            "seen": seen or description[:40],
            "brand": brand,
            "condition": condition,
            "description": description,
            "source": "deepseek",
            "matched": False,
        }
    return {
        "category": category,
        "seen": seen or category,
        "brand": brand,
        "condition": condition,
        "description": description,
        "source": "deepseek",
        "matched": True,
    }


def recognize_image(filename: str) -> dict:
    """按文件名做识物 Mock。没有模型 API 时，文件名里的品类就是识别结果。"""
    name = filename or "image.jpg"
    category = next((item for item in sorted(IMAGE_CATEGORIES, key=len, reverse=True) if item in name), None)
    if category is None:
        lowered = name.lower()
        aliases = {
            "earphone": "耳机",
            "headphone": "耳机",
            "phone": "手机",
            "shoe": "运动鞋",
            "cup": "保温杯",
            "mouse": "鼠标",
            "shirt": "T恤",
        }
        category = next((label for key, label in aliases.items() if key in lowered), None)
    brand = next((item for item in BRANDS if item.lower() in name.lower()), "未知品牌")
    stem = name.rsplit(".", 1)[0] if "." in name else name
    if category is None:
        return {
            "category": None,
            "seen": stem or name,
            "brand": brand,
            "condition": "九成新",
            "source": "mock",
            "matched": False,
            "filename": name,
        }
    return {
        "category": category,
        "seen": category,
        "brand": brand,
        "condition": "九成新",
        "source": "mock",
        "matched": True,
        "filename": name,
    }


def _load(user, session_id: str | None) -> AgentDialogue:
    if session_id:
        row = AgentDialogue.query.filter_by(id=session_id, user_id=user.id).first()
        if row:
            return row
    row = AgentDialogue(
        id=secrets.token_hex(16),
        user_id=user.id,
        slots_json="{}",
        messages_json="[]",
    )
    return row


def _slots(row: AgentDialogue) -> dict:
    try:
        data = json.loads(row.slots_json or "{}")
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def _messages(row: AgentDialogue) -> list:
    try:
        data = json.loads(row.messages_json or "[]")
    except json.JSONDecodeError:
        data = []
    return data if isinstance(data, list) else []


def _extract(text: str, slots: dict) -> tuple[dict, str]:
    updated = dict(slots)
    if any(word in text for word in WRITE_WORDS):
        return updated, "refuse"

    prices = re.findall(r"(\d+(?:\.\d+)?)\s*元以?内", text)
    prices += re.findall(r"不超过\s*(\d+(?:\.\d+)?)", text)
    if prices:
        updated["max_price"] = float(prices[0])
    above = re.findall(r"(\d+(?:\.\d+)?)\s*元以上", text)
    if above:
        updated["min_price"] = float(above[0])

    for condition in CONDITIONS:
        if condition in text:
            updated["condition"] = condition
            break

    names = [row.name for row in Category.query.all()]
    mentioned = None
    for name in sorted(names, key=len, reverse=True):
        if name and name in text:
            mentioned = name
            updated["category"] = name
            break

    if any(word in text for word in CHEAPER_WORDS):
        current = updated.get("max_price")
        if current is None and updated.get("last_prices"):
            current = max(updated["last_prices"])
        if current is not None:
            updated["max_price"] = round(float(current) * 0.8, 2)
        updated["sort"] = "price"

    recommend_only = any(word in text for word in RECOMMEND_WORDS) and mentioned is None and not prices
    if recommend_only:
        return updated, "recommend"
    return updated, "search"


def _query(slots: dict) -> list[Product]:
    query = Product.query.filter(Product.status == "approved")
    category = slots.get("category")
    if category:
        query = (
            query.join(ProductCategory, ProductCategory.product_id == Product.id)
            .join(Category, Category.id == ProductCategory.category_id)
            .filter(Category.name == category)
        )
    if slots.get("condition"):
        query = query.filter(Product.condition == slots["condition"])
    if slots.get("max_price") is not None:
        query = query.filter(Product.price <= float(slots["max_price"]))
    if slots.get("min_price") is not None:
        query = query.filter(Product.price >= float(slots["min_price"]))
    if slots.get("sort") == "price":
        query = query.order_by(Product.price.asc())
    else:
        query = query.order_by(Product.created_at.desc())
    return query.distinct().limit(6).all()


def _recommend(slots: dict) -> list[Product]:
    category = slots.get("category")
    if category:
        return _query({**slots, "sort": "price"})
    return (
        Product.query.filter(Product.status == "approved")
        .order_by(Product.created_at.desc())
        .limit(3)
        .all()
    )


def _conditions(slots: dict) -> str:
    parts = []
    if slots.get("category"):
        parts.append(f"品类是{slots['category']}")
    if slots.get("condition"):
        parts.append(f"成色是{slots['condition']}")
    if slots.get("max_price") is not None:
        parts.append(f"价格不超过 {slots['max_price']} 元")
    if slots.get("min_price") is not None:
        parts.append(f"价格不低于 {slots['min_price']} 元")
    return "，".join(parts)


def _reply(skill: str, slots: dict, items: list, recognition: dict | None) -> str:
    if skill == "refuse":
        return (
            "这个操作我不能做。我只能帮你查商品、按上一轮条件继续筛选，"
            "不能删除、改价、下单或支付。商品还在，你可以换个说法，比如「只要九成新」或「便宜一点」。"
        )
    lines = []
    if recognition and recognition.get("matched") is False:
        seen = recognition.get("seen") or "这件物品"
        lines.append(f"我看过这张图片，它更像「{seen}」。商品库里没有这个品类，没有拿其他商品来凑。")
        return "\n".join(lines)
    if recognition and recognition.get("source") == "deepseek":
        detail = recognition.get("description") or ""
        lines.append(f"我看过这张图片，它更像「{recognition['category']}」。{detail}".rstrip())
    elif recognition:
        lines.append(
            f"我看到文件名里有「{recognition['category']}」，先按这个品类来找，没有调用识图模型。"
        )
    heard = _conditions(slots)
    if skill == "recommend" and not heard:
        lines.append("你想看推荐。我按最新上架查了在售商品，没有改任何数据。")
    elif heard:
        lines.append(f"我记住的条件是：{heard}。")
    if not items:
        lines.append("按这些条件没有找到在售商品。可以说「便宜一点」以外的品类，或把价格放宽。")
        return "\n".join(lines)
    lines.append(f"已为您找到如下 {len(items)} 件商品：")
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.name}，{item.condition}，{item.price:g} 元")
    lines.append("可以继续追问，例如「只要九成新」或「便宜一点」。")
    return "\n".join(lines)


def _catalog(items: list) -> str:
    if not items:
        return "当前条件下没有在售商品。"
    lines = []
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.name}，{item.condition}，{item.price:g} 元")
    return "\n".join(lines)


def _model_messages(text: str, slots: dict, items: list, recognition: dict | None, history: list) -> list[dict]:
    heard = _conditions(slots) or "还没有筛选条件"
    seen = ""
    if recognition and recognition.get("matched") is False:
        outside = recognition.get("seen") or "这件物品"
        seen = (
            f"用户这张图片已看过，内容是「{outside}」，不在商品品类中。"
            "不要用上一轮的品类或商品冒充这张图片的结果，直接说明平台没有这一类。\n"
        )
    elif recognition and recognition.get("source") == "deepseek":
        seen = (
            f"用户上传的图片已被识图模型看过，品类是{recognition['category']}，"
            f"品牌是{recognition.get('brand') or '未知品牌'}，"
            f"成色只是猜测：{recognition.get('condition') or '不确定'}。"
            f"{recognition.get('description') or ''}"
            "筛选只用品类，不要因为猜测的成色把商品滤掉。\n"
        )
    elif recognition:
        failed = "识图模型没有看成功，" if recognition.get("fallback") else ""
        seen = (
            f"{failed}用户上传的文件名被 Mock 识别为{recognition['category']}，"
            "没有读取图片像素。\n"
        )
    system = (
        "你是校园二手市场的购物助手。下面的商品来自数据库，只能推荐这些，"
        "不要编造列表之外的名称、价格或库存。你可以回答商品是否适合某个用途，"
        "但要说明依据是列表里的哪一件。你不能删除、改价、下单、支付或封禁，"
        "也不要声称已经做了这些操作。用简短中文回答。\n"
        f"当前记住的条件：{heard}。\n"
        f"{seen}"
        f"在售商品：\n{_catalog(items)}"
    )
    messages = [{"role": "system", "content": system}]
    for item in history[-8:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": text})
    return messages


def converse(
    user,
    message: str | None,
    session_id: str | None = None,
    filename: str | None = None,
    image_data_url: str | None = None,
) -> dict:
    text = (message or "").strip()
    filename = (filename or "").strip()
    image_data_url = (image_data_url or "").strip()
    if image_data_url and not valid_image_data_url(image_data_url):
        raise ValueError("图片只支持 4MB 以内的 JPEG、PNG、GIF、WebP")
    if not text and not filename and not image_data_url:
        raise ValueError("请输入一句话，或上传一张图片")

    row = _load(user, session_id)
    slots = _slots(row)
    recognition = None
    refused_early = bool(text) and any(word in text for word in WRITE_WORDS)
    if image_data_url and api_key() and not refused_early:
        try:
            recognition = recognize_photo(image_data_url)
        except DeepSeekError as exc:
            logger.warning("DeepSeek 识图失败，改用文件名：%s", exc)
            recognition = recognize_image(filename) if filename else None
            if recognition:
                recognition["fallback"] = True
    elif filename or image_data_url:
        recognition = recognize_image(filename or "image.jpg")
    unmatched = bool(recognition) and recognition.get("matched") is False
    if unmatched:
        slots.pop("category", None)
        text = text or f"这张图片是{recognition.get('seen') or '一件物品'}"
    elif recognition and recognition.get("category"):
        slots["category"] = recognition["category"]
        text = text or f"帮我找{recognition['category']}"

    slots, skill = _extract(text, slots)
    items = []
    if unmatched:
        slots.pop("category", None)
        skill = "search"
    elif skill == "search":
        items = _query(slots)
    elif skill == "recommend":
        items = _recommend(slots)
    reply = _reply(skill, slots, items, recognition)
    engine = "rules"
    history = _messages(row)
    if skill != "refuse" and api_key():
        try:
            reply = complete(_model_messages(text, slots, items, recognition, history))
            engine = "deepseek"
        except DeepSeekError as exc:
            logger.warning("DeepSeek 调用失败，改用规则回复：%s", exc)
            reply = f"模型暂时没连上，已改用规则查询。\n{reply}"
    if skill != "refuse":
        slots["last_prices"] = [float(item.price) for item in items]
        slots.pop("sort", None)
    history.append({"role": "user", "content": text, "filename": filename or None})
    history.append({"role": "assistant", "content": reply, "skill": skill, "engine": engine})
    row.slots_json = json.dumps(slots, ensure_ascii=False)
    row.messages_json = json.dumps(history[-20:], ensure_ascii=False)
    return {
        "row": row,
        "session_id": row.id,
        "reply": reply,
        "engine": engine,
        "skill": skill,
        "refused": skill == "refuse",
        "recognition": recognition,
        "slots": {key: slots.get(key) for key in ("category", "condition", "max_price", "min_price")},
        "items": [product_public(item) for item in items],
    }
