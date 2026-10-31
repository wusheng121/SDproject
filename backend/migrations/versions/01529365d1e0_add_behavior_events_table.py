"""add_behavior_events_table

Revision ID: 01529365d1e0
Revises: b861e3a71c42
Create Date: 2026-10-30 13:46:10.813946

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01529365d1e0'
down_revision = 'b861e3a71c42'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'behavior_events',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('product_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('behavior_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_behavior_events_user_time', 'behavior_events', ['user_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_behavior_events_user_time', table_name='behavior_events')
    op.drop_table('behavior_events')
