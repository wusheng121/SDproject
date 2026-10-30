from datetime import datetime

from sqlalchemy import Index, UniqueConstraint

from extensions import db

ID_TYPE = db.BigInteger().with_variant(db.Integer, "sqlite")


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    email_normalized = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    user_type = db.Column(db.String(20), default="normal_user", nullable=False, index=True)
    phone_ciphertext = db.Column(db.Text, nullable=True)
    phone_hash = db.Column(db.String(64), unique=True, index=True, nullable=True)
    preferred_categories = db.Column(db.Text, nullable=True)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.Integer, default=1, nullable=False)

    published_products = db.relationship(
        "Product", back_populates="seller", cascade="all, delete-orphan"
    )
    behaviors = db.relationship("UserBehavior", back_populates="user", cascade="all, delete-orphan")
    user_roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    sessions = db.relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = db.relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

    def get_preferred_categories_list(self):
        if not self.preferred_categories:
            return []
        return [c.strip() for c in self.preferred_categories.split(",") if c.strip()]

    def set_preferred_categories_list(self, category_list):
        self.preferred_categories = ",".join(c.strip() for c in category_list if c.strip())

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    user_roles = db.relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = db.relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, index=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    role_permissions = db.relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )


class UserRole(db.Model):
    __tablename__ = "user_roles"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = db.Column(db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user = db.relationship("User", back_populates="user_roles")
    role = db.relationship("Role", back_populates="user_roles")


class RolePermission(db.Model):
    __tablename__ = "role_permissions"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    role_id = db.Column(db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = db.Column(
        db.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    role = db.relationship("Role", back_populates="role_permissions")
    permission = db.relationship("Permission", back_populates="role_permissions")


class AuthSession(db.Model):
    __tablename__ = "auth_sessions"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    family_id = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="sessions")


class ApiKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    key_prefix = db.Column(db.String(16), unique=True, nullable=False, index=True)
    key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    scopes = db.Column(db.Text, nullable=False, default="")
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="api_keys")

    def scope_set(self):
        return {s.strip() for s in (self.scopes or "").split(",") if s.strip()}


class EmailVerificationToken(db.Model):
    __tablename__ = "email_verification_tokens"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class OperationLog(db.Model):
    __tablename__ = "operation_logs"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    actor_id = db.Column(
        db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_snapshot = db.Column(db.String(200), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(64), nullable=True, index=True)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    trace_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("ix_operation_logs_resource", "resource_type", "resource_id"),)


class Product(db.Model, TimestampMixin):
    __tablename__ = "products"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), index=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False, index=True)
    condition = db.Column("condition_level", db.String(20), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    has_notes = db.Column(db.Boolean, nullable=False, default=False)
    defect_description = db.Column(db.String(500), nullable=True)
    trade_method = db.Column(db.String(30), nullable=True)
    trade_location = db.Column(db.String(200), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    ai_category = db.Column(db.String(50), nullable=True)
    ai_condition = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    seller_id = db.Column(
        db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    seller = db.relationship("User", back_populates="published_products")
    categories = db.relationship(
        "ProductCategory", back_populates="product", cascade="all, delete-orphan"
    )
    behaviors = db.relationship(
        "UserBehavior", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending','approved','rejected','sold','offline')",
            name="ck_products_status",
        ),
    )


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    products = db.relationship(
        "ProductCategory", back_populates="category", cascade="all, delete-orphan"
    )


class ProductCategory(db.Model):
    __tablename__ = "product_categories"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    product_id = db.Column(
        db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id = db.Column(
        db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (UniqueConstraint("product_id", "category_id", name="uq_product_category"),)

    product = db.relationship("Product", back_populates="categories")
    category = db.relationship("Category", back_populates="products")


class UserBehavior(db.Model, TimestampMixin):
    __tablename__ = "user_behaviors"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(
        db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    behavior_type = db.Column(db.String(20), nullable=False, index=True)
    value = db.Column(db.Integer, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="behaviors")
    product = db.relationship("Product", back_populates="behaviors")

    __table_args__ = (
        Index("ix_user_behaviors_user_type", "user_id", "behavior_type"),
        Index("ix_user_behaviors_product_type", "product_id", "behavior_type"),
    )


class BehaviorEvent(db.Model):
    __tablename__ = "behavior_events"

    WEIGHTS = {"view": 1, "favorite": 3, "add_cart": 4}

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    behavior_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    product = db.relationship("Product")

    __table_args__ = (Index("ix_behavior_events_user_time", "user_id", "created_at"),)

    @classmethod
    def recent(cls, now=None):
        from datetime import timedelta

        now = now or datetime.utcnow()
        return cls.query.filter(
            cls.created_at >= now - timedelta(days=7),
            cls.created_at <= now,
            cls.behavior_type.in_(cls.WEIGHTS),
        )


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(
        db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),)


class Order(db.Model, TimestampMixin):
    __tablename__ = "orders"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    buyer_id = db.Column(
        db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False, default=0)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    order_id = db.Column(
        db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = db.Column(
        db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AgentDialogue(db.Model):
    """用户与只读 Agent 的多轮会话。slots 保存追问时沿用的筛选条件。"""

    __tablename__ = "agent_dialogues"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slots_json = db.Column(db.Text, nullable=False, default="{}")
    messages_json = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(
        db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id = db.Column(
        db.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        db.CheckConstraint("score >= 1 AND score <= 5", name="ck_reviews_score"),
        UniqueConstraint("user_id", "product_id", "order_id", name="uq_review_user_product_order"),
    )
