"""策略 D 使用的 ALS 矩阵分解。

用户-商品矩阵来自行为权重。交替更新用户隐向量和商品隐向量，
预测用户还没互动过的商品。课程环境不一定能安装 scikit-surprise，
这里用同一套交替最小二乘，不额外依赖编译包。
"""

from __future__ import annotations

import math
import random


def als_predict(
    ratings: dict[tuple[int, int], float],
    user_id: int,
    candidates: list[int],
    factors: int = 4,
    iterations: int = 8,
    regularization: float = 0.1,
) -> dict[int, float]:
    users = sorted({user for user, _ in ratings})
    items = sorted({item for _, item in ratings} | set(candidates))
    if user_id not in users or not items or not ratings:
        return {}
    user_index = {user: index for index, user in enumerate(users)}
    item_index = {item: index for index, item in enumerate(items)}
    random.seed(7)
    user_factors = [[random.random() * 0.1 for _ in range(factors)] for _ in users]
    item_factors = [[random.random() * 0.1 for _ in range(factors)] for _ in items]
    by_user: dict[int, list[tuple[int, float]]] = {index: [] for index in range(len(users))}
    by_item: dict[int, list[tuple[int, float]]] = {index: [] for index in range(len(items))}
    for (user, item), value in ratings.items():
        by_user[user_index[user]].append((item_index[item], value))
        by_item[item_index[item]].append((user_index[user], value))

    for _ in range(iterations):
        for index, observed in by_user.items():
            user_factors[index] = _solve(observed, item_factors, factors, regularization)
        for index, observed in by_item.items():
            item_factors[index] = _solve(observed, user_factors, factors, regularization)

    target = user_index[user_id]
    scores = {}
    for item in candidates:
        if item not in item_index:
            continue
        scores[item] = _dot(user_factors[target], item_factors[item_index[item]])
    return _normalize(scores)


def _solve(observed: list[tuple[int, float]], opposite: list[list[float]], factors: int, regularization: float) -> list[float]:
    if not observed:
        return [0.0] * factors
    gram = [[regularization if i == j else 0.0 for j in range(factors)] for i in range(factors)]
    target = [0.0] * factors
    for index, value in observed:
        vector = opposite[index]
        for row in range(factors):
            target[row] += vector[row] * value
            for col in range(factors):
                gram[row][col] += vector[row] * vector[col]
    return _gaussian(gram, target)


def _gaussian(matrix: list[list[float]], target: list[float]) -> list[float]:
    size = len(target)
    rows = [row[:] + [target[index]] for index, row in enumerate(matrix)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(rows[row][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        if abs(rows[col][col]) < 1e-9:
            continue
        divisor = rows[col][col]
        for col2 in range(col, size + 1):
            rows[col][col2] /= divisor
        for row in range(size):
            if row == col:
                continue
            factor = rows[row][col]
            for col2 in range(col, size + 1):
                rows[row][col2] -= factor * rows[col][col2]
    return [rows[index][size] for index in range(size)]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _normalize(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    low = min(scores.values())
    high = max(scores.values())
    if math.isclose(low, high):
        return {item: 1.0 for item in scores}
    return {item: (value - low) / (high - low) for item, value in scores.items()}
