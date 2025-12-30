**1. 项目基本信息**
```
项目名称：电影推荐系统 (Movie Recommendation System)
项目类型：Web应用 (B/S架构)
技术栈：
- 后端：Python Flask
- 前端：Vue 3 + Element Plus UI 库
- 数据库：SQLite (开发环境) / MySQL (生产环境)
- 版本控制：Git
```

**2. 核心功能模块 (对应7个页面)**
将实验要求的7个页面，映射到你的电影系统中：
1.  **首页(Home)**：网站介绍、导航栏、热门/推荐电影海报轮播。
2.  **搜索页(Search)**：可按电影**标题、类型、演员**搜索，结果以卡片列表展示。
3.  **电影详情页(Info)**：展示电影详情（标题、海报、简介、演员、类型、评分）。
4.  **用户注册页(Register)**：用户名、邮箱、密码。
5.  **用户登录页(Login)**：用户名/邮箱、密码，“记住我”选项。
6.  **个人收藏夹/列表页(Favorites)**：替代“购物篮”，显示用户想看的电影列表，可移除。
7.  **评分/反馈页(Rate)**：替代“结算页”，用户对看过的电影进行1-5星评分并提交。

**3. 数据库ER图核心实体与关系 (用文字描述)**
```
实体（建议更规范化，便于扩展与查询优化）：

- 用户(User)
  - 字段：id, username(唯一), email(唯一), password_hash, created_at, last_login_at
  - 说明：username/email 建议加唯一索引；密码仅存 hash

- 电影(Movie)
  - 字段：id, title, description, release_year, poster_url, created_at
  - 说明：title 建议索引；poster_url 可为空

- 类型(Genre)
  - 字段：id, name(唯一)

- 演员(Actor)
  - 字段：id, name(唯一)

- 电影-类型关联(MovieGenre)（多对多）
  - 字段：id, movie_id, genre_id
  - 约束：movie_id + genre_id 唯一

- 电影-演员关联(MovieActor)（多对多）
  - 字段：id, movie_id, actor_id
  - 约束：movie_id + actor_id 唯一

- 收藏(Favorite)
  - 字段：id, user_id, movie_id, created_at
  - 约束：user_id + movie_id 唯一（同一用户不能重复收藏）

- 评分(Rating)
  - 字段：id, user_id, movie_id, score(1-5), comment(可选), created_at, updated_at
  - 约束：user_id + movie_id 唯一（同一用户对同一电影最多一条评分，可更新）

关系：
- User 1..N Favorite，Movie 1..N Favorite
- User 1..N Rating，Movie 1..N Rating
- Movie N..N Genre（通过 MovieGenre）
- Movie N..N Actor（通过 MovieActor）

推荐查询常用索引建议：
- Movie(title), Movie(release_year)
- Favorite(user_id), Rating(user_id), Rating(movie_id)
- MovieGenre(movie_id), MovieActor(movie_id)
```

**4. 关键API接口设计 (RESTful风格)**
说明（建议统一响应结构，便于前后端对接与调试）：
- 统一响应：`{ "code": 0, "message": "ok", "data": ... }`
- 统一错误：`{ "code": <非0>, "message": "错误原因", "data": null }`
- 鉴权方式（建议）：登录后返回 JWT，后续请求带 `Authorization: Bearer <token>`

请为以下 API 生成路由与控制器骨架（可返回模拟 JSON 数据）：
```
# 用户相关
POST   /api/register    # 注册
POST   /api/login       # 登录
GET    /api/user/profile # 获取用户信息

# 电影相关
GET    /api/movies      # 获取电影列表（分页、筛选）
                      # query: page=1&page_size=12&genre=Action&year=2020&sort=hot|new|rating
GET    /api/movies/:id  # 获取电影详情（含演员/类型/平均分）
GET    /api/movies/search?q=xxx # 搜索电影

# 交互相关
POST   /api/action/favorite  # 收藏/取消收藏电影
POST   /api/action/rate      # 为电影评分
GET    /api/recommendations  # 获取给当前用户的推荐列表
```

**5. 项目目录结构期望**
建议目录（更贴近工程实践，便于后续分层与扩展）：
```
movie-recommendation/
├── backend/
│   ├── app.py              # Flask 应用入口（create_app + 运行）
│   ├── config.py           # 配置（SQLite 路径、调试、密钥等）
│   ├── extensions.py       # db/cors 等扩展初始化
│   ├── models.py           # SQLAlchemy 模型
│   ├── routes/             # API 蓝图
│   │   ├── __init__.py
│   │   ├── user_routes.py
│   │   ├── movie_routes.py
│   │   └── action_routes.py
│   ├── services/           # 业务逻辑（推荐、搜索策略等）
│   │   └── recommendation_service.py
│   ├── seed/               # 可选：初始化测试数据脚本
│   ├── instance/           # SQLite 数据库默认放这里（不提交到 git）
│   └── requirements.txt    # Python 依赖
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── public/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── views/          # 7 个页面
│   │   ├── components/     # 可复用组件（MovieCard 等）
│   │   ├── router/         # Vue Router
│   │   ├── stores/         # Pinia
│   │   └── api/            # axios 封装
│   └── package.json        # 前端依赖
├── README.md           # 项目说明、本地运行指南
└── .gitignore          # Git忽略文件
```

