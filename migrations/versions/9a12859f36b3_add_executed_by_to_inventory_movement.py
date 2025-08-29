"""add executed_by to inventory movement"""
from alembic import op
import sqlalchemy as sa

revision = '9a12859f36b3'
down_revision = '7f4677f2443e'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('inventory_movement', sa.Column('executed_by', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'inventory_movement', 'user', ['executed_by'], ['id'])


def downgrade():
    op.drop_constraint(None, 'inventory_movement', type_='foreignkey')
    op.drop_column('inventory_movement', 'executed_by')
