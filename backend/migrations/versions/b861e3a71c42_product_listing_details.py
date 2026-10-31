"""Add listing details and trade preferences to products."""
from alembic import op
import sqlalchemy as sa


revision = "b861e3a71c42"
down_revision = "a37c46901747"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("brand", sa.String(length=100), nullable=True))
    op.add_column("products", sa.Column("has_notes", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("products", sa.Column("defect_description", sa.String(length=500), nullable=True))
    op.add_column("products", sa.Column("trade_method", sa.String(length=30), nullable=True))
    op.add_column("products", sa.Column("trade_location", sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column("products", "trade_location")
    op.drop_column("products", "trade_method")
    op.drop_column("products", "defect_description")
    op.drop_column("products", "has_notes")
    op.drop_column("products", "brand")
