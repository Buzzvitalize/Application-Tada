from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd0fe5fa26c0e'
down_revision = '9a12859f36b3'
branch_labels = None
depends_on = None

def upgrade():
    op.create_unique_constraint('uq_client_identifier_company', 'client', ['identifier', 'company_id'])
    op.create_unique_constraint('uq_client_email_company', 'client', ['email', 'company_id'])

def downgrade():
    op.drop_constraint('uq_client_email_company', 'client', type_='unique')
    op.drop_constraint('uq_client_identifier_company', 'client', type_='unique')
