"""add status to quotation

Revision ID: 4b3f24c55f2b
Revises: d0fe5fa26c0e
Create Date: 2025-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4b3f24c55f2b'
down_revision = 'd0fe5fa26c0e'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('quotation') as batch:
        batch.add_column(sa.Column('status', sa.String(length=20), server_default='vigente', nullable=False))
    op.execute("UPDATE quotation SET status='vigente' WHERE status IS NULL")
    with op.batch_alter_table('quotation') as batch:
        batch.alter_column('status', server_default=None)


def downgrade():
    with op.batch_alter_table('quotation') as batch:
        batch.drop_column('status')
