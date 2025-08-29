"""add terms acceptance to account_request

Revision ID: 7f4677f2443e
Revises: 53842ef09674
Create Date: 2025-08-29 14:10:55.638310
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7f4677f2443e'
down_revision = '53842ef09674'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('account_request', sa.Column('accepted_terms', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('account_request', sa.Column('accepted_terms_at', sa.DateTime(), nullable=True))
    op.add_column('account_request', sa.Column('accepted_terms_ip', sa.String(length=45), nullable=True))
    op.add_column('account_request', sa.Column('accepted_terms_user_agent', sa.String(length=255), nullable=True))
    op.execute("UPDATE account_request SET accepted_terms=0")
    op.alter_column('account_request', 'accepted_terms', server_default=None)

def downgrade():
    op.drop_column('account_request', 'accepted_terms_user_agent')
    op.drop_column('account_request', 'accepted_terms_ip')
    op.drop_column('account_request', 'accepted_terms_at')
    op.drop_column('account_request', 'accepted_terms')
