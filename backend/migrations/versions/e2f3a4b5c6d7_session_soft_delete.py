"""soft delete assistant sessions

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversation_sessions", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column(
        "conversation_sessions",
        sa.Column("deleted_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
    )
    op.create_index("ix_conversation_sessions_deleted_at", "conversation_sessions", ["deleted_at"])


def downgrade():
    op.drop_index("ix_conversation_sessions_deleted_at", table_name="conversation_sessions")
    op.drop_column("conversation_sessions", "deleted_by")
    op.drop_column("conversation_sessions", "deleted_at")
