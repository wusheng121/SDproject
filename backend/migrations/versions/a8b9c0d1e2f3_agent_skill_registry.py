"""agent skill registry

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agents",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("agent_type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_agents_code"),
    )
    op.create_index("ix_agents_agent_type", "agents", ["agent_type"])
    op.create_index("ix_agents_status", "agents", ["status"])

    op.create_table(
        "skills",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("skill_no", sa.String(length=32), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("input_schema_json", sa.Text(), nullable=True),
        sa.Column("output_schema_json", sa.Text(), nullable=True),
        sa.Column("allowed_operations", sa.String(length=500), nullable=True),
        sa.Column("forbidden_operations", sa.String(length=500), nullable=True),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("handler_type", sa.String(length=20), nullable=False, server_default="java"),
        sa.Column("handler_target", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_skills_code"),
    )
    op.create_index("ix_skills_module", "skills", ["module"])
    op.create_index("ix_skills_status", "skills", ["status"])
    op.create_index("ix_skills_scope", "skills", ["scope"])

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("skill_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "skill_id", name="uq_agent_skills_agent_skill"),
    )
    op.create_index("ix_agent_skills_agent_id", "agent_skills", ["agent_id"])
    op.create_index("ix_agent_skills_skill_id", "agent_skills", ["skill_id"])

    bind = op.get_bind()

    for name, description in (
        ("skill:view", "查看 Skill"),
        ("skill:manage", "管理 Skill"),
        ("skill:test", "测试 Skill"),
    ):
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (name, description)
                SELECT :name, :description
                WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = :name)
                """
            ),
            {"name": name, "description": description},
        )

    for permission in ("skill:view", "skill:manage", "skill:test"):
        bind.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = 'admin' AND p.name = :permission
                  AND NOT EXISTS (
                    SELECT 1 FROM role_permissions rp
                    WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  )
                """
            ),
            {"permission": permission},
        )

    agents = (
        ("main_agent", "主 Agent", "main", "意图识别、任务拆解与子 Agent 路由", "deepseek-flash"),
        ("product_agent", "商品 Agent", "sub", "商品查询、自然语言筛选与识图", "deepseek-flash"),
        ("recommendation_agent", "推荐 Agent", "sub", "个性化推荐与相似商品", "deepseek-flash"),
        ("trade_agent", "交易 Agent", "sub", "购物车、订单与交易状态查询", "deepseek-flash"),
        ("user_agent", "用户 Agent", "sub", "用户资料与偏好查询", "deepseek-flash"),
        ("admin_read_agent", "管理只读 Agent", "sub", "待审核商品与审计日志只读查询", "deepseek-flash"),
    )
    for code, name, agent_type, description, model in agents:
        bind.execute(
            sa.text(
                """
                INSERT INTO agents (code, name, agent_type, description, model, status, created_at, updated_at)
                SELECT :code, :name, :agent_type, :description, :model, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM agents WHERE code = :code)
                """
            ),
            {
                "code": code,
                "name": name,
                "agent_type": agent_type,
                "description": description,
                "model": model,
            },
        )

    skills = (
        (
            "SK-001",
            "product_query",
            "商品信息查询",
            "product",
            "查询已上架商品列表",
            '{"type":"object","properties":{"category":{"type":"string"},"condition":{"type":"string"},"min_price":{"type":"number"},"max_price":{"type":"number"}}}',
            '{"type":"object","properties":{"items":{"type":"array"}}}',
            "product:view",
            "product_query",
            "读取商品列表",
            "修改商品、删除商品、批量改价",
        ),
        (
            "SK-002",
            "nl_filter",
            "自然语言筛选",
            "product",
            "从自然语言条件中提取分类、成色和价格区间并查询商品",
            '{"type":"object","properties":{"text":{"type":"string"},"category":{"type":"string"},"condition":{"type":"string"},"min_price":{"type":"number"},"max_price":{"type":"number"}}}',
            '{"type":"object","properties":{"items":{"type":"array"}}}',
            "product:view",
            "nl_filter",
            "读取商品列表",
            "修改商品、删除商品、执行任意 SQL",
        ),
        (
            "SK-003",
            "recommendation_query",
            "个性化推荐查询",
            "recommendation",
            "查询用户推荐商品",
            '{"type":"object","properties":{"user_id":{"type":"integer"},"limit":{"type":"integer"}}}',
            '{"type":"object","properties":{"items":{"type":"array"},"strategy":{"type":"string"}}}',
            "recommendation:query",
            "recommendation_query",
            "读取推荐结果",
            "修改用户偏好、写入行为数据",
        ),
        (
            "SK-004",
            "product_recognize",
            "商品图片识别",
            "product",
            "根据图片识别商品关键词与分类",
            '{"type":"object","properties":{"image_base64":{"type":"string"},"mime":{"type":"string"}},"required":["image_base64"]}',
            '{"type":"object","properties":{"keywords":{"type":"array"},"category":{"type":"string"}}}',
            "product:view",
            "product_recognize",
            "读取图片识别结果",
            "修改商品、上传文件、保存图片",
        ),
    )
    for skill_no, code, name, module, description, input_schema, output_schema, scope, handler, allowed, forbidden in skills:
        bind.execute(
            sa.text(
                """
                INSERT INTO skills (
                    skill_no, code, name, module, description, input_schema_json,
                    output_schema_json, allowed_operations, forbidden_operations, scope,
                    handler_type, handler_target, status, version, created_at, updated_at
                )
                SELECT :skill_no, :code, :name, :module, :description, :input_schema,
                       :output_schema, :allowed, :forbidden, :scope,
                       'java', :handler, 'published', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM skills WHERE code = :code)
                """
            ),
            {
                "skill_no": skill_no,
                "code": code,
                "name": name,
                "module": module,
                "description": description,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "allowed": allowed,
                "forbidden": forbidden,
                "scope": scope,
                "handler": handler,
            },
        )

    for agent_code, skill_codes in (
        ("product_agent", ("product_query", "nl_filter", "product_recognize")),
        ("recommendation_agent", ("recommendation_query",)),
    ):
        for skill_code in skill_codes:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO agent_skills (agent_id, skill_id, enabled, priority, created_at)
                    SELECT a.id, s.id, 1, 100, CURRENT_TIMESTAMP
                    FROM agents a, skills s
                    WHERE a.code = :agent_code AND s.code = :skill_code
                      AND NOT EXISTS (
                        SELECT 1 FROM agent_skills x
                        WHERE x.agent_id = a.id AND x.skill_id = s.id
                      )
                    """
                ),
                {"agent_code": agent_code, "skill_code": skill_code},
            )


def downgrade():
    op.drop_index("ix_agent_skills_skill_id", table_name="agent_skills")
    op.drop_index("ix_agent_skills_agent_id", table_name="agent_skills")
    op.drop_table("agent_skills")

    op.drop_index("ix_skills_scope", table_name="skills")
    op.drop_index("ix_skills_status", table_name="skills")
    op.drop_index("ix_skills_module", table_name="skills")
    op.drop_table("skills")

    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_agent_type", table_name="agents")
    op.drop_table("agents")

    bind = op.get_bind()
    for permission in ("skill:view", "skill:manage", "skill:test"):
        bind.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (SELECT id FROM permissions WHERE name = :permission)
                """
            ),
            {"permission": permission},
        )
        bind.execute(sa.text("DELETE FROM permissions WHERE name = :permission"), {"permission": permission})
