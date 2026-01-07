# 步骤三：模型集成模块使用指南

## 📚 模块概述

`recommender.py` 提供了完整的推荐系统接口，整合了混合推荐模型（ALS + 基于内容）。

### 核心功能

1. **个性化推荐**：基于用户历史评分生成推荐
2. **热门推荐**：适用于新用户冷启动场景
3. **相似电影推荐**：基于电影内容特征
4. **多样性推荐**：避免推荐过多相同类型的电影

## 🚀 快速开始

### 1. 基础使用

```python
from ml.recommender import Recommender

# 初始化推荐系统
recommender = Recommender(
    hybrid_model_path='../data/output5/hybrid_model.pkl',
    movies_path='../data/ml-latest-small/movies.csv',
    ratings_path='../data/output1/ratings_train.csv'
)

# 为用户生成推荐
recommendations = recommender.get_recommendations(user_id=1, n=10)

# 打印推荐结果
for rec in recommendations:
    print(f"{rec['title']}: 预测评分 {rec['predicted_rating']:.2f}")
```

### 2. 测试推荐系统

```bash
cd backend
python -m ml.recommender --user-id 1 --movie-id 1
```

输出示例：
```
======================================================================
模型信息
======================================================================
  model_type: Hybrid (ALS + Content-Based)
  alpha: 0.30
  als_weight: 30%
  content_weight: 70%
  ...

======================================================================
为用户 1 生成个性化推荐 (Top 10)
======================================================================

1. Toy Story (1995)
   预测评分: 4.23
   类型: Animation|Children|Comedy
   平均评分: 3.92 (247 人评分)
...
```

## 📖 API 参考

### `Recommender` 类

#### 初始化

```python
recommender = Recommender(
    hybrid_model_path='../data/output5/hybrid_model.pkl',
    movies_path='../data/ml-latest-small/movies.csv',
    ratings_path='../data/output1/ratings_train.csv'
)
```

**参数：**
- `hybrid_model_path`: 混合模型文件路径
- `movies_path`: 电影元数据CSV路径
- `ratings_path`: 评分数据CSV路径（用于计算热门度）

---

### 方法1：`get_recommendations()`

为用户生成个性化推荐

```python
recommendations = recommender.get_recommendations(
    user_id=1,
    n=10,
    exclude_rated=True,
    diversity=False
)
```

**参数：**
- `user_id` (int): 用户ID
- `n` (int): 推荐数量，默认10
- `exclude_rated` (bool): 是否排除已评分电影，默认True
- `diversity` (bool): 是否启用多样性推荐，默认False

**返回：**
```python
[
    {
        'movie_id': 1,
        'title': 'Toy Story (1995)',
        'predicted_rating': 4.23,
        'genres': 'Animation|Children|Comedy',
        'avg_rating': 3.92,
        'rating_count': 247,
        'popularity_score': 3.85
    },
    ...
]
```

**使用示例：**
```python
# 普通推荐
recs = recommender.get_recommendations(user_id=1, n=10)

# 多样性推荐（避免同类型电影扎堆）
diverse_recs = recommender.get_recommendations(user_id=1, n=10, diversity=True)
```

---

### 方法2：`get_popular_recommendations()`

获取热门电影推荐（冷启动场景）

```python
popular = recommender.get_popular_recommendations(n=10)
```

**参数：**
- `n` (int): 推荐数量，默认10

**返回：**
```python
[
    {
        'movie_id': 318,
        'title': 'Shawshank Redemption, The (1994)',
        'predicted_rating': 4.45,  # 平均评分
        'genres': 'Crime|Drama',
        'avg_rating': 4.45,
        'rating_count': 317,
        'popularity_score': 4.42
    },
    ...
]
```

**使用场景：**
- 新用户推荐（没有历史数据）
- 首页热门电影展示
- 作为个性化推荐的补充

---

### 方法3：`get_similar_movies()`

获取相似电影推荐（基于内容）

```python
similar = recommender.get_similar_movies(movie_id=1, n=10)
```

**参数：**
- `movie_id` (int): 电影ID
- `n` (int): 推荐数量，默认10

**返回：**
```python
[
    {
        'movie_id': 3114,
        'title': 'Toy Story 2 (1999)',
        'similarity': 0.95,
        'genres': 'Animation|Children|Comedy',
        'avg_rating': 3.86,
        'rating_count': 198
    },
    ...
]
```

**使用场景：**
- 电影详情页的"相似推荐"
- "喜欢这部电影的人还喜欢"
- 基于用户浏览历史的推荐

---

### 方法4：`get_model_info()`

获取模型信息

```python
info = recommender.get_model_info()
```

**返回：**
```python
{
    'model_type': 'Hybrid (ALS + Content-Based)',
    'alpha': 0.30,
    'als_weight': '30%',
    'content_weight': '70%',
    'als_users': 610,
    'als_movies': 8974,
    'content_movies': 9742,
    'global_mean_rating': 3.508
}
```

---

## 🔧 Flask 集成示例

### 在现有 Flask 应用中集成

#### 步骤1：在 `app.py` 中初始化

```python
from ml.recommender import Recommender

recommender = None

def create_app():
    app = Flask(__name__)
    
    # 初始化推荐系统
    global recommender
    recommender = Recommender(
        hybrid_model_path='./data/output5/hybrid_model.pkl',
        movies_path='./data/ml-latest-small/movies.csv',
        ratings_path='./data/output1/ratings_train.csv'
    )
    
    # ... 注册蓝图等
    
    return app
```

#### 步骤2：创建推荐路由

```python
from flask import Blueprint, request, jsonify

recommend_bp = Blueprint('recommend', __name__)

@recommend_bp.get('/api/recommendations')
def get_recommendations():
    """个性化推荐接口"""
    user_id = int(request.args.get('user_id', 0))
    n = int(request.args.get('n', 10))
    
    recommendations = recommender.get_recommendations(user_id, n)
    
    return jsonify({
        "code": 0,
        "data": recommendations
    })

@recommend_bp.get('/api/recommendations/popular')
def get_popular():
    """热门推荐接口"""
    n = int(request.args.get('n', 10))
    popular = recommender.get_popular_recommendations(n)
    
    return jsonify({
        "code": 0,
        "data": popular
    })

@recommend_bp.get('/api/recommendations/similar/<int:movie_id>')
def get_similar(movie_id):
    """相似电影推荐接口"""
    n = int(request.args.get('n', 10))
    similar = recommender.get_similar_movies(movie_id, n)
    
    return jsonify({
        "code": 0,
        "data": similar
    })

# 注册蓝图
app.register_blueprint(recommend_bp)
```

#### 步骤3：前端调用

```javascript
// 获取个性化推荐
async function getRecommendations(userId) {
  const response = await fetch(`/api/recommendations?user_id=${userId}&n=10`);
  const data = await response.json();
  return data.data;
}

// 获取热门推荐
async function getPopular() {
  const response = await fetch('/api/recommendations/popular?n=10');
  const data = await response.json();
  return data.data;
}

// 获取相似电影
async function getSimilar(movieId) {
  const response = await fetch(`/api/recommendations/similar/${movieId}?n=10`);
  const data = await response.json();
  return data.data;
}
```

---

## 🎯 使用场景示例

### 场景1：首页推荐

```python
# 检查用户是否登录
if user_is_logged_in():
    # 个性化推荐
    recommendations = recommender.get_recommendations(
        user_id=current_user.id,
        n=12,
        diversity=True  # 多样性推荐
    )
else:
    # 热门推荐
    recommendations = recommender.get_popular_recommendations(n=12)
```

### 场景2：电影详情页

```python
# 显示与当前电影相似的推荐
similar_movies = recommender.get_similar_movies(
    movie_id=current_movie_id,
    n=6
)
```

### 场景3：用户个人中心

```python
# 为你推荐
personal_recs = recommender.get_recommendations(
    user_id=user_id,
    n=20,
    exclude_rated=True
)

# 分类显示
action_recs = [r for r in personal_recs if 'Action' in r['genres']][:5]
comedy_recs = [r for r in personal_recs if 'Comedy' in r['genres']][:5]
drama_recs = [r for r in personal_recs if 'Drama' in r['genres']][:5]
```

### 场景4：搜索结果页

```python
# 基于搜索结果推荐相似电影
search_results = search_movies(query)

# 为每个搜索结果推荐相似电影
for movie in search_results:
    movie['similar'] = recommender.get_similar_movies(
        movie_id=movie['id'],
        n=3
    )
```

---

## ⚡ 性能优化建议

### 1. 缓存推荐结果

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedRecommender:
    def __init__(self, recommender):
        self.recommender = recommender
        self.cache = {}
        self.cache_ttl = timedelta(hours=1)
    
    def get_recommendations(self, user_id, n=10):
        cache_key = f"user_{user_id}_{n}"
        
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return result
        
        result = self.recommender.get_recommendations(user_id, n)
        self.cache[cache_key] = (result, datetime.now())
        return result
```

### 2. 批量预测

```python
# 为多个用户批量生成推荐
def batch_recommendations(user_ids, n=10):
    results = {}
    for user_id in user_ids:
        results[user_id] = recommender.get_recommendations(user_id, n)
    return results
```

### 3. 异步加载

```python
from concurrent.futures import ThreadPoolExecutor

def async_recommendations(user_id):
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 并行获取不同类型的推荐
        future_personal = executor.submit(
            recommender.get_recommendations, user_id, 10
        )
        future_popular = executor.submit(
            recommender.get_popular_recommendations, 10
        )
        
        return {
            'personal': future_personal.result(),
            'popular': future_popular.result()
        }
```

---

## 🎉 总结

你现在有了一个完整的推荐系统：

1. ✅ **步骤一**：数据准备（按用户分组划分）
2. ✅ **步骤二**：模型训练
   - ALS 协同过滤
   - 基于内容推荐
   - 混合推荐系统（RMSE 0.896）
3. ✅ **步骤三**：模型集成
   - 完整的推荐API
   - 多种推荐场景
   - Flask 集成示例

**测试命令：**
```bash
cd backend
python -m ml.recommender --user-id 1 --movie-id 1
```

**性能指标：**
- 测试集 RMSE: 0.896
- 评级：★★★★☆ 良好
- 混合权重：30% ALS + 70% 内容




