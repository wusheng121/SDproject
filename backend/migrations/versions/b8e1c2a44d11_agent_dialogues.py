"""agent dialogues

Revision ID: b8e1c2a44d11
Revises: a37c46901747
Create Date: 2026-10-30 22:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b8e1c2a44d11"
down_revision = "a37c46901747"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_dialogues",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("slots_json", sa.Text(), nullable=False),
        sa.Column("messages_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_dialogues_user_id", "agent_dialogues", ["user_id"])


def downgrade():
    op.drop_index("ix_agent_dialogues_user_id", table_name="agent_dialogues")
    op.drop_table("agent_dialogues")
