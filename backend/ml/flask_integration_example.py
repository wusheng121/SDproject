"""
在 Flask 应用中集成推荐系统的示例

使用方法：
1. 在 app.py 中初始化推荐系统
2. 在路由中调用推荐接口
"""

from flask import Flask, jsonify, request
from ml.recommender import Recommender

app = Flask(__name__)

# 全局推荐系统实例（应用启动时初始化一次）
recommender = None


def init_recommender():
    """初始化推荐系统（在应用启动时调用）"""
    global recommender
    recommender = Recommender(
        hybrid_model_path='./data/output5/hybrid_model.pkl',
        movies_path='./data/ml-latest-small/movies.csv',
        ratings_path='./data/output1/ratings_train.csv'
    )
    print("推荐系统已初始化")


# 方式1：在应用启动时初始化
@app.before_first_request
def setup():
    init_recommender()


# API 示例1：个性化推荐
@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """
    GET /api/recommendations?user_id=1&n=10&diversity=true
    
    返回：
    {
      "code": 0,
      "message": "ok",
      "data": {
        "user_id": 1,
        "recommendations": [
          {
            "movie_id": 123,
            "title": "Toy Story (1995)",
            "predicted_rating": 4.5,
            "genres": "Animation|Children|Comedy",
            "avg_rating": 3.9,
            "rating_count": 247
          },
          ...
        ]
      }
    }
    """
    try:
        user_id = int(request.args.get('user_id', 0))
        n = int(request.args.get('n', 10))
        diversity = request.args.get('diversity', 'false').lower() == 'true'
        
        if user_id <= 0:
            return jsonify({
                "code": 400,
                "message": "user_id is required",
                "data": None
            }), 400
        
        recommendations = recommender.get_recommendations(
            user_id=user_id,
            n=n,
            diversity=diversity
        )
        
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": {
                "user_id": user_id,
                "count": len(recommendations),
                "recommendations": recommendations
            }
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e),
            "data": None
        }), 500


# API 示例2：热门推荐（冷启动）
@app.route('/api/recommendations/popular', methods=['GET'])
def get_popular():
    """
    GET /api/recommendations/popular?n=10
    
    返回热门电影列表
    """
    try:
        n = int(request.args.get('n', 10))
        
        popular = recommender.get_popular_recommendations(n=n)
        
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": {
                "count": len(popular),
                "recommendations": popular
            }
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e),
            "data": None
        }), 500


# API 示例3：相似电影推荐
@app.route('/api/recommendations/similar/<int:movie_id>', methods=['GET'])
def get_similar(movie_id):
    """
    GET /api/recommendations/similar/1?n=10
    
    返回与指定电影相似的电影列表
    """
    try:
        n = int(request.args.get('n', 10))
        
        similar = recommender.get_similar_movies(movie_id=movie_id, n=n)
        
        if not similar:
            return jsonify({
                "code": 404,
                "message": "Movie not found",
                "data": None
            }), 404
        
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": {
                "movie_id": movie_id,
                "count": len(similar),
                "recommendations": similar
            }
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e),
            "data": None
        }), 500


# API 示例4：模型信息
@app.route('/api/recommendations/info', methods=['GET'])
def get_model_info():
    """
    GET /api/recommendations/info
    
    返回推荐系统模型信息
    """
    try:
        info = recommender.get_model_info()
        
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": info
        })
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e),
            "data": None
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)





