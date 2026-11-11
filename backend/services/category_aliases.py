"""Category synonyms shared by the Python assistant and NL filter."""

CATEGORY_ALIASES = {
    "书籍": "书籍",
    "教材": "书籍",
    "课本": "书籍",
    "书": "书籍",
    "保温水杯": "保温杯",
    "保温杯": "保温杯",
    "水杯": "保温杯",
    "杯子": "保温杯",
    "水壶": "保温杯",
    "智能手机": "手机",
    "电话": "手机",
    "手机": "手机",
    "单车": "自行车",
    "山地车": "自行车",
    "自行车": "自行车",
    "运动鞋": "运动鞋",
    "跑鞋": "运动鞋",
}


def resolve_category(text: str, category_names: list[str]) -> str | None:
    """Return a canonical category when text contains a known synonym."""
    if not text:
        return None
    names = set(category_names or [])
    for alias in sorted(CATEGORY_ALIASES, key=len, reverse=True):
        canonical = CATEGORY_ALIASES[alias]
        if alias in text and canonical in names:
            return canonical
    for name in sorted(names, key=len, reverse=True):
        if name and name in text:
            return name
    return None
