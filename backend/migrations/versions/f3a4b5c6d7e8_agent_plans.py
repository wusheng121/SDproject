"""agent plans and action message links

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_plans",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="executing"),
        sa.Column("steps_json", sa.Text(), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_plans_session_id", "agent_plans", ["session_id"])
    op.create_index("ix_agent_plans_user_id", "agent_plans", ["user_id"])
    op.create_index("ix_agent_plans_status", "agent_plans", ["status"])

    op.add_column(
        "pending_actions",
        sa.Column("message_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
    )
    op.add_column(
        "pending_actions",
        sa.Column("plan_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
    )
    op.create_index("ix_pending_actions_message_id", "pending_actions", ["message_id"])
    op.create_index("ix_pending_actions_plan_id", "pending_actions", ["plan_id"])


def downgrade():
    op.drop_index("ix_pending_actions_plan_id", table_name="pending_actions")
    op.drop_index("ix_pending_actions_message_id", table_name="pending_actions")
    op.drop_column("pending_actions", "plan_id")
    op.drop_column("pending_actions", "message_id")

    op.drop_index("ix_agent_plans_status", table_name="agent_plans")
    op.drop_index("ix_agent_plans_user_id", table_name="agent_plans")
    op.drop_index("ix_agent_plans_session_id", table_name="agent_plans")
    op.drop_table("agent_plans")
