"""
初始化商品数据和 RBAC 权限数据
运行方式：python backend/seed/init_products.py
"""
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)

from app import app
from extensions import db
from models import User, Product, Category, ProductCategory, Role, Permission, UserRole, RolePermission
from werkzeug.security import generate_password_hash


def init_categories():
    """初始化商品品类"""
    categories = [
        "保温杯", "运动鞋", "手机", "耳机", "T恤", "鼠标",
        "键盘", "台灯", "书籍", "自行车"
    ]
    
    existing = {c.name for c in Category.query.all()}
    for name in categories:
        if name not in existing:
            db.session.add(Category(name=name))
    
    db.session.commit()
    print(f"✅ 已初始化 {len(categories)} 个品类")


def init_rbac():
    """初始化 RBAC 角色和权限"""
    # 创建权限
    permissions = [
        ("product:view", "查看商品"),
        ("product:publish", "发布商品"),
        ("product:edit", "编辑商品"),
        ("product:delete", "删除商品"),
        ("product:audit", "审核商品"),
        ("user:manage", "管理用户"),
        ("recommendation:query", "查询推荐"),
        ("admin:log", "查看操作日志"),
    ]
    
    perm_map = {}
    for name, desc in permissions:
        p = Permission.query.filter_by(name=name).first()
        if not p:
            p = Permission(name=name, description=desc)
            db.session.add(p)
        perm_map[name] = p
    
    db.session.commit()
    
    # 创建角色
    roles_config = {
        "normal_user": {
            "description": "普通用户",
            "permissions": ["product:view", "product:publish", "product:edit", "product:delete", "recommendation:query"]
        },
        "admin": {
            "description": "平台管理员",
            "permissions": ["product:view", "product:audit", "user:manage", "admin:log", "recommendation:query"]
        },
        "agent_service": {
            "description": "Agent服务账号",
            "permissions": ["product:view", "recommendation:query"]
        }
    }
    
    for role_name, config in roles_config.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=config["description"])
            db.session.add(role)
            db.session.commit()
        
        # 清空旧权限
        RolePermission.query.filter_by(role_id=role.id).delete()
        
        # 添加新权限
        for perm_name in config["permissions"]:
            if perm_name in perm_map:
                rp = RolePermission(role_id=role.id, permission_id=perm_map[perm_name].id)
                db.session.add(rp)
    
    db.session.commit()
    print(f"✅ 已初始化 {len(roles_config)} 个角色和 {len(permissions)} 个权限")


def init_users():
    """初始化测试用户"""
    users_data = [
        {"username": "testuser", "email": "test@example.com", "password": "123456", "user_type": "normal_user"},
        {"username": "admin", "email": "admin@example.com", "password": "admin123", "user_type": "admin"},
        {"username": "agent", "email": "agent@example.com", "password": "agent123", "user_type": "agent_service"},
    ]
    
    for data in users_data:
        user = User.query.filter_by(username=data["username"]).first()
        if not user:
            user = User(
                username=data["username"],
                email=data["email"],
                password_hash=generate_password_hash(data["password"]),
                user_type=data["user_type"]
            )
            db.session.add(user)
            db.session.commit()
            
            # 分配角色
            role = Role.query.filter_by(name=data["user_type"]).first()
            if role:
                ur = UserRole(user_id=user.id, role_id=role.id)
                db.session.add(ur)
    
    db.session.commit()
    print(f"✅ 已初始化 {len(users_data)} 个测试用户")


def init_products():
    """初始化商品数据"""
    # 获取测试用户
    seller = User.query.filter_by(username="testuser").first()
    if not seller:
        print("❌ 请先初始化用户")
        return
    
    # 获取品类
    categories = {c.name: c for c in Category.query.all()}
    
    products_data = [
        {"name": "保温杯 500ml 蓝色", "price": 35.0, "condition": "九成新", "category": "保温杯", "desc": "品牌保温杯，保温效果好，外观完好"},
        {"name": "耐克运动鞋 42码", "price": 180.0, "condition": "八成新", "category": "运动鞋", "desc": "正品耐克跑鞋，穿过几次，鞋底磨损轻微"},
        {"name": "iPhone 12 128G", "price": 2800.0, "condition": "九五新", "category": "手机", "desc": "自用iPhone，无磕碰，电池健康度92%"},
        {"name": "AirPods Pro", "price": 800.0, "condition": "全新", "category": "耳机", "desc": "闲置未拆封，官网购入"},
        {"name": "优衣库T恤 L码", "price": 25.0, "condition": "九成新", "category": "T恤", "desc": "纯棉T恤，洗过一次，基本全新"},
        {"name": "罗技 MX Master 3", "price": 320.0, "condition": "九成新", "category": "鼠标", "desc": "经典办公鼠标，功能完好"},
        {"name": "机械键盘青轴", "price": 150.0, "condition": "八成新", "category": "键盘", "desc": "樱桃青轴，键帽有轻微磨损"},
        {"name": "飞利浦护眼台灯", "price": 120.0, "condition": "九成新", "category": "台灯", "desc": "无频闪台灯，适合宿舍学习"},
        {"name": "算法导论（第三版）", "price": 45.0, "condition": "八成新", "category": "书籍", "desc": "经典算法教材，有笔记"},
        {"name": "捷安特山地车", "price": 600.0, "condition": "七成新", "category": "自行车", "desc": "21速山地车，车况良好"},
        {"name": "小米保温杯 白色", "price": 28.0, "condition": "全新", "category": "保温杯", "desc": "全新未使用，活动赠品"},
        {"name": "阿迪达斯运动鞋 40码", "price": 150.0, "condition": "九成新", "category": "运动鞋", "desc": "三叶草经典款，尺码偏小转让"},
        {"name": "小米11 256G", "price": 1500.0, "condition": "九成新", "category": "手机", "desc": "骁龙888，性能强劲，无暗病"},
        {"name": "索尼 WH-1000XM4", "price": 1200.0, "condition": "九五新", "category": "耳机", "desc": "降噪耳机天花板，配件齐全"},
        {"name": "Champion卫衣 XL", "price": 80.0, "condition": "九成新", "category": "T恤", "desc": "正品Champion，厚实保暖"},
        {"name": "雷蛇炼狱蝰蛇", "price": 180.0, "condition": "九成新", "category": "鼠标", "desc": "游戏鼠标，RGB灯效"},
        {"name": "HHKB键盘", "price": 800.0, "condition": "九五新", "category": "键盘", "desc": "程序员神器，静电容键盘"},
        {"name": "米家台灯 Pro", "price": 180.0, "condition": "全新", "category": "台灯", "desc": "智能台灯，支持米家APP"},
        {"name": "深入理解计算机系统", "price": 55.0, "condition": "九成新", "category": "书籍", "desc": "CSAPP，无笔记，几乎全新"},
        {"name": "永久折叠自行车", "price": 280.0, "condition": "八成新", "category": "自行车", "desc": "折叠便携，适合短途通勤"},
    ]
    
    existing_count = Product.query.count()
    if existing_count > 0:
        print(f"ℹ️  已有 {existing_count} 个商品，跳过初始化")
        return
    
    for data in products_data:
        product = Product(
            name=data["name"],
            description=data["desc"],
            price=data["price"],
            condition=data["condition"],
            status="approved",  # 已审核通过
            seller_id=seller.id
        )
        db.session.add(product)
        db.session.flush()
        
        # 关联品类
        if data["category"] in categories:
            pc = ProductCategory(product_id=product.id, category_id=categories[data["category"]].id)
            db.session.add(pc)
    
    db.session.commit()
    print(f"✅ 已初始化 {len(products_data)} 个商品")


def main():
    with app.app_context():
        print("🚀 开始初始化数据...")
        
        # 创建所有表
        db.create_all()
        print("✅ 数据库表已创建")
        
        # 初始化数据
        init_categories()
        init_rbac()
        init_users()
        init_products()
        
        print("\n🎉 数据初始化完成！")
        print("测试账号：")
        print("  普通用户: testuser / 123456")
        print("  管理员: admin / admin123")
        print("  Agent: agent / agent123")


if __name__ == "__main__":
    main()
