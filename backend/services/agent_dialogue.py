"""不调用大模型的只读对话。多轮条件记在会话里，追问只改上一轮的筛选。"""

import json
import re
import secrets

from models import AgentDialogue, Category, Product, ProductCategory
from utils.serializers import product_public

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
    if category is None:
        category = IMAGE_CATEGORIES[sum(ord(char) for char in name) % len(IMAGE_CATEGORIES)]
    brand = next((item for item in BRANDS if item.lower() in name.lower()), "未知品牌")
    return {
        "category": category,
        "brand": brand,
        "condition": "九成新",
        "source": "mock",
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


def _reply(skill: str, slots: dict, items: list, recognition: dict | None) -> str:
    if skill == "refuse":
        return "这个操作我不能做。我只能查询商品和推荐，不能删除、改价、下单或支付。请到对应页面自己操作。"
    prefix = ""
    if recognition:
        prefix = (
            f"这张图看起来是{recognition['brand']}的{recognition['condition']}{recognition['category']}。"
        )
    if skill == "recommend":
        prefix += "按你的追问，我用只读推荐查了一下。"
    elif slots.get("max_price") is not None and slots.get("sort") == "price":
        prefix += f"已把价格上限调到 {slots['max_price']} 元。"
    elif slots.get("condition") and slots.get("category"):
        prefix += f"继续按{slots['category']}、{slots['condition']}筛选。"
    if not items:
        return prefix + "没有找到符合条件的在售商品。可以换个品类，或把价格放宽一点。"
    return prefix + f"已为您找到如下 {len(items)} 件商品："


def converse(user, message: str | None, session_id: str | None = None, filename: str | None = None) -> dict:
    text = (message or "").strip()
    filename = (filename or "").strip()
    if not text and not filename:
        raise ValueError("请输入一句话，或上传一张图片")

    row = _load(user, session_id)
    slots = _slots(row)
    recognition = None
    if filename:
        recognition = recognize_image(filename)
        slots["category"] = recognition["category"]
        text = text or f"帮我找{recognition['category']}"

    slots, skill = _extract(text, slots)
    items = []
    if skill == "search":
        items = _query(slots)
    elif skill == "recommend":
        items = _recommend(slots)
    reply = _reply(skill, slots, items, recognition)
    if skill != "refuse":
        slots["last_prices"] = [float(item.price) for item in items]
        slots.pop("sort", None)
    history = _messages(row)
    history.append({"role": "user", "content": text, "filename": filename or None})
    history.append({"role": "assistant", "content": reply, "skill": skill})
    row.slots_json = json.dumps(slots, ensure_ascii=False)
    row.messages_json = json.dumps(history[-20:], ensure_ascii=False)
    return {
        "row": row,
        "session_id": row.id,
        "reply": reply,
        "skill": skill,
        "refused": skill == "refuse",
        "recognition": recognition,
        "slots": {key: slots.get(key) for key in ("category", "condition", "max_price", "min_price")},
        "items": [product_public(item) for item in items],
    }
