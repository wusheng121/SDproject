"""product ai tags

Revision ID: c4d5e6f7a8b9
Revises: b8e1c2a44d11
Create Date: 2026-10-31 00:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7a8b9"
down_revision = "b8e1c2a44d11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("ai_category", sa.String(length=50), nullable=True))
    op.add_column("products", sa.Column("ai_condition", sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column("products", "ai_condition")
    op.drop_column("products", "ai_category")
