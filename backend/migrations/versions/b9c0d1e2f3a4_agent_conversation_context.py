"""agent conversation context

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa


revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("agent_code", sa.String(length=64), nullable=False, server_default="main_agent"),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("token_budget", sa.Integer(), nullable=False, server_default="6000"),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_sessions_user_id", "conversation_sessions", ["user_id"])
    op.create_index("ix_conversation_sessions_agent_code", "conversation_sessions", ["agent_code"])
    op.create_index("ix_conversation_sessions_last_message_at", "conversation_sessions", ["last_message_at"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=20), nullable=False, server_default="text"),
        sa.Column("agent_code", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_messages_session_id", "conversation_messages", ["session_id"])
    op.create_index("ix_conversation_messages_trace_id", "conversation_messages", ["trace_id"])

    op.create_table(
        "conversation_nodes",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("parent_node_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("node_type", sa.String(length=20), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_node_id"], ["conversation_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_nodes_session_id", "conversation_nodes", ["session_id"])
    op.create_index("ix_conversation_nodes_parent_node_id", "conversation_nodes", ["parent_node_id"])
    op.create_index("ix_conversation_nodes_trace_id", "conversation_nodes", ["trace_id"])

    op.create_table(
        "agent_tool_calls",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("node_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("agent_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("skill_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["conversation_nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tool_calls_session_id", "agent_tool_calls", ["session_id"])
    op.create_index("ix_agent_tool_calls_node_id", "agent_tool_calls", ["node_id"])
    op.create_index("ix_agent_tool_calls_skill_id", "agent_tool_calls", ["skill_id"])
    op.create_index("ix_agent_tool_calls_trace_id", "agent_tool_calls", ["trace_id"])

    op.create_table(
        "context_artifacts",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_storage_key", sa.String(length=255), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("extracted_json", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ready"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_context_artifacts_hash"),
    )
    op.create_index("ix_context_artifacts_session_id", "context_artifacts", ["session_id"])
    op.create_index("ix_context_artifacts_source_type", "context_artifacts", ["source_type"])


def downgrade():
    op.drop_index("ix_context_artifacts_source_type", table_name="context_artifacts")
    op.drop_index("ix_context_artifacts_session_id", table_name="context_artifacts")
    op.drop_table("context_artifacts")

    op.drop_index("ix_agent_tool_calls_trace_id", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_skill_id", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_node_id", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_session_id", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")

    op.drop_index("ix_conversation_nodes_trace_id", table_name="conversation_nodes")
    op.drop_index("ix_conversation_nodes_parent_node_id", table_name="conversation_nodes")
    op.drop_index("ix_conversation_nodes_session_id", table_name="conversation_nodes")
    op.drop_table("conversation_nodes")

    op.drop_index("ix_conversation_messages_trace_id", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_session_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")

    op.drop_index("ix_conversation_sessions_last_message_at", table_name="conversation_sessions")
    op.drop_index("ix_conversation_sessions_agent_code", table_name="conversation_sessions")
    op.drop_index("ix_conversation_sessions_user_id", table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
