from datetime import datetime

from extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    # 用户类型：normal_user(普通用户), admin(管理员), agent_service(Agent服务账号)
    user_type = db.Column(db.String(20), default="normal_user", nullable=False, index=True)
    # 手机号 TODO: 需要脱敏处理
    phone = db.Column(db.String(20), nullable=True)
    # 用户兴趣标签（逗号分隔的品类名称，如 "保温杯,运动鞋"）
    preferred_categories = db.Column(db.Text, nullable=True)

    # 关系
    published_products = db.relationship("Product", back_populates="seller", cascade="all, delete-orphan")
    behaviors = db.relationship("UserBehavior", back_populates="user", cascade="all, delete-orphan")
    user_roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    def get_preferred_categories_list(self):
        """返回偏好品类列表"""
        if not self.preferred_categories:
            return []
        return [c.strip() for c in self.preferred_categories.split(",") if c.strip()]

    def set_preferred_categories_list(self, category_list):
        """设置偏好品类列表"""
        if not category_list:
            self.preferred_categories = ""
        else:
            self.preferred_categories = ",".join([c.strip() for c in category_list if c.strip()])


class Product(db.Model, TimestampMixin):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), index=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False, index=True)
    condition = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    seller = db.relationship("User", back_populates="published_products")
    categories = db.relationship("ProductCategory", back_populates="product", cascade="all, delete-orphan")
    behaviors = db.relationship("UserBehavior", back_populates="product", cascade="all, delete-orphan")


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)

    products = db.relationship("ProductCategory", back_populates="category", cascade="all, delete-orphan")


class ProductCategory(db.Model):
    __tablename__ = "product_categories"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("product_id", "category_id", name="uq_product_category"),
    )

    product = db.relationship("Product", back_populates="categories")
    category = db.relationship("Category", back_populates="products")


class UserBehavior(db.Model, TimestampMixin):
    __tablename__ = "user_behaviors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    behavior_type = db.Column(db.String(20), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", back_populates="behaviors")
    product = db.relationship("Product", back_populates="behaviors")


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    user_roles = db.relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = db.relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, index=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    role_permissions = db.relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class UserRole(db.Model):
    __tablename__ = "user_roles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    user = db.relationship("User", back_populates="user_roles")
    role = db.relationship("Role", back_populates="user_roles")


class RolePermission(db.Model):
    __tablename__ = "role_permissions"

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role = db.relationship("Role", back_populates="role_permissions")
    permission = db.relationship("Permission", back_populates="role_permissions")








