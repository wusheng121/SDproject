"""complex user agent actions

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa


revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversation_sessions", sa.Column("context_json", sa.Text(), nullable=True))

    op.create_table(
        "pending_actions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("session_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_actions_user_id", "pending_actions", ["user_id"])
    op.create_index("ix_pending_actions_session_id", "pending_actions", ["session_id"])
    op.create_index("ix_pending_actions_status", "pending_actions", ["status"])

    bind = op.get_bind()
    skills = (
        (
            "SK-005", "product_detail", "商品详情查询", "product",
            "读取商品详情、卖家信息和评价",
            '{"type":"object","properties":{"product_id":{"type":"integer"}},"required":["product_id"]}',
            '{"type":"object","properties":{"product":{},"reviews":{"type":"array"}}}',
            "product:view", "product_detail", "读取商品详情", "修改商品、删除商品",
        ),
        (
            "SK-006", "product_compare", "商品对比", "product",
            "对比多个商品的价格、成色、风险和性价比",
            '{"type":"object","properties":{"product_ids":{"type":"array","items":{"type":"integer"}}}}',
            '{"type":"object","properties":{"items":{"type":"array"},"recommendation":{"type":"string"}}}',
            "product:view", "product_compare", "读取商品并计算对比", "修改商品、下单",
        ),
        (
            "SK-007", "product_advice", "购买建议", "product",
            "根据商品信息生成购买建议、风险点和缺失信息",
            '{"type":"object","properties":{"product_id":{"type":"integer"}},"required":["product_id"]}',
            '{"type":"object","properties":{"summary":{"type":"string"},"pros":{"type":"array"},"risks":{"type":"array"}}}',
            "product:view", "product_advice", "读取商品并生成建议", "编造商品参数、替用户下单",
        ),
        (
            "SK-008", "seller_questions", "卖家提问", "product",
            "生成向卖家确认商品情况的问题和沟通话术",
            '{"type":"object","properties":{"product_id":{"type":"integer"}},"required":["product_id"]}',
            '{"type":"object","properties":{"questions":{"type":"array"},"script":{"type":"string"}}}',
            "product:view", "seller_questions", "生成问题草稿", "自动发送消息",
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

    for skill_code in ("product_detail", "product_compare", "product_advice", "seller_questions"):
        bind.execute(
            sa.text(
                """
                INSERT INTO agent_skills (agent_id, skill_id, enabled, priority, created_at)
                SELECT a.id, s.id, 1, 100, CURRENT_TIMESTAMP
                FROM agents a, skills s
                WHERE a.code = 'product_agent' AND s.code = :skill_code
                  AND NOT EXISTS (
                    SELECT 1 FROM agent_skills x
                    WHERE x.agent_id = a.id AND x.skill_id = s.id
                  )
                """
            ),
            {"skill_code": skill_code},
        )


def downgrade():
    bind = op.get_bind()
    for code in ("product_detail", "product_compare", "product_advice", "seller_questions"):
        bind.execute(
            sa.text(
                """
                DELETE FROM agent_skills
                WHERE skill_id IN (SELECT id FROM skills WHERE code = :code)
                """
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM skills WHERE code = :code"), {"code": code})

    op.drop_index("ix_pending_actions_status", table_name="pending_actions")
    op.drop_index("ix_pending_actions_session_id", table_name="pending_actions")
    op.drop_index("ix_pending_actions_user_id", table_name="pending_actions")
    op.drop_table("pending_actions")
    op.drop_column("conversation_sessions", "context_json")
