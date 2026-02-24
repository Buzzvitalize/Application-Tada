"""add product_price_log table

Revision ID: 8e1f9d2c4b7a
Revises: f2c1b8e4a9d3
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa


revision = '8e1f9d2c4b7a'
down_revision = 'f2c1b8e4a9d3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'product_price_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('product.id'), nullable=False),
        sa.Column('old_price', sa.Float(), nullable=True),
        sa.Column('new_price', sa.Float(), nullable=False),
        sa.Column('old_cost_price', sa.Float(), nullable=True),
        sa.Column('new_cost_price', sa.Float(), nullable=True),
        sa.Column('changed_by', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company_info.id'), nullable=False),
    )


def downgrade():
    op.drop_table('product_price_log')
