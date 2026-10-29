from datetime import datetime

from flask import current_app

from extensions import db
from models import (
    Category,
    Permission,
    Product,
    ProductCategory,
    Role,
    RolePermission,
    User,
    UserRole,
)
from utils.security import hash_password

PERMISSIONS = [
    ("product:view", "查看商品"),
    ("product:publish", "发布商品"),
    ("product:edit", "编辑商品"),
    ("product:delete", "删除商品"),
    ("product:audit", "审核/下架商品"),
    ("user:manage", "管理用户"),
    ("recommendation:query", "查询推荐"),
    ("behavior:write", "记录用户行为"),
    ("order:create", "创建订单"),
    ("review:write", "提交评价"),
    ("admin:log", "查看操作日志"),
    ("admin:stats", "查看平台统计"),
]

ROLES = {
    "normal_user": {
        "description": "普通用户",
        "permissions": [
            "product:view",
            "product:publish",
            "product:edit",
            "product:delete",
            "recommendation:query",
            "behavior:write",
            "order:create",
            "review:write",
        ],
    },
    "admin": {
        "description": "平台管理员",
        "permissions": [
            "product:view",
            "product:audit",
            "user:manage",
            "recommendation:query",
            "admin:log",
            "admin:stats",
        ],
    },
    "agent_service": {
        "description": "Agent 服务账号",
        "permissions": ["product:view", "recommendation:query"],
    },
}

CATEGORIES = [
    "保温杯",
    "运动鞋",
    "手机",
    "耳机",
    "T恤",
    "鼠标",
    "键盘",
    "台灯",
    "书籍",
    "自行车",
    "平板",
    "相机",
    "音箱",
    "游戏机",
    "显示器",
    "充电宝",
    "外套",
    "裤子",
    "背包",
    "行李箱",
    "篮球",
    "羽毛球拍",
    "吉他",
    "护肤品",
    "收纳盒",
    "小风扇",
    "电饭煲",
    "吹风机",
    "插线板",
    "学习桌",
    "椅子",
]

PRODUCTS = [
    ("保温杯 500ml 蓝色", "品牌保温杯，保温效果好", 35.0, "九成新", "保温杯"),
    ("耐克运动鞋 42码", "正品耐克跑鞋", 180.0, "八成新", "运动鞋"),
    ("iPhone 12 128G", "自用 iPhone，无磕碰", 2800.0, "九五新", "手机"),
    ("AirPods Pro", "闲置未拆封", 800.0, "全新", "耳机"),
    ("优衣库 T恤 L码", "纯棉 T恤", 25.0, "九成新", "T恤"),
    ("罗技 MX Master 3", "经典办公鼠标", 320.0, "九成新", "鼠标"),
    ("机械键盘青轴", "樱桃青轴", 150.0, "八成新", "键盘"),
    ("飞利浦护眼台灯", "无频闪台灯", 120.0, "九成新", "台灯"),
    ("算法导论（第三版）", "经典算法教材", 45.0, "八成新", "书籍"),
    ("捷安特山地车", "21 速山地车", 600.0, "七成新", "自行车"),
    ("iPad 9 64G", "上网课用，屏幕无划痕，附保护壳", 1800.0, "九成新", "平板"),
    ("小米平板 5", "6+128G，看视频和记笔记都很流畅", 950.0, "八成新", "平板"),
    ("索尼 A6000 微单", "套机 16-50mm，快门数不高", 2200.0, "九成新", "相机"),
    ("佳能 50mm 定焦镜头", "f/1.8 小痰盂，成色好", 600.0, "八成新", "相机"),
    ("JBL 蓝牙音箱", "音质不错，续航正常", 180.0, "九成新", "音箱"),
    ("小爱音箱 mini", "宿舍用，功能正常", 60.0, "八成新", "音箱"),
    ("Switch OLED", "白色款，含底座和手柄", 1500.0, "九五新", "游戏机"),
    ("PS4 Slim 500G", "含一个原装手柄，可试机", 1100.0, "八成新", "游戏机"),
    ("戴尔 24 寸显示器", "1080P IPS，办公学习够用", 500.0, "九成新", "显示器"),
    ("小米 27 寸显示器", "2K 分辨率，轻微使用痕迹", 800.0, "九成新", "显示器"),
    ("罗马仕 20000mAh 充电宝", "大容量，支持双向快充", 70.0, "九成新", "充电宝"),
    ("安克 65W 氮化镓充电器", "小巧便携，可充笔记本", 90.0, "九成新", "充电宝"),
    ("北面冲锋衣 L码", "防风防水，适合秋季", 350.0, "九成新", "外套"),
    ("优衣库羽绒服 M码", "轻便保暖，无破损", 200.0, "八成新", "外套"),
    ("李维斯牛仔裤 32码", "经典 501 版型", 120.0, "九成新", "裤子"),
    ("耐克运动短裤 L码", "速干面料，适合跑步", 40.0, "八成新", "裤子"),
    ("耐克双肩包", "可放 15 寸电脑，容量大", 150.0, "九成新", "背包"),
    ("小米旅行箱 24 寸", "万向轮顺滑，密码锁正常", 220.0, "八成新", "行李箱"),
    ("斯伯丁篮球", "7 号球，室内外可用", 80.0, "九成新", "篮球"),
    ("尤尼克斯羽毛球拍", "碳素拍，送手胶", 260.0, "九成新", "羽毛球拍"),
    ("雅马哈民谣吉他", "41 寸，适合入门", 450.0, "八成新", "吉他"),
    ("兰蔻粉水 400ml", "全新未开封，专柜购入", 180.0, "全新", "护肤品"),
    ("珂润面霜 40g", "敏感肌适用，剩余九成", 90.0, "九成新", "护肤品"),
    ("无印良品收纳盒", "桌面收纳，带盖", 30.0, "九成新", "收纳盒"),
    ("宿舍静音小风扇", "USB 供电，夜间不扰民", 35.0, "八成新", "小风扇"),
    ("美的电饭煲 3L", "适合 2-4 人，内胆完好", 100.0, "九成新", "电饭煲"),
    ("飞科吹风机", "大功率，冷热风正常", 60.0, "九成新", "吹风机"),
    ("公牛插线板 5 位", "带独立开关，线长 3 米", 25.0, "九成新", "插线板"),
    ("宜家学习桌", "120x60cm，可折叠", 150.0, "八成新", "学习桌"),
    ("人体工学椅", "带腰托，宿舍自习用", 260.0, "八成新", "椅子"),
    ("罗技 K380 蓝牙键盘", "可连三台设备，便携", 120.0, "九成新", "键盘"),
    ("索尼 WH-1000XM4", "降噪耳机，配件齐全", 1200.0, "九五新", "耳机"),
    ("小米 13 256G", "骁龙 8 Gen2，无拆修", 1800.0, "九成新", "手机"),
    ("阿迪达斯运动鞋 40码", "三叶草经典款，尺码偏小", 150.0, "九成新", "运动鞋"),
    ("象印保温杯 350ml", "保温效果好，杯身无磕碰", 90.0, "九成新", "保温杯"),
    ("三体全集", "三册齐全，无笔记", 60.0, "九成新", "书籍"),
    ("迪卡侬公路车", "适合通勤，刚做过保养", 900.0, "八成新", "自行车"),
]


def seed_rbac():
    perm_map = {}
    for name, description in PERMISSIONS:
        permission = Permission.query.filter_by(name=name).first()
        if not permission:
            permission = Permission(name=name, description=description)
            db.session.add(permission)
            db.session.flush()
        perm_map[name] = permission

    for role_name, config in ROLES.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=config["description"])
            db.session.add(role)
            db.session.flush()
        RolePermission.query.filter_by(role_id=role.id).delete()
        for permission_name in config["permissions"]:
            db.session.add(
                RolePermission(role_id=role.id, permission_id=perm_map[permission_name].id)
            )
    db.session.commit()


def seed_categories():
    for name in CATEGORIES:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
    db.session.commit()


def _upsert_user(username, email, password, user_type, verified=True):
    email = email.lower()
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            username=username,
            email=email,
            email_normalized=email,
            password_hash=hash_password(password),
            user_type=user_type,
            email_verified_at=datetime.utcnow() if verified else None,
        )
        db.session.add(user)
        db.session.flush()
    role = Role.query.filter_by(name=user_type).first()
    if role and not UserRole.query.filter_by(user_id=user.id, role_id=role.id).first():
        db.session.add(UserRole(user_id=user.id, role_id=role.id))
    return user


def seed_users():
    _upsert_user("testuser", "test@example.com", "Test12345", "normal_user")
    _upsert_user("admin", "admin@example.com", "Admin12345", "admin")
    _upsert_user("agent", "agent@example.com", "Agent12345", "agent_service")
    db.session.commit()


def seed_products():
    seller = User.query.filter_by(username="testuser").first()
    if not seller:
        return
    categories = {category.name: category for category in Category.query.all()}
    added = 0
    for name, description, price, condition, category_name in PRODUCTS:
        product = Product.query.filter_by(name=name).first()
        if not product:
            product = Product(
                name=name,
                description=description,
                price=price,
                condition=condition,
                status="approved",
                seller_id=seller.id,
            )
            db.session.add(product)
            db.session.flush()
            added += 1
        category = categories.get(category_name)
        if category and not ProductCategory.query.filter_by(
            product_id=product.id, category_id=category.id
        ).first():
            db.session.add(
                ProductCategory(product_id=product.id, category_id=category.id)
            )
    db.session.commit()
    print(f"Products seeded: {added} added, {Product.query.count()} total")


def seed_all():
    if current_app.config.get("APP_ENV") == "production":
        raise RuntimeError("Demo seed is disabled in production")
    seed_rbac()
    seed_categories()
    seed_users()
    seed_products()
    print("Demo data seeded: testuser / admin / agent")
