from services.category_aliases import resolve_category
from services.nl_filter import parse_nl


def test_category_aliases_resolve_common_synonyms():
    names = ["书籍", "保温杯", "手机", "自行车"]

    assert resolve_category("推荐一些书", names) == "书籍"
    assert resolve_category("推荐一些教材", names) == "书籍"
    assert resolve_category("推荐一些水杯", names) == "保温杯"
    assert resolve_category("想买单车", names) == "自行车"


def test_nl_filter_uses_category_aliases():
    result = parse_nl("推荐一些书", ["书籍", "保温杯"])

    assert result["category"] == "书籍"
