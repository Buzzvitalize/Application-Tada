"""add valid_until to quotation

Revision ID: 1b60f7130a5a
Revises: 4b3f24c55f2b
Create Date: 2025-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1b60f7130a5a'
down_revision = '4b3f24c55f2b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('quotation', sa.Column('valid_until', sa.DateTime(), nullable=True))
    op.execute("UPDATE quotation SET valid_until = datetime(date, '+30 day')")
    op.alter_column('quotation', 'valid_until', nullable=False)


def downgrade():
    op.drop_column('quotation', 'valid_until')
