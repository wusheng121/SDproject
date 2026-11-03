"""conversation message metadata

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversation_messages", sa.Column("metadata_json", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("conversation_messages", "metadata_json")
