def get_recommendations_for_user(user_id: int, limit: int = 10):
    """
    推荐服务（占位实现）

    你后续可以替换为：
    - 热门推荐：按收藏数/评分数排序
    - 个性化推荐：统计用户高分电影的类型偏好，再推荐同类型 TopN
    - 协同过滤：基于用户-电影评分矩阵做相似度（课程项目可简化）
    """
    # mock：返回固定列表，便于前端联调
    demo = [
        {"id": 1, "title": "Interstellar", "release_year": 2014, "poster_url": None},
        {"id": 2, "title": "Inception", "release_year": 2010, "poster_url": None},
        {"id": 3, "title": "The Dark Knight", "release_year": 2008, "poster_url": None},
    ]
    return demo[: max(0, limit)]



