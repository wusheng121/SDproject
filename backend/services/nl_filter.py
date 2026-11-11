"""把一句话筛选成品类、成色和价格。查询仍走参数绑定，不拼接 SQL。"""

import re

from services.category_aliases import resolve_category

CONDITIONS = ("九五新", "九成新", "八成新", "七成新", "全新")


def parse_nl(text: str, category_names: list[str]) -> dict:
    raw = (text or "").strip()
    slots = {
        "text": raw,
        "keyword": "",
        "category": "",
        "min_condition": "",
        "min_price": None,
        "max_price": None,
    }
    if not raw:
        return slots

    between = re.search(r"(\d+(?:\.\d+)?)\s*[-~到至]\s*(\d+(?:\.\d+)?)\s*元", raw)
    if between:
        low = float(between.group(1))
        high = float(between.group(2))
        slots["min_price"] = min(low, high)
        slots["max_price"] = max(low, high)
    else:
        ceiling = re.search(r"(\d+(?:\.\d+)?)\s*元以?内", raw) or re.search(r"不超过\s*(\d+(?:\.\d+)?)", raw)
        if ceiling:
            slots["max_price"] = float(ceiling.group(1))
        floor = re.search(r"(\d+(?:\.\d+)?)\s*元以上", raw)
        if floor:
            slots["min_price"] = float(floor.group(1))

    for condition in CONDITIONS:
        if condition in raw:
            slots["min_condition"] = condition
            break

    category = resolve_category(raw, category_names)
    if category:
        slots["category"] = category

    keyword = raw
    for piece in (slots["category"], slots["min_condition"], "元以内", "元内", "元以上", "不超过"):
        if piece:
            keyword = keyword.replace(piece, " ")
    keyword = re.sub(r"\d+(?:\.\d+)?", " ", keyword)
    keyword = re.sub(r"[\s的了和与或,，。]+", " ", keyword).strip()
    if len(keyword) >= 2:
        slots["keyword"] = keyword
    return slots
