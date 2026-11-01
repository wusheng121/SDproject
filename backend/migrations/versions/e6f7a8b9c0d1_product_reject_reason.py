"""product reject reason

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-11-01 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("reject_reason", sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column("products", "reject_reason")
