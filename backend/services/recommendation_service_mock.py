"""推荐服务 - 骨架版返回 Mock 数据，算法逻辑留给组员实现"""
from flask import Blueprint

from auth import login_required
from utils.response import ok

recommendation_bp = Blueprint("recommendation_bp", __name__, url_prefix="/api")


@recommendation_bp.get("/recommendations")
@login_required
def get_recommendations(user):
    """
    GET /api/recommendations
    个性化推荐接口 - 当前返回 Mock 数据
    
    TODO: 需要实现的推荐策略：
    A. 无兴趣标签 → 全局热门（按行为数排序）
    B. 有兴趣标签但无行为 → 基于内容推荐（根据选定品类）
    C. 有兴趣标签 + 少量行为(<10) → 轻量混合（70%内容 + 30%协同）
    D. 行为充足(>=10) → ML模型（矩阵分解 + 内容混合）
    
    数据来源：
    - 用户行为表 UserBehavior (behavior_type: favorite, review, view, add_cart, order)
    - 用户偏好品类 User.preferred_categories
    - 商品品类 ProductCategory
    
    参考原电影推荐系统：
    - backend/services/recommendation_service.py (原算法逻辑)
    - backend/ml/ (机器学习模型)
    """
    
    # Mock 推荐数据
    mock_items = [
        {
            "id": 1,
            "name": "保温杯 500ml 蓝色",
            "price": 35.0,
            "condition": "九成新",
            "image_url": None,
            "categories": ["保温杯"],
            "reason": "热门商品",
        },
        {
            "id": 2,
            "name": "耐克运动鞋 42码",
            "price": 180.0,
            "condition": "八成新",
            "image_url": None,
            "categories": ["运动鞋"],
            "reason": "热门商品",
        },
        {
            "id": 3,
            "name": "iPhone 12 128G",
            "price": 2800.0,
            "condition": "九五新",
            "image_url": None,
            "categories": ["手机"],
            "reason": "猜你喜欢",
        },
    ]
    
    return ok({
        "user_id": user.id,
        "items": mock_items,
        "strategy": "Mock",
        "message": "当前返回模拟数据，真实推荐算法待实现"
    })


# TODO: 相似商品推荐（基于商品详情页）
@recommendation_bp.get("/recommendations/similar/<int:product_id>")
def get_similar_products(product_id):
    """
    GET /api/recommendations/similar/:product_id
    相似商品推荐 - 基于品类、价格区间、成色（TODO: 待实现）
    """
    mock_items = [
        {
            "id": 2,
            "name": "小米保温杯 白色",
            "price": 28.0,
            "condition": "全新",
            "reason": "同类商品",
        }
    ]
    
    return ok({
        "product_id": product_id,
        "items": mock_items,
        "message": "相似商品推荐待实现"
    })
